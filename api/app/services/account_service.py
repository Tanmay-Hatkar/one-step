"""Optional accounts: passkey sign-in (WebAuthn) and a synced kitchen.

No email, no password, no third party: the account is a random id, the only way in is a
passkey on the user's device (synced by their phone's password manager), and the only
thing stored is the kitchen they'd otherwise keep in the browser.
"""

import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.config import Settings
from app.db import AuthChallenge, Passkey
from app.repositories.account_repository import AccountRepository, aware

logger = logging.getLogger(__name__)

USER_NAME = "One Step kitchen"  # what the passkey is called in the user's password manager


class AuthFailed(ValueError):
    """The passkey ceremony didn't check out (wrong origin, stale prompt, bad signature)."""


class KitchenTooLarge(ValueError):
    """A synced kitchen over the size limit."""


def token_hash(token: str) -> str:
    """Sessions are stored by hash, so a database leak doesn't leak sign-ins."""
    return hashlib.sha256(token.encode()).hexdigest()


class AccountService:
    """Passkey registration and sign-in, sessions, and the synced kitchen."""

    def __init__(self, repo: AccountRepository, settings: Settings) -> None:
        """Args: repo: account storage; settings: allowed origins, lifetimes, limits."""
        self._repo = repo
        self._settings = settings

    # --- Passkey ceremonies -------------------------------------------------------------

    def register_options(self, origin: str) -> tuple[str, dict[str, Any]]:
        """Start creating an account. Returns (challenge id, options for the browser).

        Raises:
            AuthFailed: If the request didn't come from one of our sites.
        """
        rp_id = self._rp_id(origin)
        user_id = secrets.token_hex(16)
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name=self._settings.rp_name,
            user_id=user_id.encode(),
            user_name=USER_NAME,
            user_display_name=USER_NAME,
            # A discoverable passkey: sign-in later needs no username at all.
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )
        return self._challenge("register", options, origin, user_id)

    def register_verify(self, challenge_id: str, credential: dict[str, Any]) -> str:
        """Finish creating an account. Returns a session token.

        Raises:
            AuthFailed: If the challenge is unknown/expired or the passkey doesn't verify.
        """
        challenge = self._take(challenge_id, "register")
        try:
            verified = verify_registration_response(
                credential=credential,
                expected_challenge=challenge.challenge,
                expected_rp_id=self._rp_id(challenge.origin),
                expected_origin=challenge.origin,
            )
        except InvalidRegistrationResponse as exc:
            logger.info("Passkey registration rejected: %s", exc)
            raise AuthFailed("That passkey couldn't be saved.") from exc
        user_id = challenge.user_id or ""
        self._repo.create_user(
            user_id,
            Passkey(
                id=bytes_to_base64url(verified.credential_id),
                user_id=user_id,
                public_key=verified.credential_public_key,
                sign_count=verified.sign_count,
            ),
        )
        return self._start_session(user_id)

    def login_options(self, origin: str) -> tuple[str, dict[str, Any]]:
        """Start signing in with any passkey for this site.

        Raises:
            AuthFailed: If the request didn't come from one of our sites.
        """
        options = generate_authentication_options(
            rp_id=self._rp_id(origin),
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        return self._challenge("login", options, origin, None)

    def login_verify(self, challenge_id: str, credential: dict[str, Any]) -> str:
        """Finish signing in. Returns a session token.

        Raises:
            AuthFailed: If the challenge, passkey or signature doesn't check out.
        """
        challenge = self._take(challenge_id, "login")
        credential_id = credential.get("id") if isinstance(credential, dict) else None
        passkey = self._repo.passkey(credential_id) if isinstance(credential_id, str) else None
        if passkey is None:
            raise AuthFailed("That passkey isn't linked to a kitchen here.")
        try:
            verified = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge.challenge,
                expected_rp_id=self._rp_id(challenge.origin),
                expected_origin=challenge.origin,
                credential_public_key=passkey.public_key,
                credential_current_sign_count=passkey.sign_count,
            )
        except InvalidAuthenticationResponse as exc:
            logger.info("Passkey sign-in rejected: %s", exc)
            raise AuthFailed("That passkey didn't check out.") from exc
        self._repo.set_sign_count(passkey.id, verified.new_sign_count)
        return self._start_session(passkey.user_id)

    # --- Sessions -----------------------------------------------------------------------

    def user_for(self, token: str) -> str | None:
        """The signed-in user's id, or None."""
        return self._repo.session_user(token_hash(token), datetime.now(UTC))

    def sign_out(self, token: str) -> None:
        """End this device's session."""
        self._repo.end_session(token_hash(token))

    def delete_account(self, user_id: str) -> None:
        """Delete the account, its passkeys, sessions and kitchen."""
        self._repo.delete_user(user_id)

    # --- Synced kitchen -----------------------------------------------------------------

    def kitchen(self, user_id: str) -> tuple[dict[str, Any], datetime] | None:
        """The synced kitchen and when it was saved, or None."""
        row = self._repo.kitchen(user_id)
        if row is None:
            return None
        try:
            return json.loads(row.payload_json), row.updated_at
        except json.JSONDecodeError:
            logger.exception("Unreadable synced kitchen for %s", user_id)
            return None

    def save_kitchen(self, user_id: str, kitchen: dict[str, Any]) -> datetime:
        """Replace the synced kitchen. Returns when it was saved.

        The kitchen is the web app's own saved state; it's re-validated by every request
        that uses it, so here it's only size-checked.

        Raises:
            KitchenTooLarge: Over the size limit.
        """
        payload = json.dumps(kitchen, separators=(",", ":"))
        if len(payload.encode()) > self._settings.max_synced_kitchen_bytes:
            raise KitchenTooLarge("That kitchen is too big to sync.")
        now = datetime.now(UTC)
        self._repo.save_kitchen(user_id, payload, now)
        return now

    # --- Helpers ------------------------------------------------------------------------

    def _rp_id(self, origin: str) -> str:
        """Passkeys belong to the site's host name; only our own sites may ask."""
        if origin not in self._settings.cors_origin_list:
            raise AuthFailed("Sign-in isn't available from this site.")
        host = urlparse(origin).hostname
        if not host:
            raise AuthFailed("Sign-in isn't available from this site.")
        return host

    def _challenge(
        self, kind: str, options: Any, origin: str, user_id: str | None
    ) -> tuple[str, dict[str, Any]]:
        now = datetime.now(UTC)
        self._repo.purge_challenges(now - timedelta(seconds=self._settings.auth_challenge_seconds))
        challenge_id = secrets.token_urlsafe(24)
        self._repo.add_challenge(
            AuthChallenge(
                id=challenge_id,
                kind=kind,
                challenge=options.challenge,
                origin=origin,
                user_id=user_id,
                created_at=now,
            )
        )
        return challenge_id, json.loads(options_to_json(options))

    def _take(self, challenge_id: str, kind: str) -> AuthChallenge:
        challenge = self._repo.take_challenge(challenge_id)
        if challenge is None or challenge.kind != kind:
            raise AuthFailed("That sign-in prompt expired. Try again.")
        age = datetime.now(UTC) - aware(challenge.created_at)
        if age > timedelta(seconds=self._settings.auth_challenge_seconds):
            raise AuthFailed("That sign-in prompt expired. Try again.")
        return challenge

    def _start_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(days=self._settings.session_days)
        self._repo.add_session(token_hash(token), user_id, expires)
        return token
