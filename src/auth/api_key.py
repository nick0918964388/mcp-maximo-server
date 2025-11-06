"""
API Key authentication middleware for MCP Server
Validates API keys from Dify requests
"""
from typing import Optional

from fastapi import Header, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from src.config import settings
from src.utils.logger import get_logger, set_correlation_id

logger = get_logger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> str:
    """
    Verify API key from request headers
    Supports both Authorization: Bearer <key> and X-API-Key: <key> formats
    """
    api_key = None

    # Try Authorization header first (Bearer format)
    if authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]  # Remove "Bearer " prefix
        else:
            api_key = authorization

    # Fall back to X-API-Key header
    if not api_key and x_api_key:
        api_key = x_api_key

    # Validate API key
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if api_key != settings.mcp_api_key:
        logger.warning("Invalid API key attempt", api_key_prefix=api_key[:8] if api_key else "")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("API key validated successfully")
    return api_key


async def correlation_id_middleware(request: Request, call_next):
    """
    Middleware to extract or generate correlation ID for request tracking
    Looks for X-Correlation-ID or X-Request-ID headers
    """
    correlation_id = (
        request.headers.get("x-correlation-id")
        or request.headers.get("x-request-id")
        or None
    )

    # Set correlation ID in context
    correlation_id = set_correlation_id(correlation_id)

    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id,
    )

    # Add correlation ID to response headers
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id

    return response


class APIKeyAuth:
    """Dependency class for API key authentication"""

    def __init__(self, required: bool = True):
        self.required = required

    async def __call__(
        self,
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None),
    ) -> Optional[str]:
        if not self.required:
            return None

        return await verify_api_key(authorization, x_api_key)
