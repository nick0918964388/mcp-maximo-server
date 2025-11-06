"""
Configuration management for MCP Maximo Server
Using Pydantic Settings for type-safe configuration
"""
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Union


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application settings
    app_name: str = Field(default="MCP Maximo Server", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # MCP Server settings
    mcp_server_name: str = Field(default="maximo-integration-server", description="MCP server name")
    mcp_server_version: str = Field(default="1.0.0", description="MCP server version")

    # Authentication
    mcp_api_key: str = Field(..., description="API key for authenticating Dify requests to MCP server")

    # Maximo API settings
    maximo_api_url: str = Field(..., description="Maximo API base URL (e.g., https://maximo.company.com/maximo)")
    maximo_api_key: str = Field(..., description="Maximo API key for authentication")
    maximo_timeout: int = Field(default=30, description="Maximo API request timeout in seconds")
    maximo_max_retries: int = Field(default=3, description="Maximum retry attempts for Maximo API calls")

    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_enabled: bool = Field(default=True, description="Enable Redis caching")

    # Cache settings
    cache_ttl_asset: int = Field(default=600, description="Asset cache TTL in seconds (10 minutes)")
    cache_ttl_workorder: int = Field(default=300, description="Work order cache TTL in seconds (5 minutes)")
    cache_ttl_inventory: int = Field(default=600, description="Inventory cache TTL in seconds (10 minutes)")
    cache_ttl_search: int = Field(default=300, description="Search results cache TTL in seconds (5 minutes)")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=100, description="Maximum requests per minute")
    rate_limit_search_per_minute: int = Field(default=50, description="Maximum search requests per minute")
    rate_limit_create_per_minute: int = Field(default=20, description="Maximum create requests per minute")

    # Logging
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_format: str = Field(default="json", description="Log format: json or text")

    # CORS settings
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: Union[str, list[str]] = Field(default=["*"], description="Allowed CORS origins")

    # Health check
    health_check_enabled: bool = Field(default=True, description="Enable health check endpoint")

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            # If it's a single "*", return as list
            if v.strip() == "*":
                return ["*"]
            # If it's comma-separated, split it
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance"""
    return settings


# Cache configuration dictionary
CACHE_CONFIG = {
    "asset_detail": {"ttl": settings.cache_ttl_asset},
    "workorder_detail": {"ttl": settings.cache_ttl_workorder},
    "workorder_list": {"ttl": settings.cache_ttl_workorder},
    "inventory_detail": {"ttl": settings.cache_ttl_inventory},
    "inventory_stock": {"ttl": settings.cache_ttl_inventory},
    "asset_search": {"ttl": settings.cache_ttl_search},
    "workorder_search": {"ttl": settings.cache_ttl_search},
}


# Rate limit configuration dictionary
RATE_LIMIT_CONFIG = {
    "default": f"{settings.rate_limit_per_minute}/minute",
    "search": f"{settings.rate_limit_search_per_minute}/minute",
    "create": f"{settings.rate_limit_create_per_minute}/minute",
}
