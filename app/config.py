# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:107gaming@localhost:5432/rfp"
    UPLOAD_DIR: str = "./uploads"
    GOOGLE_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
