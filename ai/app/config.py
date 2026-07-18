"""AI 引擎配置

所有敏感配置和部署相关值均从 .env 文件读取。
本文件只提供空默认值和类型声明，不包含任何真实密钥或地址。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（本文件位于 ai/app/，向上两级到根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Redis（任务队列 + 缓存）
    REDIS_URL: str = ""

    # 后端服务地址
    BACKEND_URL: str = ""

    # 本地微调模型
    LOCAL_MODEL_URL: str = ""
    LOCAL_MODEL_NAME: str = ""

    # 远程大模型 API
    REMOTE_MODEL_API_KEY: str = ""
    REMOTE_MODEL_BASE_URL: str = ""
    REMOTE_MODEL_NAME: str = ""

    # 快速回答模型（内网部署的 Qwen3.5-9B）
    QUICK_MODEL_URL: str = ""
    QUICK_MODEL_NAME: str = ""

    # DeepSeek 深度解答模型
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = ""
    DEEPSEEK_MODEL_NAME: str = ""

    # ChromaDB
    CHROMADB_HOST: str = ""
    CHROMADB_PORT: int = 8000

    # 服务间认证（backend → ai）
    SERVICE_TOKEN: str = ""

    # 知识图谱
    KG_DATA_DIR: str = "data/kg"
    KG_MODEL_API_KEY: str = ""
    KG_MODEL_BASE_URL: str = ""
    KG_MODEL_NAME: str = ""

    # OCR 文档解析
    OCR_VLM_URL: str = ""
    OCR_OUTPUT_DIR: str = "data/ocr_output"
    OCR_TASK_RETENTION_SECONDS: int = 86400
    OCR_MAX_CONCURRENT: int = 2

    # Apache AGE
    AGE_HOST: str = ""
    AGE_PORT: int = 5432
    AGE_DB: str = ""
    AGE_USER: str = ""
    AGE_PASSWORD: str = ""
    AGE_GRAPH_NAME: str = ""

    # MCP 联网搜索
    MCP_SEARCH_URL: str = ""
    MCP_SEARCH_TOKEN: str = ""
    MCP_PROXY: str = ""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore"
    )

settings = Settings()
