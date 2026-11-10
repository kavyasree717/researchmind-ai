from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError
from uuid import UUID

from app.database import get_db
from app.config import settings
from app.models.user import User

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
)

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"


def set_refresh_cookie(
    response: Response,
    token: str,
    remember_me: bool,
):
    cookie_options = {
        "key": REFRESH_COOKIE_NAME,
        "value": token,
        "httponly": True,
        "secure": settings.refresh_cookie_secure,
        "samesite": settings.refresh_cookie_samesite,
        "path": REFRESH_COOKIE_PATH,
    }

    if remember_me:
        cookie_options["max_age"] = (
            settings.refresh_token_expire_days * 24 * 60 * 60
        )

    response.set_cookie(**cookie_options)


def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(
            or_(
                User.email == user_data.email,
                User.username == user_data.username,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email or username already registered",
        )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == login_data.email)
    )

    if not user or not verify_password(
        login_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user_id = str(user.id)

    access_token = create_access_token(user_id)

    refresh_token = create_refresh_token(
        user_id,
        remember_me=login_data.remember_me,
    )

    set_refresh_cookie(
        response,
        refresh_token,
        login_data.remember_me,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session not found. Please log in again.",
        )

    try:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Incorrect token type")

        user_id = UUID(payload["sub"])
        remember_me = payload.get("remember_me", True)

    except (InvalidTokenError, ValueError, KeyError, TypeError):
        clear_refresh_cookie(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session expired. Please log in again.",
        )

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        clear_refresh_cookie(response)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    # Generate a new access token.
    new_access_token = create_access_token(str(user.id))

    # Rotate the refresh token and extend its expiry.
    new_refresh_token = create_refresh_token(
        str(user.id),
        remember_me=remember_me,
    )

    set_refresh_cookie(
        response,
        new_refresh_token,
        remember_me,
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(response: Response):
    clear_refresh_cookie(response)

    return {
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user