"""
Auth API router — Presentation Layer.

Thin router for authentication endpoints:
  - Token generation (login)
  - Current user info
  - User registration (admin-only)
  - SSO / OIDC login (optional)

This router contains ZERO business logic or direct database access.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    handle_sso_login,
    hash_password,
    is_setup_required,
)
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def _sso_is_configured() -> bool:
    """Return True only when all required SSO settings are present."""
    return bool(
        settings.sso_client_id
        and settings.sso_client_secret
        and settings.sso_discovery_url
    )


# ── Setup / Status ─────────────────────────────────────────────


@router.get("/setup-status")
def get_setup_status(db: DbSession):
    """Check if the system requires first-run setup."""
    return {"needs_setup": is_setup_required(db)}


# ── Login / Token ──────────────────────────────────────────────


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DbSession = None,
):
    """
    Authenticate with username and password, receive a JWT token.

    Uses OAuth2-compatible form encoding (application/x-www-form-urlencoded).
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


# ── Current User Info ──────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


# ── User Registration (Admin Only) ────────────────────────────


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    body: UserCreate,
    db: DbSession,
    token: str | None = Depends(optional_oauth2_scheme),
):
    """
    Create a new user account.

    Allows registration without an admin JWT ONLY IF the system requires setup.
    Otherwise, a valid admin JWT is required.
    """
    if not is_setup_required(db):
        if not token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Setup already complete. Admin privileges required.",
            )
        from app.api.deps import get_current_user, get_current_active_admin
        try:
            user = get_current_user(token, db)
            get_current_active_admin(user)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )

    repo = UserRepository(db)

    # Check for existing username
    if repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' is already taken",
        )

    # Check for existing email
    if repo.get_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    created = repo.create(user)
    return UserResponse.model_validate(created)


# ── SSO / OIDC ─────────────────────────────────────────────────


@router.get("/sso/enabled")
def sso_enabled():
    """Public endpoint — tells the frontend whether SSO is configured."""
    return {"sso_enabled": _sso_is_configured()}


@router.get("/sso/login")
async def sso_login(request: Request):
    """
    Initialize the OIDC login flow.

    Fetches provider metadata from the Discovery URL, builds an
    authorization redirect, and sends the browser to the IdP.
    """
    if not _sso_is_configured():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO is not configured",
        )

    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="sso",
        client_id=settings.sso_client_id,
        client_secret=settings.sso_client_secret,
        server_metadata_url=settings.sso_discovery_url,
        client_kwargs={"scope": "openid email profile"},
    )

    redirect_uri = str(request.url_for("sso_callback"))
    return await oauth.sso.authorize_redirect(request, redirect_uri)


@router.get("/sso/callback")
async def sso_callback(request: Request, db: DbSession):
    """
    Handle the OIDC callback from the Identity Provider.

    Exchanges the authorization code for tokens, extracts user
    claims, provisions/updates the local user via the service
    layer, and returns a 302 redirect to the frontend with the
    JWT in the query string.
    """
    if not _sso_is_configured():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO is not configured",
        )

    from authlib.integrations.starlette_client import OAuth

    oauth = OAuth()
    oauth.register(
        name="sso",
        client_id=settings.sso_client_id,
        client_secret=settings.sso_client_secret,
        server_metadata_url=settings.sso_discovery_url,
        client_kwargs={"scope": "openid email profile"},
    )

    try:
        token_data = await oauth.sso.authorize_access_token(request)
    except Exception as exc:
        logger.error("SSO token exchange failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSO authentication failed",
        )

    # Extract claims from the ID token
    userinfo = token_data.get("userinfo", {})
    email = userinfo.get("email", "")
    username = userinfo.get("preferred_username") or userinfo.get("name") or email.split("@")[0]
    user_groups = userinfo.get("groups", []) or userinfo.get("roles", [])

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO provider did not return an email address",
        )

    # Delegate to service layer (business logic)
    user = handle_sso_login(db, email, username, user_groups)

    # Issue a local IPAM JWT — same as local login
    access_token = create_access_token(data={"sub": user.username})

    # 302 redirect to the frontend SSOSuccess page with the token
    frontend_url = f"/sso-success?token={access_token}"
    return RedirectResponse(url=frontend_url, status_code=302)

