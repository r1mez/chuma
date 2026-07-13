"""ChuMa AI Engine"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api import chat, gnn, kg
from app.dependencies import verify_service_token
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.tasks.worker import start_worker
from app.ocr.router import router as ocr_router, set_task_manager
from app.ocr.task_manager import AsyncTaskManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()

    ocr_manager = AsyncTaskManager()
    await ocr_manager.start()
    set_task_manager(ocr_manager)

    worker_task = asyncio.create_task(start_worker())

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
app.include_router(ocr_router, prefix="/ocr", tags=["OCR"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
