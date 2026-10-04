import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from backend.app.core.errors import NutriLensException
from backend.app.models.user import AppUser
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserUpdateRequest,
)

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, payload: UserRegisterRequest) -> TokenResponse:
        existing = self.db.query(AppUser).filter(AppUser.email == payload.email).first()
        if existing:
            raise NutriLensException(
                status_code=400,
                code="EMAIL_ALREADY_REGISTERED",
                message="An account with this email address already exists",
            )

        user = AppUser(
            id=str(uuid.uuid4()),
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            auth_provider="email",
            display_name=payload.display_name or payload.email.split("@")[0],
            age_range=payload.age_range,
            sex=payload.sex,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            timezone=payload.timezone or "Asia/Kolkata",
            training_consent=payload.training_consent,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        access_token = create_access_token({"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token({"sub": user.id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=60 * 24 * 7,
            user={
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
        )

    def login(self, payload: UserLoginRequest) -> TokenResponse:
        user = self.db.query(AppUser).filter(AppUser.email == payload.email, AppUser.deleted_at.is_(None)).first()
        if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
            raise NutriLensException(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password",
            )

        access_token = create_access_token({"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token({"sub": user.id})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=60 * 24 * 7,
            user={
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            },
        )

    def get_profile(self, user_id: str) -> UserProfileResponse:
        user = self.db.query(AppUser).filter(AppUser.id == user_id, AppUser.deleted_at.is_(None)).first()
        if not user:
            raise NutriLensException(status_code=404, code="USER_NOT_FOUND", message="User not found")
        return UserProfileResponse.from_orm(user)

    def update_profile(self, user_id: str, payload: UserUpdateRequest) -> UserProfileResponse:
        user = self.db.query(AppUser).filter(AppUser.id == user_id, AppUser.deleted_at.is_(None)).first()
        if not user:
            raise NutriLensException(status_code=404, code="USER_NOT_FOUND", message="User not found")

        if payload.display_name is not None:
            user.display_name = payload.display_name
        if payload.age_range is not None:
            user.age_range = payload.age_range
        if payload.sex is not None:
            user.sex = payload.sex
        if payload.height_cm is not None:
            user.height_cm = payload.height_cm
        if payload.weight_kg is not None:
            user.weight_kg = payload.weight_kg
        if payload.timezone is not None:
            user.timezone = payload.timezone
        if payload.training_consent is not None:
            user.training_consent = payload.training_consent

        self.db.commit()
        self.db.refresh(user)
        return UserProfileResponse.from_orm(user)

    def delete_account(self, user_id: str) -> bool:
        user = self.db.query(AppUser).filter(AppUser.id == user_id).first()
        if not user:
            return False
        user.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return True
