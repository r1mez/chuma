"""用户认证路由"""

from fastapi import APIRouter, Depends

router = APIRouter()


@router.post("/register")
async def register():
    """用户注册"""
    pass


@router.post("/login")
async def login():
    """用户登录，返回 JWT token"""
    pass


@router.get("/me")
async def get_current_user_info():
    """获取当前用户信息"""
    pass
