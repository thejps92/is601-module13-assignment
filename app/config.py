from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Default to SQLite for local dev; override via DATABASE_URL for Postgres.
    DATABASE_URL: str = "sqlite:///./app.db"

    # JWT settings (override via env vars in production/CI)
    JWT_SECRET_KEY: str = "change-me-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
