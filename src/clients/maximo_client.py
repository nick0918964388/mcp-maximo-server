"""
Maximo API Client with connection pooling, retry logic, and error handling
"""
import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MaximoAPIError(Exception):
    """Base exception for Maximo API errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(self.message)


class MaximoAuthenticationError(MaximoAPIError):
    """Raised when authentication fails"""
    pass


class MaximoNotFoundError(MaximoAPIError):
    """Raised when resource is not found"""
    pass


class MaximoValidationError(MaximoAPIError):
    """Raised when validation fails"""
    pass


class MaximoClient:
    """
    Async HTTP client for Maximo REST API
    Implements connection pooling, retry logic, and structured error handling
    """

    def __init__(self):
        # 確保 base_url 以 / 結尾，以便正確使用 urljoin
        self.base_url = settings.maximo_api_url.rstrip("/") + "/"
        self.api_key = settings.maximo_api_key        # 用於一般 API
        self.maxauth = settings.maximo_maxauth        # 用於 whoami 端點
        self.timeout = settings.maximo_timeout
        self.max_retries = settings.maximo_max_retries

        # Configure HTTP client with connection pooling
        limits = httpx.Limits(
            max_connections=50,
            max_keepalive_connections=10,
            keepalive_expiry=30.0,
        )

        self._client: Optional[httpx.AsyncClient] = None
        self._limits = limits

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client instance"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                limits=self._limits,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close HTTP client connection"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Maximo API client closed")

    def _build_headers(self, additional_headers: Optional[Dict[str, str]] = None, use_maxauth: bool = False) -> Dict[str, str]:
        """Build HTTP headers for Maximo API requests

        Args:
            additional_headers: Optional additional headers to include
            use_maxauth: If True, use 'maxauth' header instead of 'apikey' (for whoami endpoint)
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Choose authentication header and credential based on endpoint type
        if use_maxauth:
            headers["maxauth"] = self.maxauth  # 使用 MAXIMO_MAXAUTH
        else:
            headers["apikey"] = self.api_key    # 使用 MAXIMO_API_KEY

        if additional_headers:
            headers.update(additional_headers)
        return headers

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        if endpoint.startswith("http"):
            return endpoint
        return urljoin(self.base_url, endpoint.lstrip("/"))

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from Maximo API"""
        status_code = response.status_code
        response_body = response.text

        logger.error(
            "Maximo API error",
            status_code=status_code,
            response_body=response_body[:500],  # Limit log size
        )

        # Parse error message from response if available
        try:
            error_data = response.json()
            error_message = error_data.get("Error", {}).get("message", response_body)
        except Exception:
            error_message = response_body

        # Map status codes to specific exceptions
        if status_code == 401:
            raise MaximoAuthenticationError(
                f"Authentication failed: {error_message}",
                status_code=status_code,
                response_body=response_body,
            )
        elif status_code == 404:
            raise MaximoNotFoundError(
                f"Resource not found: {error_message}",
                status_code=status_code,
                response_body=response_body,
            )
        elif status_code == 400:
            raise MaximoValidationError(
                f"Validation error: {error_message}",
                status_code=status_code,
                response_body=response_body,
            )
        else:
            raise MaximoAPIError(
                f"Maximo API error ({status_code}): {error_message}",
                status_code=status_code,
                response_body=response_body,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_maxauth: bool = False,
    ) -> Dict[str, Any]:
        """Execute GET request to Maximo API

        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Additional headers
            use_maxauth: If True, use 'maxauth' header instead of 'apikey'
        """
        client = await self._get_client()
        url = self._build_url(endpoint)
        request_headers = self._build_headers(headers, use_maxauth=use_maxauth)

        logger.debug("Maximo GET request", url=url, params=params, auth_type="maxauth" if use_maxauth else "apikey")

        try:
            response = await client.get(url, params=params, headers=request_headers)
            response.raise_for_status()

            logger.info(
                "Maximo GET success",
                url=url,
                status_code=response.status_code,
                duration_ms=response.elapsed.total_seconds() * 1000,
            )

            return response.json()

        except httpx.HTTPStatusError as e:
            self._handle_error_response(e.response)
        except httpx.TimeoutException as e:
            logger.error("Maximo API timeout", url=url, timeout=self.timeout)
            raise MaximoAPIError(f"Request timeout after {self.timeout}s") from e
        except httpx.NetworkError as e:
            logger.error("Maximo API network error", url=url, error=str(e))
            raise MaximoAPIError("Network error connecting to Maximo") from e
        except Exception as e:
            logger.error("Unexpected error in Maximo GET", url=url, error=str(e))
            raise MaximoAPIError(f"Unexpected error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute POST request to Maximo API"""
        client = await self._get_client()
        url = self._build_url(endpoint)
        request_headers = self._build_headers(headers)

        logger.debug("Maximo POST request", url=url, data_keys=list(data.keys()))

        try:
            response = await client.post(url, json=data, headers=request_headers)
            response.raise_for_status()

            logger.info(
                "Maximo POST success",
                url=url,
                status_code=response.status_code,
                duration_ms=response.elapsed.total_seconds() * 1000,
            )

            return response.json()

        except httpx.HTTPStatusError as e:
            self._handle_error_response(e.response)
        except httpx.TimeoutException as e:
            logger.error("Maximo API timeout", url=url, timeout=self.timeout)
            raise MaximoAPIError(f"Request timeout after {self.timeout}s") from e
        except httpx.NetworkError as e:
            logger.error("Maximo API network error", url=url, error=str(e))
            raise MaximoAPIError("Network error connecting to Maximo") from e
        except Exception as e:
            logger.error("Unexpected error in Maximo POST", url=url, error=str(e))
            raise MaximoAPIError(f"Unexpected error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def patch(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute PATCH request to Maximo API"""
        client = await self._get_client()
        url = self._build_url(endpoint)
        request_headers = self._build_headers(headers)

        # Add required headers for PATCH
        request_headers.update({
            "x-method-override": "PATCH",
            "patchtype": "MERGE",
        })

        logger.debug("Maximo PATCH request", url=url, data_keys=list(data.keys()))

        try:
            response = await client.patch(url, json=data, headers=request_headers)
            response.raise_for_status()

            logger.info(
                "Maximo PATCH success",
                url=url,
                status_code=response.status_code,
                duration_ms=response.elapsed.total_seconds() * 1000,
            )

            return response.json()

        except httpx.HTTPStatusError as e:
            self._handle_error_response(e.response)
        except httpx.TimeoutException as e:
            logger.error("Maximo API timeout", url=url, timeout=self.timeout)
            raise MaximoAPIError(f"Request timeout after {self.timeout}s") from e
        except httpx.NetworkError as e:
            logger.error("Maximo API network error", url=url, error=str(e))
            raise MaximoAPIError("Network error connecting to Maximo") from e
        except Exception as e:
            logger.error("Unexpected error in Maximo PATCH", url=url, error=str(e))
            raise MaximoAPIError(f"Unexpected error: {str(e)}") from e

    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Execute DELETE request to Maximo API"""
        client = await self._get_client()
        url = self._build_url(endpoint)
        request_headers = self._build_headers(headers)

        logger.debug("Maximo DELETE request", url=url)

        try:
            response = await client.delete(url, headers=request_headers)
            response.raise_for_status()

            logger.info(
                "Maximo DELETE success",
                url=url,
                status_code=response.status_code,
            )

            return True

        except httpx.HTTPStatusError as e:
            self._handle_error_response(e.response)
        except Exception as e:
            logger.error("Unexpected error in Maximo DELETE", url=url, error=str(e))
            raise MaximoAPIError(f"Unexpected error: {str(e)}") from e

    async def health_check(self) -> bool:
        """Check if Maximo API is accessible"""
        try:
            # Try to access whoami endpoint (requires maxauth header)
            await self.get("/oslc/whoami", use_maxauth=True)
            return True
        except Exception as e:
            logger.error("Maximo health check failed", error=str(e))
            return False


# Global client instance
_maximo_client: Optional[MaximoClient] = None


def get_maximo_client() -> MaximoClient:
    """Get global Maximo client instance"""
    global _maximo_client
    if _maximo_client is None:
        _maximo_client = MaximoClient()
    return _maximo_client


async def close_maximo_client():
    """Close global Maximo client instance"""
    global _maximo_client
    if _maximo_client:
        await _maximo_client.close()
        _maximo_client = None
