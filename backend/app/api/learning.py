"""学习管理路由"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def get_learning_dashboard():
    """获取学习仪表盘数据（进度、统计、趋势）"""
    pass


@router.get("/plan")
async def get_learning_plan():
    """获取当前学习计划"""
    pass


@router.post("/plan/generate")
async def generate_learning_plan():
    """基于当前知识水平生成个性化学习计划"""
    pass


@router.get("/progress")
async def get_learning_progress():
    """获取学习进度（知识点掌握度）"""
    pass


@router.get("/history")
async def get_learning_history():
    """获取学习历史趋势（每日做题量、正确率变化）"""
    pass
