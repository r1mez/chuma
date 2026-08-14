"""Authentication for internal AI -> backend callbacks."""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

service_token_header = APIKeyHeader(name="X-Service-Token", auto_error=False)


async def verify_ai_service_token(token: str | None = Depends(service_token_header)) -> None:
    if not token or token != settings.AI_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid service token",
        )
