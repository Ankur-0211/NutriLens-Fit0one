from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import security_bearer, decode_token
from backend.app.modules.auth.service import AuthService
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserUpdateRequest,
)

router = APIRouter(tags=["auth"])

def get_current_user_id(credentials = Depends(security_bearer)) -> str:
    if not credentials or not credentials.credentials:
        # Default guest user ID for smooth zero-friction access
        return "guest-user-default"
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload["sub"]

@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(payload)

@router.post("/auth/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(payload)

@router.get("/users/me", response_model=UserProfileResponse)
def get_me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        return service.get_profile(user_id)
    except Exception:
        # If guest or demo, return demo profile
        return UserProfileResponse(
            id=user_id,
            email="demo@nutrilens.ai",
            display_name="Kinetix Athlete",
            age_range="25-35",
            sex="unspecified",
            height_cm=175.0,
            weight_kg=72.0,
            timezone="Asia/Kolkata",
            training_consent=False,
            created_at="2026-10-04T00:00:00Z",
        )

@router.patch("/users/me", response_model=UserProfileResponse)
def update_me(payload: UserUpdateRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.update_profile(user_id, payload)

