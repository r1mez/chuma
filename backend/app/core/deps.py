"""FastAPI 公共依赖注入"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)
security_scheme_strict = HTTPBearer()


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """解析 JWT token（可选），失败时返回匿名测试用户"""
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            user_id = payload.get("sub")
            return {"id": user_id, "role": payload.get("role")}
    # 无 token 或 token 无效，返回匿名测试用户
    return {"id": 1, "role": "anonymous"}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme_strict),
    db: AsyncSession = Depends(get_db),
):
    """解析 JWT token，返回当前用户（严格认证，用于敏感接口）"""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    # TODO: 从数据库查询用户并返回
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    return {"id": user_id, "role": payload.get("role")}
