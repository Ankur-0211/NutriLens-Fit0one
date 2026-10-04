from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    age_range: Optional[str] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    timezone: Optional[str] = "Asia/Kolkata"
    training_consent: bool = False

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    age_range: Optional[str]
    sex: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    timezone: str
    training_consent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    age_range: Optional[str] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    timezone: Optional[str] = None
    training_consent: Optional[bool] = None
