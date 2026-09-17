import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Reel AI Studio"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # API Keys (BYOK fallback)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Security & Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")
    TRUSTED_PROXIES: str = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1,localhost")

    # Auth & Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "reel-studio-super-secure-jwt-key-987654321")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72
    
    # Admin Security (IP Whitelisting)
    ADMIN_ALLOWED_IPS: str = os.getenv("ADMIN_ALLOWED_IPS", "127.0.0.1,::1,localhost")
    ADMIN_DEFAULT_EMAIL: str = os.getenv("ADMIN_DEFAULT_EMAIL", "admin@reels.ai")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@123456")
    
    # Directories
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    FONTS_DIR: Path = BASE_DIR / "fonts"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Limits & Retention Tuning for 1GB VPS
    MAX_UPLOAD_SIZE_MB: int = 200
    MAX_YOUTUBE_DURATION_SEC: int = 300  # 5 mins max for shorts/reels
    AUTO_CLEANUP_HOURS: int = 72         # 3 days automatic purge
    FFMPEG_THREADS: int = 1              # 1 thread to prevent OOM on 1GB VPS
    
    class Config:
        env_file = BASE_DIR / ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.FONTS_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
