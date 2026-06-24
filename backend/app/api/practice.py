"""题目练习路由"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/questions")
async def list_questions():
    """获取题目列表（支持按科目、难度筛选）"""
    pass


@router.get("/questions/{question_id}")
async def get_question(question_id: int):
    """获取单道题目详情"""
    pass


@router.post("/submit")
async def submit_answer():
    """提交做题答案，返回对错和解析"""
    pass


@router.get("/wrong-book")
async def get_wrong_book():
    """获取错题本（含归因分析：概念/方法/计算错误）"""
    pass


@router.get("/wrong-book/analytics")
async def get_wrong_book_analytics():
    """获取错题分析报告（薄弱知识点统计）"""
    pass


@router.post("/hint")
async def get_hint():
    """获取渐进式提示（思路方向 → 关键步骤 → 完整解答）"""
    pass
