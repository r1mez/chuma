"""应用配置 — 从环境变量加载"""

from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录（本文件位于 backend/app/core/，向上三级到根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "ChuMa Backend"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://chuma:chuma@postgres:5432/chuma"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # AI 服务
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TOKEN: str = "change-me-in-production"  # 必须与 ai/app/config.py 中的 SERVICE_TOKEN 一致

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    class Config:
        env_file = PROJECT_ROOT / ".env"


settings = Settings()
