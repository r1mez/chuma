"""AI 引擎配置"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis（任务队列 + 缓存）
    REDIS_URL: str = "redis://redis:6379/1"

    # 后端服务地址
    BACKEND_URL: str = "http://backend:8000"

    # 本地微调模型
    LOCAL_MODEL_URL: str = "http://localhost:8002/v1"  # vLLM/Ollama 服务地址
    LOCAL_MODEL_NAME: str = "chuma-finetuned"

    # 远程大模型 API
    REMOTE_MODEL_API_KEY: str = ""
    REMOTE_MODEL_BASE_URL: str = ""  # 讯飞星火或其他
    REMOTE_MODEL_NAME: str = ""

    # ChromaDB（Docker 内部通信使用服务名 "chromadb"，本地开发改为 "localhost:8020"）
    CHROMADB_HOST: str = "chromadb"
    CHROMADB_PORT: int = 8000

    # 服务间认证（backend → ai）
    SERVICE_TOKEN: str = "change-me-in-production"

    # 知识图谱
    KG_DATA_DIR: str = "data/kg"

    class Config:
        env_file = ".env"


settings = Settings()
