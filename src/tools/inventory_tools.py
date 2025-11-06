"""
MCP Tools for Maximo Inventory Management
"""
from typing import Any, Dict, List, Optional

from src.clients.maximo_client import get_maximo_client, MaximoAPIError
from src.middleware.cache import cached, get_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@cached('inventory_detail')
async def get_inventory(itemnum: str, siteid: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
    """Get inventory item details"""
    logger.info("Getting inventory", itemnum=itemnum, siteid=siteid, location=location)

    try:
        client = get_maximo_client()

        params = {
            "oslc.select": "itemnum,siteid,location,description,curbal,reorder,status,binnum",
            "lean": "1",
        }

        where_parts = [f"itemnum=\"{itemnum}\""]
        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")
        if location:
            where_parts.append(f"location=\"{location}\"")

        params["oslc.where"] = " and ".join(where_parts)

        response = await client.get("/oslc/os/mxapiinventory", params=params)

        members = response.get("member", [])
        if not members:
            raise MaximoAPIError(f"Inventory item not found: {itemnum}", status_code=404)

        item = members[0]
        logger.info("Inventory item retrieved successfully", itemnum=itemnum)

        return item

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error getting inventory", itemnum=itemnum, error=str(e))
        raise MaximoAPIError(f"Failed to get inventory: {str(e)}") from e


@cached('inventory_stock')
async def search_inventory(
    query: Optional[str] = None,
    low_stock: bool = False,
    siteid: Optional[str] = None,
    location: Optional[str] = None,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """Search inventory items"""
    logger.info("Searching inventory", query=query, low_stock=low_stock)

    try:
        client = get_maximo_client()

        params = {
            "oslc.select": "itemnum,siteid,location,description,curbal,reorder,status",
            "oslc.pageSize": str(page_size),
            "lean": "1",
        }

        where_parts = []

        if query:
            where_parts.append(f"(description~\"{query}\" or itemnum~\"{query}\")")

        if low_stock:
            where_parts.append("curbal<reorder")

        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")

        if location:
            where_parts.append(f"location=\"{location}\"")

        if where_parts:
            params["oslc.where"] = " and ".join(where_parts)

        response = await client.get("/oslc/os/mxapiinventory", params=params)

        items = response.get("member", [])
        logger.info("Inventory search completed", count=len(items))

        return items

    except Exception as e:
        logger.error("Error searching inventory", error=str(e))
        raise MaximoAPIError(f"Failed to search inventory: {str(e)}") from e


async def issue_inventory(
    itemnum: str,
    quantity: float,
    siteid: str,
    location: str,
    to_wonum: Optional[str] = None,
    to_location: Optional[str] = None,
    memo: Optional[str] = None,
) -> Dict[str, Any]:
    """Issue inventory item"""
    logger.info("Issuing inventory", itemnum=itemnum, quantity=quantity)

    try:
        client = get_maximo_client()

        issue_data = {
            "itemnum": itemnum,
            "quantity": quantity,
            "siteid": siteid,
            "location": location,
            "transtype": "ISSUE",
        }

        if to_wonum:
            issue_data["wonum"] = to_wonum

        if to_location:
            issue_data["tolocation"] = to_location

        if memo:
            issue_data["memo"] = memo

        response = await client.post("/oslc/os/mxapiinvtrans", data=issue_data)

        logger.info("Inventory issued successfully", itemnum=itemnum, quantity=quantity)

        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern(f"get_inventory:{itemnum}:*")
        await cache_manager.delete_pattern("search_inventory:*")

        return response

    except Exception as e:
        logger.error("Error issuing inventory", itemnum=itemnum, error=str(e))
        raise MaximoAPIError(f"Failed to issue inventory: {str(e)}") from e
