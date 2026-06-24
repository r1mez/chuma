"""础码 (ChuMa) — AI 引擎服务入口"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api import rag, gnn, kg
from app.dependencies import verify_service_token
from app.tasks.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化定时任务调度器"""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="ChuMa AI Engine", version="0.1.0", lifespan=lifespan)

auth_dep = [Depends(verify_service_token)]

app.include_router(rag.router, prefix="/rag", tags=["GraphRAG"], dependencies=auth_dep)
app.include_router(gnn.router, prefix="/gnn", tags=["GNN 推荐"], dependencies=auth_dep)
app.include_router(kg.router, prefix="/kg", tags=["知识图谱"], dependencies=auth_dep)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
