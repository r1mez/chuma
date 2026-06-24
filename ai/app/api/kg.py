"""知识图谱管理路由"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/extract")
async def start_extraction():
    """提交知识图谱抽取任务（异步，从教材/课件中提取）"""
    pass


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """查询抽取任务状态"""
    pass


@router.get("/search")
async def search_kg():
    """在知识图谱中语义搜索"""
    pass
