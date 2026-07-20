"""FastAPI 公共依赖注入"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.auth_service import AuthService

security_scheme = HTTPBearer(auto_error=False)
security_scheme_strict = HTTPBearer()


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            return {
                "id": int(payload.get("sub")),
                "user_type": payload.get("user_type", "anonymous"),
            }
    return {"id": 1, "user_type": "anonymous"}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme_strict),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    user_id = payload.get("sub")
    user_type = payload.get("user_type")
    if user_id is None or user_type is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")

    auth_service = AuthService()
    user_id_int = int(user_id)

    if user_type == "student":
        user = await auth_service.get_student_by_id(user_id_int, db)
    elif user_type == "teacher":
        user = await auth_service.get_teacher_by_id(user_id_int, db)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未知的用户类型")

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    return {"id": user_id_int, "user_type": user_type}
