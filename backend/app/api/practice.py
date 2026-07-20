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


@router.get("/exercise-records")
async def get_exercise_records():
    """获取做题记录（含做题归因分析：概念/方法/计算情况）"""
    pass


@router.get("/exercise-records/analytics")
async def get_exercise_records_analytics():
    """获取做题记录分析报告（知识点掌握度统计）"""
    pass


@router.post("/hint")
async def get_hint():
    """获取渐进式提示（思路方向 → 关键步骤 → 完整解答）"""
    pass
