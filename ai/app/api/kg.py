"""知识图谱管理路由"""

import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Body, HTTPException

from app.config import settings
from app.kg_pipeline.models import PipelineResult
from app.kg_pipeline.queries import GraphQueryError, get_full_graph, search_nodes
from app.ocr.schemas import TaskSubmitResponse


router = APIRouter()


@router.post("/build", response_model=TaskSubmitResponse)
async def start_kg_build(
    file_path: str = Body(..., embed=True),
    graph_name: str | None = Body(default=None, embed=True),
):
    """提交知识图谱构建任务（异步）"""
    task_id = str(uuid.uuid4())

    r = aioredis.from_url(settings.REDIS_URL)
    await r.lpush("chuma:tasks", json.dumps({
        "type": "kg_build",
        "task_id": task_id,
        "file_path": file_path,
        "output_key": f"kg:result:{task_id}",
        "graph_name": graph_name,  # pass through to task worker
    }))

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/kg/build/status/{task_id}",
        result_url=f"/kg/build/result/{task_id}",
    )


@router.get("/build/status/{task_id}")
async def get_build_status(task_id: str):
    """查询构建任务状态"""
    r = aioredis.from_url(settings.REDIS_URL)
    result = await r.get(f"kg:result:{task_id}")
    if result is None:
        return {"task_id": task_id, "status": "processing"}
    return json.loads(result)


@router.get("/build/result/{task_id}")
async def get_build_result(task_id: str):
    """获取构建结果"""
    r = aioredis.from_url(settings.REDIS_URL)
    result = await r.get(f"kg:result:{task_id}")
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return PipelineResult.model_validate_json(result)


@router.get("/graph/data")
async def get_graph_data(graph_name: str | None = None):
    """获取知识图谱全量数据（节点 + 边 + 统计）"""
    try:
        data = await asyncio.get_event_loop().run_in_executor(
            None, get_full_graph, graph_name
        )
        return data
    except GraphQueryError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/graph/search")
async def search_graph_nodes(q: str, graph_name: str | None = None):
    """按名称搜索实体节点"""
    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, search_nodes, q, graph_name
        )
        return {"results": results}
    except GraphQueryError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/graph/delete")
async def delete_graph_data(graph_name: str):
    """清空并删除指定 AGE 图"""
    from app.kg_pipeline.storage import AgeStorage
    try:
        storage = AgeStorage(graph_name=graph_name)
        storage.drop_graph()
        return {"status": "ok", "graph_name": graph_name}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
