"""Optional accounts: passkey sign-in and the synced kitchen. The app works without them."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.config import settings
from app.deps import get_account_service
from app.limiter import limiter
from app.models.api import (
    KitchenSync,
    KitchenSyncResponse,
    Me,
    PasskeyFinish,
    PasskeyOptions,
    SessionResponse,
)
from app.repositories.account_repository import AccountStoreError
from app.services.account_service import AccountService, AuthFailed, KitchenTooLarge

router = APIRouter(prefix="/api")

STORE_DOWN_MESSAGE = "Sign-in is down for a moment. Your kitchen is still saved on this device."


def bearer(authorization: str | None = Header(default=None)) -> str:
    """The session token from `Authorization: Bearer <token>`."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in.")
    return authorization.removeprefix("Bearer ").strip()


def current_user(
    token: str = Depends(bearer), service: AccountService = Depends(get_account_service)
) -> str:
    """The signed-in user's id, or 401."""
    try:
        user_id = service.user_for(token)
    except AccountStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, STORE_DOWN_MESSAGE) from exc
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signed out. Sign in again.")
    return user_id


def _origin(request: Request) -> str:
    return request.headers.get("origin", "")


def _call(fn, *args):
    """Run a service call, mapping its errors to HTTP."""
    try:
        return fn(*args)
    except AuthFailed as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except KitchenTooLarge as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except AccountStoreError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, STORE_DOWN_MESSAGE) from exc


@router.post("/auth/register/options", response_model=PasskeyOptions)
@limiter.limit(settings.auth_rate_limit)
async def register_options(
    request: Request, service: AccountService = Depends(get_account_service)
) -> PasskeyOptions:
    """Start saving a kitchen with a new passkey."""
    challenge_id, options = _call(service.register_options, _origin(request))
    return PasskeyOptions(challenge_id=challenge_id, options=options)


@router.post("/auth/register/verify", response_model=SessionResponse)
@limiter.limit(settings.auth_rate_limit)
async def register_verify(
    request: Request, body: PasskeyFinish, service: AccountService = Depends(get_account_service)
) -> SessionResponse:
    """Finish: the passkey is saved and this device is signed in."""
    return SessionResponse(token=_call(service.register_verify, body.challenge_id, body.credential))


@router.post("/auth/login/options", response_model=PasskeyOptions)
@limiter.limit(settings.auth_rate_limit)
async def login_options(
    request: Request, service: AccountService = Depends(get_account_service)
) -> PasskeyOptions:
    """Start signing in with a passkey (no username needed)."""
    challenge_id, options = _call(service.login_options, _origin(request))
    return PasskeyOptions(challenge_id=challenge_id, options=options)


@router.post("/auth/login/verify", response_model=SessionResponse)
@limiter.limit(settings.auth_rate_limit)
async def login_verify(
    request: Request, body: PasskeyFinish, service: AccountService = Depends(get_account_service)
) -> SessionResponse:
    """Finish signing in."""
    return SessionResponse(token=_call(service.login_verify, body.challenge_id, body.credential))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(bearer), service: AccountService = Depends(get_account_service)
) -> Response:
    """Sign this device out. The kitchen stays on the device and in the account."""
    _call(service.sign_out, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=Me)
async def me(
    user_id: str = Depends(current_user), service: AccountService = Depends(get_account_service)
) -> Me:
    """Am I signed in, and is there a kitchen in my account?"""
    saved = _call(service.kitchen, user_id)
    return Me(
        has_kitchen=saved is not None,
        kitchen_updated_at=saved[1].isoformat() if saved else None,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user_id: str = Depends(current_user), service: AccountService = Depends(get_account_service)
) -> Response:
    """Delete the account and everything in it. The passkey on the device can then be removed."""
    _call(service.delete_account, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/kitchen", response_model=KitchenSyncResponse)
@limiter.limit(settings.sync_rate_limit)
async def get_kitchen(
    request: Request,
    user_id: str = Depends(current_user),
    service: AccountService = Depends(get_account_service),
) -> KitchenSyncResponse:
    """The kitchen saved in this account (null if none yet)."""
    saved = _call(service.kitchen, user_id)
    if saved is None:
        return KitchenSyncResponse(kitchen=None, updated_at=None)
    return KitchenSyncResponse(kitchen=saved[0], updated_at=saved[1].isoformat())


@router.put("/kitchen", response_model=KitchenSyncResponse)
@limiter.limit(settings.sync_rate_limit)
async def put_kitchen(
    request: Request,
    body: KitchenSync,
    user_id: str = Depends(current_user),
    service: AccountService = Depends(get_account_service),
) -> KitchenSyncResponse:
    """Save this device's kitchen to the account."""
    saved_at = _call(service.save_kitchen, user_id, body.kitchen)
    return KitchenSyncResponse(kitchen=body.kitchen, updated_at=saved_at.isoformat())
