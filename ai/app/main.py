"""ChuMa AI Engine"""

import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI

from app.api import chat, gnn, kg
from app.agent import router as agent_router
from app.config import settings
from app.dependencies import verify_service_token
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.tasks.worker import start_worker
from app.agent.mcp_client import mcp_client
from app.ocr.router import router as ocr_router, set_task_manager
from app.ocr.task_manager import AsyncTaskManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 清理 Redis 残留缓存（如旧版 KG 构建结果）
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match="kg:result:*", count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
        await r.aclose()
    except Exception:
        logger.warning("Failed to clean Redis cache on startup (non-fatal)")

    start_scheduler()

    ocr_manager = AsyncTaskManager()
    await ocr_manager.start()
    set_task_manager(ocr_manager)

    worker_task = asyncio.create_task(start_worker())

    async with mcp_client:
        yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    await ocr_manager.shutdown()
    stop_scheduler()


app = FastAPI(title="ChuMa AI Engine", version="0.1.0", lifespan=lifespan)

auth_dep = [Depends(verify_service_token)]

app.include_router(chat.router, prefix="/rag", tags=["AI Chat"], dependencies=auth_dep)
app.include_router(gnn.router, prefix="/gnn", tags=["GNN"], dependencies=auth_dep)
app.include_router(kg.router, prefix="/kg", tags=["Knowledge Graph"], dependencies=auth_dep)
app.include_router(agent_router.router, prefix="/agent", tags=["Agent"], dependencies=auth_dep)

# OCR 路由 — 无需认证
app.include_router(ocr_router, prefix="/ocr", tags=["OCR 文档解析"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
