"""
Auth API router — Presentation Layer.

Thin router for authentication endpoints:
  - Token generation (login)
  - Current user info
  - User registration (admin-only)

This router contains ZERO business logic or direct database access.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentAdmin, CurrentUser, DbSession
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.auth_service import authenticate_user, create_access_token, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


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
    admin: CurrentAdmin = None,
):
    """
    Create a new user account.

    Restricted to admin users. Use the CLI bootstrap script
    (backend/scripts/create_admin.py) to create the initial admin.
    """
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
