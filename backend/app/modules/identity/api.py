from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.modules.identity.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from app.modules.identity.service import (
    authenticate_user,
    build_token_pair,
    get_current_user,
    refresh_tokens,
    register_user,
)

router = APIRouter()


@router.post(
    "/auth/register", response_model=TokenPairResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = register_user(db, email=payload.email, password=payload.password)
    return build_token_pair(user)


@router.post("/auth/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    return build_token_pair(user)


@router.post("/auth/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    return refresh_tokens(db, refresh_token=payload.refresh_token)


@router.get("/users/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return current_user
