"""
MCP Tools for Maximo Work Order Management
"""
from typing import Any, Dict, List, Optional

from src.clients.maximo_client import get_maximo_client, MaximoAPIError
from src.middleware.cache import cached, get_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@cached('workorder_detail')
async def get_work_order(
    wonum: str,
    siteid: Optional[str] = None,
    _headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Get work order details by work order number"""
    logger.info("Getting work order", wonum=wonum, siteid=siteid)

    try:
        client = get_maximo_client()

        params = {
            "oslc.select": "wonum,siteid,description,status,worktype,assetnum,location,priority,reportedby,reportdate",
            "lean": "1",
        }

        where_parts = [f"wonum=\"{wonum}\""]
        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")

        params["oslc.where"] = " and ".join(where_parts)

        response = await client.get("/oslc/os/mxwo", params=params, headers=_headers)

        members = response.get("member", [])
        if not members:
            raise MaximoAPIError(f"Work order not found: {wonum}", status_code=404)

        wo = members[0]
        logger.info("Work order retrieved successfully", wonum=wonum)

        return wo

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error getting work order", wonum=wonum, error=str(e))
        raise MaximoAPIError(f"Failed to get work order: {str(e)}") from e


@cached('workorder_list')
async def search_work_orders(
    query: Optional[str] = None,
    status: Optional[str] = None,
    worktype: Optional[str] = None,
    assetnum: Optional[str] = None,
    location: Optional[str] = None,
    siteid: Optional[str] = None,
    page_size: int = 100,
    _headers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Search work orders with filters"""
    logger.info("Searching work orders", query=query, status=status)

    try:
        client = get_maximo_client()

        params = {
            "oslc.select": "wonum,siteid,description,status,worktype,assetnum,location,priority",
            "oslc.pageSize": str(page_size),
            "lean": "1",
        }

        where_parts = []

        if query:
            where_parts.append(f"(description~\"{query}\" or wonum~\"{query}\")")

        if status:
            where_parts.append(f"status=\"{status}\"")

        if worktype:
            where_parts.append(f"worktype=\"{worktype}\"")

        if assetnum:
            where_parts.append(f"assetnum=\"{assetnum}\"")

        if location:
            where_parts.append(f"location=\"{location}\"")

        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")

        if where_parts:
            params["oslc.where"] = " and ".join(where_parts)

        response = await client.get("/oslc/os/mxwo", params=params, headers=_headers)

        work_orders = response.get("member", [])
        logger.info("Work orders search completed", count=len(work_orders))

        return work_orders

    except Exception as e:
        logger.error("Error searching work orders", error=str(e))
        raise MaximoAPIError(f"Failed to search work orders: {str(e)}") from e


async def create_work_order(
    description: str,
    siteid: str,
    assetnum: Optional[str] = None,
    location: Optional[str] = None,
    worktype: Optional[str] = "CM",
    priority: int = 2,
    **additional_fields
) -> Dict[str, Any]:
    """Create a new work order"""
    logger.info("Creating work order", description=description, siteid=siteid)

    try:
        client = get_maximo_client()

        wo_data = {
            "description": description,
            "siteid": siteid,
            "worktype": worktype,
            "priority": priority,
        }

        if assetnum:
            wo_data["assetnum"] = assetnum

        if location:
            wo_data["location"] = location

        wo_data.update(additional_fields)

        response = await client.post("/oslc/os/mxwo", data=wo_data)

        logger.info("Work order created successfully", wonum=response.get("wonum"))

        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern("search_work_orders:*")

        return response

    except Exception as e:
        logger.error("Error creating work order", error=str(e))
        raise MaximoAPIError(f"Failed to create work order: {str(e)}") from e


async def update_work_order(wonum: str, siteid: str, **fields_to_update) -> Dict[str, Any]:
    """Update an existing work order"""
    logger.info("Updating work order", wonum=wonum, fields=list(fields_to_update.keys()))

    try:
        client = get_maximo_client()

        wo = await get_work_order(wonum, siteid)

        wo_id = wo.get("_id") or wo.get("workorderid")
        endpoint = f"/oslc/os/mxwo/{wo_id}"

        response = await client.patch(endpoint, data=fields_to_update)

        logger.info("Work order updated successfully", wonum=wonum)

        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern(f"get_work_order:{wonum}:*")
        await cache_manager.delete_pattern("search_work_orders:*")

        return response

    except Exception as e:
        logger.error("Error updating work order", wonum=wonum, error=str(e))
        raise MaximoAPIError(f"Failed to update work order: {str(e)}") from e


async def change_work_order_status(
    wonum: str,
    siteid: str,
    new_status: str,
    memo: Optional[str] = None
) -> Dict[str, Any]:
    """Change work order status"""
    logger.info("Changing work order status", wonum=wonum, new_status=new_status)

    try:
        update_data = {"status": new_status}

        if memo:
            update_data["memo"] = memo

        result = await update_work_order(wonum, siteid, **update_data)

        logger.info("Work order status changed", wonum=wonum, new_status=new_status)

        return result

    except Exception as e:
        logger.error("Error changing work order status", wonum=wonum, error=str(e))
        raise MaximoAPIError(f"Failed to change work order status: {str(e)}") from e
