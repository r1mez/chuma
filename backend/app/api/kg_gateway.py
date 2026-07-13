"""知识图谱网关 — 代理转发到 ai/ 服务的 KG 模块"""

import os
import tempfile

import httpx
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.config import settings

router = APIRouter()

KG_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "kg_uploads")


def _ai_headers() -> dict[str, str]:
    return {"X-Service-Token": settings.AI_SERVICE_TOKEN}


async def _proxy(request: Request, method: str, path: str):
    """通用代理转发"""
    params = dict(request.query_params)
    kwargs = {"headers": _ai_headers(), "params": params, "timeout": 60.0}
    if method == "POST":
        kwargs["json"] = await request.json()

    async with httpx.AsyncClient() as client:
        response = await client.request(method, f"{settings.AI_SERVICE_URL}{path}", **kwargs)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


@router.post("/build")
async def start_kg_build(file: UploadFile = File(...)):
    """提交知识图谱构建任务 — 接收文件上传，保存后转发到 AI 引擎"""
    os.makedirs(KG_UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(KG_UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.AI_SERVICE_URL}/kg/build",
            headers=_ai_headers(),
            json={"file_path": file_path},
        )
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


@router.get("/build/status/{task_id}")
async def get_build_status(task_id: str, request: Request):
    """查询构建任务状态"""
    return await _proxy(request, "GET", f"/kg/build/status/{task_id}")


@router.get("/build/result/{task_id}")
async def get_build_result(task_id: str, request: Request):
    """获取构建结果"""
    return await _proxy(request, "GET", f"/kg/build/result/{task_id}")


@router.get("/graph/data")
async def get_graph_data(request: Request):
    """获取知识图谱全量数据"""
    return await _proxy(request, "GET", "/kg/graph/data")


@router.get("/graph/search")
async def search_graph_nodes(request: Request):
    """搜索知识图谱节点"""
    return await _proxy(request, "GET", "/kg/graph/search")
