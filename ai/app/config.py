"""AI 引擎配置"""

from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录（本文件位于 ai/app/，向上两级到根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Redis（任务队列 + 缓存）
    REDIS_URL: str = "redis://localhost:6379/1"

    # 后端服务地址
    BACKEND_URL: str = "http://localhost:8006"

    # 本地微调模型
    LOCAL_MODEL_URL: str = "http://localhost:8002/v1"  # vLLM/Ollama 服务地址
    LOCAL_MODEL_NAME: str = "chuma-finetuned"

    # 远程大模型 API
    REMOTE_MODEL_API_KEY: str = ""
    REMOTE_MODEL_BASE_URL: str = ""  # 讯飞星火或其他
    REMOTE_MODEL_NAME: str = ""

    # 快速回答模型（内网部署的 Qwen3.5-9B）
    QUICK_MODEL_URL: str = "http://10.16.75.254:8002/v1"
    QUICK_MODEL_NAME: str = "/home/ll_yqs2/models/Qwen3.5-9B"

    # DeepSeek 深度解答模型（从项目根目录 .env 读取）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = ""
    DEEPSEEK_MODEL_NAME: str = ""

    # ChromaDB（Docker 内部通信使用服务名 "chromadb"，本地开发改为 "localhost:8020"）
    CHROMADB_HOST: str = "localhost"
    CHROMADB_PORT: int = 8000

    # 服务间认证（backend → ai）
    SERVICE_TOKEN: str = "change-me-in-production"

    # 知识图谱
    KG_DATA_DIR: str = "data/kg"
    KG_MODEL_API_KEY: str = ""
    KG_MODEL_BASE_URL: str = "https://api.deepseek.com"
    KG_MODEL_NAME: str = "deepseek-v4-flash"

    # OCR 文档解析
    OCR_VLM_URL: str = "http://10.16.75.254:8004"  # vLLM OCR 服务地址
    OCR_OUTPUT_DIR: str = "data/ocr_output"          # 解析结果输出目录
    OCR_TASK_RETENTION_SECONDS: int = 86400           # 任务结果保留时间 (24h)
    OCR_MAX_CONCURRENT: int = 2                       # 最大并发解析数

    # Apache AGE
    AGE_HOST: str = "43.139.215.55"
    AGE_PORT: int = 5432
    AGE_DB: str = "chuma"
    AGE_USER: str = "chuma"
    AGE_PASSWORD: str = ""
    AGE_GRAPH_NAME: str = "chuma_kg"

    # MCP 联网搜索
    MCP_SEARCH_URL: str = ""        # MCP SSE 端点 URL
    MCP_SEARCH_TOKEN: str = ""      # MCP Server 认证令牌

    class Config:
        env_file = PROJECT_ROOT / ".env"
        extra = "ignore"


settings = Settings()
