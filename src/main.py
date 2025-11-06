"""
FastMCP Main Application - Maximo Integration Server
Exposes Maximo API as MCP tools for Dify agents
"""
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from src.config import settings
from src.auth.api_key import verify_api_key, correlation_id_middleware
from src.middleware.rate_limiter import rate_limit_middleware
from src.clients.maximo_client import get_maximo_client, close_maximo_client
from src.middleware.cache import get_cache_manager, close_cache_manager
from src.utils.logger import get_logger

# Import tools
from src.tools import asset_tools, workorder_tools, inventory_tools

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("Starting MCP Maximo Server", version=settings.app_version)

    # Initialize connections
    cache_manager = get_cache_manager()
    maximo_client = get_maximo_client()

    logger.info("Server started successfully")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down MCP Maximo Server")
    await close_cache_manager()
    await close_maximo_client()
    logger.info("Server shut down complete")


# Create FastMCP instance
mcp = FastMCP(
    name=settings.mcp_server_name,
    version=settings.mcp_server_version,
    lifespan=lifespan,
)


# ============================================================
# MCP TOOLS - Asset Management
# ============================================================

@mcp.tool()
async def get_asset(assetnum: str, siteid: Optional[str] = None) -> Dict[str, Any]:
    """
    Get asset details from Maximo

    Args:
        assetnum: Asset number to retrieve
        siteid: Site ID (optional)

    Returns:
        Asset details including status, location, description, etc.
    """
    return await asset_tools.get_asset(assetnum, siteid)


