"""知识图谱路由"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/graph")
async def get_knowledge_graph():
    """获取知识图谱数据（节点+边），用于前端 ECharts 可视化"""
    pass


@router.get("/nodes/{node_id}")
async def get_node_detail(node_id: int):
    """获取单个知识点详情（关联题目、资源、前置知识）"""
    pass


@router.get("/nodes/{node_id}/questions")
async def get_node_questions(node_id: int):
    """获取某知识点下的练习题"""
    pass
