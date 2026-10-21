"""Passkey accounts end to end, with a software authenticator standing in for a phone."""

import base64
import hashlib
import json
import os

import cbor2
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app

ORIGIN = "http://localhost:3000"
RP_ID = "localhost"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class FakeAuthenticator:
    """Just enough of a platform authenticator: one P-256 key, 'none' attestation."""

    def __init__(self) -> None:
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(16)
        self.count = 0
        self.user_handle = b""

    def _client_data(self, kind: str, challenge: str, origin: str) -> bytes:
        return json.dumps(
            {"type": kind, "challenge": challenge, "origin": origin, "crossOrigin": False}
        ).encode()

    def create(self, options: dict, origin: str = ORIGIN) -> dict:
        numbers = self.key.public_key().public_numbers()
        cose = cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32), -3: numbers.y.to_bytes(32)}
        )
        auth_data = (
            hashlib.sha256(options["rp"]["id"].encode()).digest()
            + bytes([0x45])  # user present + verified + attested credential data
            + self.count.to_bytes(4)
            + bytes(16)
            + len(self.credential_id).to_bytes(2)
            + self.credential_id
            + cose
        )
        self.user_handle = unb64(options["user"]["id"])
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        client_data = self._client_data("webauthn.create", options["challenge"], origin)
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {"clientDataJSON": b64(client_data), "attestationObject": b64(attestation)},
            "clientExtensionResults": {},
        }

    def get(self, options: dict, origin: str = ORIGIN) -> dict:
        self.count += 1
        auth_data = (
            hashlib.sha256(options["rpId"].encode()).digest()
            + bytes([0x05])
            + self.count.to_bytes(4)
        )
        client_data = self._client_data("webauthn.get", options["challenge"], origin)
        signature = self.key.sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "authenticatorData": b64(auth_data),
                "signature": b64(signature),
                "userHandle": b64(self.user_handle),
            },
            "clientExtensionResults": {},
        }


@pytest.fixture
def api():
    with TestClient(create_app(), headers={"Origin": ORIGIN}) as client:
        yield client


def register(api, device: FakeAuthenticator) -> str:
    start = api.post("/api/auth/register/options").json()
    assert start["options"]["rp"]["id"] == RP_ID
    finish = api.post(
        "/api/auth/register/verify",
        json={"challenge_id": start["challenge_id"], "credential": device.create(start["options"])},
    )
    assert finish.status_code == 200, finish.text
    return finish.json()["token"]


def login(api, device: FakeAuthenticator):
    start = api.post("/api/auth/login/options").json()
    return api.post(
        "/api/auth/login/verify",
        json={"challenge_id": start["challenge_id"], "credential": device.get(start["options"])},
    )


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


KITCHEN = {"dishes": [{"name": "Flavoured rice"}], "cooked": [], "prefs": {"diet": {}}}


def test_save_sign_in_elsewhere_and_delete(api) -> None:
    phone = FakeAuthenticator()
    token = register(api, phone)
    assert api.get("/api/me", headers=auth(token)).json()["has_kitchen"] is False

    saved = api.put("/api/kitchen", json={"kitchen": KITCHEN}, headers=auth(token))
    assert saved.status_code == 200 and saved.json()["updated_at"]

    # Sign out, then sign in again with the same (synced) passkey: the kitchen is there.
    assert api.post("/api/auth/logout", headers=auth(token)).status_code == 204
    assert api.get("/api/me", headers=auth(token)).status_code == 401
    again = login(api, phone)
    assert again.status_code == 200, again.text
    token2 = again.json()["token"]
    assert api.get("/api/kitchen", headers=auth(token2)).json()["kitchen"] == KITCHEN

    assert api.delete("/api/me", headers=auth(token2)).status_code == 204
    assert api.get("/api/me", headers=auth(token2)).status_code == 401
    assert login(api, phone).status_code == 400  # the passkey is gone with the account


def test_prompt_from_another_site_is_refused(api) -> None:
    refused = api.post("/api/auth/register/options", headers={"Origin": "https://evil.example"})
    assert refused.status_code == 400


def test_response_for_another_origin_fails(api) -> None:
    start = api.post("/api/auth/register/options").json()
    credential = FakeAuthenticator().create(start["options"], origin="https://evil.example")
    result = api.post(
        "/api/auth/register/verify",
        json={"challenge_id": start["challenge_id"], "credential": credential},
    )
    assert result.status_code == 400


def test_challenge_works_once(api) -> None:
    device = FakeAuthenticator()
    start = api.post("/api/auth/register/options").json()
    body = {"challenge_id": start["challenge_id"], "credential": device.create(start["options"])}
    assert api.post("/api/auth/register/verify", json=body).status_code == 200
    assert api.post("/api/auth/register/verify", json=body).status_code == 400


def test_wrong_key_cannot_sign_in(api) -> None:
    phone = FakeAuthenticator()
    register(api, phone)
    thief = FakeAuthenticator()
    thief.credential_id = phone.credential_id  # same id, different private key
    thief.user_handle = phone.user_handle
    assert login(api, thief).status_code == 400


def test_kitchen_needs_sign_in_and_has_a_size_limit(api) -> None:
    assert api.get("/api/kitchen").status_code == 401
    assert api.get("/api/kitchen", headers=auth("made-up")).status_code == 401
    token = register(api, FakeAuthenticator())
    huge = {"notes": "x" * (settings.max_synced_kitchen_bytes + 1)}
    assert api.put("/api/kitchen", json={"kitchen": huge}, headers=auth(token)).status_code == 413
