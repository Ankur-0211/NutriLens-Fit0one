from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "NutriLens - Indian Food Calorie & Nutrition Tracker"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/v1"
    
    # Versioning tags as mandated by SDD Section 40 & 21
    SCHEMA_VERSION: str = "1.0"
    VISUAL_LABELSET_VERSION: str = "vis-2026.01"
    IDENTITY_MAP_VERSION: str = "idmap-2026.01"
    NUTRITION_DB_VERSION: str = "nut-2026.01"
    DETECTOR_MODEL_VERSION: str = "det-0.3.1"
    CLASSIFIER_MODEL_VERSION: str = "cls-0.5.0"
    PORTION_MODEL_VERSION: str = "por-0.2.0"
    RESOLVER_VERSION: str = "idr-0.1.0"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'nutrilens.db'}")
    
    # JWT Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "nutrilens_super_secret_jwt_key_development_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Upload & Storage
    STORAGE_DIR: Path = BASE_DIR / "uploads"
    MAX_IMAGE_SIZE_BYTES: int = 8 * 1024 * 1024  # 8 MB
    MIN_IMAGE_DIMENSION: int = 320
    MAX_IMAGE_DIMENSION: int = 4096

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
