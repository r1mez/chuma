"""础码 (ChuMa) — AI 引擎服务入口"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api import chat, gnn, kg
from app.dependencies import verify_service_token
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.ocr.router import router as ocr_router, set_task_manager
from app.ocr.task_manager import AsyncTaskManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化定时任务调度器和 OCR 任务管理器"""
    start_scheduler()

    # 启动 OCR 任务管理器
    ocr_manager = AsyncTaskManager()
    await ocr_manager.start()
    set_task_manager(ocr_manager)

    yield

    # 关闭 OCR 任务管理器
    await ocr_manager.shutdown()
    stop_scheduler()


app = FastAPI(title="ChuMa AI Engine", version="0.1.0", lifespan=lifespan)

auth_dep = [Depends(verify_service_token)]

app.include_router(chat.router, prefix="/rag", tags=["AI 对话"], dependencies=auth_dep)
app.include_router(gnn.router, prefix="/gnn", tags=["GNN 推荐"], dependencies=auth_dep)
app.include_router(kg.router, prefix="/kg", tags=["知识图谱"], dependencies=auth_dep)

# OCR 路由 — 无需认证
app.include_router(ocr_router, prefix="/ocr", tags=["OCR 文档解析"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
