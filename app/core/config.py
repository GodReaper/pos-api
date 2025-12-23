from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    # App
    APP_NAME: str = "POS API"
    DEBUG: bool = False
    
    # MongoDB
    # Support both MONGO_URI (legacy) and MONGODB_URL
    MONGO_URI: str | None = None
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pos_db"
    
    # Redis - support both REDIS_URL and separate fields
    REDIS_URL: str | None = None
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_SSL: bool = False
    
    # JWT
    JWT_SECRET: str = "change_me_to_long_random"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Admin Seed
    SEED_ADMIN_KEY: str | None = None
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string, preferring MONGO_URI if set"""
        if self.MONGO_URI:
            return self.MONGO_URI
        return self.MONGODB_URL
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields in .env
    )


settings = Settings()