@mcp.tool()
async def search_assets(
    query: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    assettype: Optional[str] = None,
    siteid: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Search assets in Maximo with filters

    Args:
        query: Search text (searches description and assetnum)
        status: Filter by asset status
        location: Filter by location
        assettype: Filter by asset type
        siteid: Filter by site ID
        page_size: Maximum results to return (default: 100)

    Returns:
        List of matching assets
    """
    return await asset_tools.search_assets(query, status, location, assettype, siteid, page_size)


@mcp.tool()
async def create_asset(
    assetnum: str,
    siteid: str,
    description: str,
    assettype: Optional[str] = None,
    location: Optional[str] = None,
    status: str = "NOT READY",
) -> Dict[str, Any]:
    """
    Create a new asset in Maximo

    Args:
        assetnum: Unique asset number
        siteid: Site ID where asset will be created
        description: Asset description
        assettype: Asset type code (optional)
        location: Location code (optional)
        status: Initial status (default: "NOT READY")

    Returns:
        Created asset details
    """
    return await asset_tools.create_asset(assetnum, siteid, description, assettype, location, status)


@mcp.tool()
async def update_asset_status(
    assetnum: str,
    siteid: str,
    new_status: str,
    memo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Change asset status in Maximo

    Args:
        assetnum: Asset number to update
        siteid: Site ID
        new_status: New status value (e.g., "OPERATING", "DECOMMISSIONED")
        memo: Optional memo for status change

    Returns:
        Updated asset details
    """
    return await asset_tools.change_asset_status(assetnum, siteid, new_status, memo)


# ============================================================
# MCP TOOLS - Work Order Management
# ============================================================

@mcp.tool()
async def get_work_order(wonum: str, siteid: Optional[str] = None) -> Dict[str, Any]:
    """
    Get work order details from Maximo

    Args:
        wonum: Work order number
        siteid: Site ID (optional)

    Returns:
        Work order details including status, description, asset, etc.
    """
    return await workorder_tools.get_work_order(wonum, siteid)


@mcp.tool()
async def search_work_orders(
    query: Optional[str] = None,
    status: Optional[str] = None,
    worktype: Optional[str] = None,
    assetnum: Optional[str] = None,
    location: Optional[str] = None,
    siteid: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Search work orders in Maximo

    Args:
        query: Search text (searches description and wonum)
        status: Filter by work order status
        worktype: Filter by work type
        assetnum: Filter by asset number
        location: Filter by location
        siteid: Filter by site ID
        page_size: Maximum results (default: 100)

    Returns:
        List of matching work orders
    """
    return await workorder_tools.search_work_orders(query, status, worktype, assetnum, location, siteid, page_size)


@mcp.tool()
async def create_work_order(
    description: str,
    siteid: str,
    assetnum: Optional[str] = None,
    location: Optional[str] = None,
    worktype: str = "CM",
    priority: int = 2,
) -> Dict[str, Any]:
    """
    Create a new work order in Maximo

    Args:
        description: Work order description
        siteid: Site ID
        assetnum: Asset number (optional)
        location: Location code (optional)
        worktype: Work type code (default: "CM" for corrective maintenance)
        priority: Priority level 1-5 (default: 2)

    Returns:
        Created work order details
    """
    return await workorder_tools.create_work_order(description, siteid, assetnum, location, worktype, priority)


@mcp.tool()
async def update_work_order_status(
    wonum: str,
    siteid: str,
    new_status: str,
    memo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Change work order status in Maximo

    Args:
        wonum: Work order number
        siteid: Site ID
        new_status: New status value (e.g., "WAPPR", "INPRG", "COMP")
        memo: Optional memo for status change

    Returns:
        Updated work order details
    """
    return await workorder_tools.change_work_order_status(wonum, siteid, new_status, memo)


# ============================================================
# MCP TOOLS - Inventory Management
# ============================================================

@mcp.tool()
async def get_inventory(
    itemnum: str,
    siteid: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get inventory item details from Maximo

    Args:
        itemnum: Item number
        siteid: Site ID (optional)
        location: Storeroom location (optional)

    Returns:
        Inventory details including current balance, reorder point, etc.
    """
    return await inventory_tools.get_inventory(itemnum, siteid, location)


@mcp.tool()
async def search_inventory(
    query: Optional[str] = None,
    low_stock: bool = False,
    siteid: Optional[str] = None,
    location: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Search inventory items in Maximo

    Args:
        query: Search text (searches description and itemnum)
        low_stock: Filter items where current balance < reorder point
        siteid: Filter by site ID
        location: Filter by storeroom location
        page_size: Maximum results (default: 100)

    Returns:
        List of matching inventory items
    """
    return await inventory_tools.search_inventory(query, low_stock, siteid, location, page_size)


@mcp.tool()
async def issue_inventory(
    itemnum: str,
    quantity: float,
    siteid: str,
    location: str,
    to_wonum: Optional[str] = None,
    to_location: Optional[str] = None,
    memo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Issue inventory item from storeroom

    Args:
        itemnum: Item number to issue
        quantity: Quantity to issue
        siteid: Site ID
        location: Storeroom location to issue from
        to_wonum: Work order number to issue to (optional)
        to_location: Location to transfer to (optional)
        memo: Transaction memo (optional)

    Returns:
        Inventory transaction details
    """
    return await inventory_tools.issue_inventory(itemnum, quantity, siteid, location, to_wonum, to_location, memo)


# ============================================================
# Health Check and FastAPI App
# ============================================================

@mcp.get("/health")
async def health_check():
    """Health check endpoint"""
    cache_manager = get_cache_manager()
    maximo_client = get_maximo_client()

    cache_healthy = await cache_manager.health_check()
    maximo_healthy = await maximo_client.health_check()

    health_status = {
        "status": "healthy" if (cache_healthy and maximo_healthy) else "degraded",
        "cache": "healthy" if cache_healthy else "unhealthy",
        "maximo": "healthy" if maximo_healthy else "unhealthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }

    logger.info("Health check performed", **health_status)
    return health_status


# Get the FastAPI app
app = mcp.get_asgi_app()


# Add middleware
app.middleware("http")(correlation_id_middleware)
app.middleware("http")(rate_limit_middleware)

if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
