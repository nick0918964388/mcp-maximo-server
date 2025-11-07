"""
FastMCP Main Application - Maximo Integration Server
Exposes Maximo API as MCP tools for Dify agents
"""
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from pydantic import BaseModel

from src.config import settings
from src.clients.maximo_client import get_maximo_client, close_maximo_client
from src.middleware.cache import get_cache_manager, close_cache_manager
from src.utils.logger import get_logger

# Import tools
from src.tools import asset_tools, workorder_tools, inventory_tools, user_tools

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app):
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
# MCP TOOLS - User Management
# ============================================================

@mcp.tool()
async def get_user_status(userid: str) -> Dict[str, Any]:
    """
    Get user account status and details from Maximo

    Args:
        userid: User ID (login username)

    Returns:
        User details including status, locked status, failed login count, etc.
    """
    return await user_tools.get_user_status(userid)


@mcp.tool()
async def search_users(
    query: Optional[str] = None,
    status: Optional[str] = None,
    personid: Optional[str] = None,
    locked_only: bool = False,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Search users in Maximo with filters

    Args:
        query: Search text (searches userid, displayname, personid)
        status: Filter by user status (e.g., ACTIVE, INACTIVE)
        personid: Filter by person ID
        locked_only: If True, only return locked accounts
        page_size: Maximum results to return (default: 100)

    Returns:
        List of matching users
    """
    return await user_tools.search_users(query, status, personid, locked_only, page_size)


@mcp.tool()
async def unlock_user_account(userid: str, memo: Optional[str] = None) -> Dict[str, Any]:
    """
    Unlock a user account in Maximo by resetting lock status and failed login count

    Args:
        userid: User ID to unlock
        memo: Optional memo for the unlock operation

    Returns:
        Updated user details
    """
    return await user_tools.unlock_user_account(userid, memo)


# ============================================================
# Custom HTTP Routes using FastMCP
# ============================================================

class TestToolRequest(BaseModel):
    """Request model for testing MCP tools"""
    tool: str
    params: Dict[str, Any] = {}


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request):
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
    return JSONResponse(health_status)


@mcp.custom_route("/api/test-maximo", methods=["POST"])
async def test_maximo_connection(request: Request):
    """Test Maximo API connection"""
    try:
        maximo_client = get_maximo_client()
        is_healthy = await maximo_client.health_check()

        if is_healthy:
            return JSONResponse({
                "success": True,
                "message": "Maximo connection successful",
                "maximo_url": settings.maximo_api_url,
            })
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "Maximo connection failed",
                    "maximo_url": settings.maximo_api_url,
                }
            )
    except Exception as e:
        logger.error("Maximo connection test failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error testing Maximo connection: {str(e)}",
            }
        )


@mcp.custom_route("/api/test-tool", methods=["POST"])
async def test_tool(request: Request):
    """Test individual MCP tool execution"""
    try:
        body = await request.json()
        tool_name = body.get("tool")
        params = body.get("params", {})

        # Extract maxauth from request headers if present
        maxauth = request.headers.get("maxauth")
        headers = {}
        if maxauth:
            headers["maxauth"] = maxauth
            logger.debug("Using maxauth from request header")

        # Map tool names to functions
        tool_map = {
            "get_asset": asset_tools.get_asset,
            "search_assets": asset_tools.search_assets,
            "get_work_order": workorder_tools.get_work_order,
            "search_work_orders": workorder_tools.search_work_orders,
            "get_inventory": inventory_tools.get_inventory,
            "search_inventory": inventory_tools.search_inventory,
            "get_user_status": user_tools.get_user_status,
            "search_users": user_tools.search_users,
            "unlock_user_account": user_tools.unlock_user_account,
        }

        if tool_name not in tool_map:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": list(tool_map.keys())
                }
            )

        # Execute tool with additional headers if present
        tool_func = tool_map[tool_name]
        if headers:
            params["_headers"] = headers
        result = await tool_func(**params)

        return JSONResponse({
            "success": True,
            "tool": tool_name,
            "params": params,
            "result": result,
        })

    except Exception as e:
        logger.error("Tool test failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request):
    """Redirect to test page"""
    return FileResponse("static/test.html")


@mcp.custom_route("/test", methods=["GET"])
async def test_page(request: Request):
    """Serve test page"""
    return FileResponse("static/test.html")


# ============================================================
# Create Starlette App with Middleware
# ============================================================

# Prepare middleware list
middleware_list = []

if settings.cors_enabled:
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

    middleware_list.append(
        Middleware(
            StarletteCORSMiddleware,
            allow_origins=settings.get_cors_origins_list(),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    )

# Create the HTTP app
# Use FastMCP's built-in http_app which includes all custom routes
app = mcp.http_app(middleware=middleware_list)


if __name__ == "__main__":
    # Run with SSE transport for Dify compatibility
    # This will create endpoint at / (root)
    mcp.run(transport="sse", host=settings.host, port=settings.port)
