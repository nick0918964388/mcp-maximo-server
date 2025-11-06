"""
MCP Tools for Maximo Asset Management
Provides create, update, and search operations for assets
"""
from typing import Any, Dict, List, Optional

from src.clients.maximo_client import get_maximo_client, MaximoAPIError
from src.middleware.cache import cached, get_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@cached('asset_detail')
async def get_asset(
    assetnum: str,
    siteid: Optional[str] = None,
    _headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Get asset details by asset number

    Args:
        assetnum: Asset number
        siteid: Site ID (optional)
        _headers: Internal parameter for additional headers (e.g., maxauth from frontend)

    Returns:
        Asset details dictionary
    """
    logger.info("Getting asset", assetnum=assetnum, siteid=siteid)

    try:
        client = get_maximo_client()

        # Build query parameters
        params = {
            "oslc.select": "assetnum,siteid,description,status,location,assettype,serialnum,manufacturer,model",
            "lean": "1",
        }

        # Build where clause
        where_parts = [f"assetnum=\"{assetnum}\""]
        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")

        params["oslc.where"] = " and ".join(where_parts)

        # Execute request
        response = await client.get("/oslc/os/mxapiasset", params=params, headers=_headers)

        # Extract asset from response
        members = response.get("member", [])
        if not members:
            raise MaximoAPIError(f"Asset not found: {assetnum}", status_code=404)

        asset = members[0]
        logger.info("Asset retrieved successfully", assetnum=assetnum)

        return asset

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error getting asset", assetnum=assetnum, error=str(e))
        raise MaximoAPIError(f"Failed to get asset: {str(e)}") from e


@cached('asset_search')
async def search_assets(
    query: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    assettype: Optional[str] = None,
    siteid: Optional[str] = None,
    page_size: int = 100,
    _headers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search assets with filters

    Args:
        query: Search query (searches in description and assetnum)
        status: Asset status filter
        location: Location filter
        assettype: Asset type filter
        siteid: Site ID filter
        page_size: Maximum number of results (default: 100)
        _headers: Internal parameter for additional headers (e.g., maxauth from frontend)

    Returns:
        List of asset dictionaries
    """
    logger.info("Searching assets", query=query, status=status, location=location)

    try:
        client = get_maximo_client()

        # Build query parameters
        params = {
            "oslc.select": "assetnum,siteid,description,status,location,assettype,serialnum",
            "oslc.pageSize": str(page_size),
            "lean": "1",
        }

        # Build where clause
        where_parts = []

        if query:
            # Search in description and assetnum
            where_parts.append(f"(description~\"{query}\" or assetnum~\"{query}\")")

        if status:
            where_parts.append(f"status=\"{status}\"")

        if location:
            where_parts.append(f"location=\"{location}\"")

        if assettype:
            where_parts.append(f"assettype=\"{assettype}\"")

        if siteid:
            where_parts.append(f"siteid=\"{siteid}\"")

        if where_parts:
            params["oslc.where"] = " and ".join(where_parts)

        # Execute request
        response = await client.get("/oslc/os/mxapiasset", params=params, headers=_headers)

        # Extract assets from response
        assets = response.get("member", [])
        logger.info("Assets search completed", count=len(assets))

        return assets

    except Exception as e:
        logger.error("Error searching assets", error=str(e))
        raise MaximoAPIError(f"Failed to search assets: {str(e)}") from e


async def create_asset(
    assetnum: str,
    siteid: str,
    description: str,
    assettype: Optional[str] = None,
    location: Optional[str] = None,
    status: str = "NOT READY",
    **additional_fields
) -> Dict[str, Any]:
    """
    Create a new asset in Maximo

    Args:
        assetnum: Asset number (unique identifier)
        siteid: Site ID
        description: Asset description
        assettype: Asset type (optional)
        location: Location (optional)
        status: Initial status (default: NOT READY)
        **additional_fields: Additional asset fields

    Returns:
        Created asset dictionary
    """
    logger.info("Creating asset", assetnum=assetnum, siteid=siteid)

    try:
        client = get_maximo_client()

        # Build asset data
        asset_data = {
            "assetnum": assetnum,
            "siteid": siteid,
            "description": description,
            "status": status,
        }

        if assettype:
            asset_data["assettype"] = assettype

        if location:
            asset_data["location"] = location

        # Add additional fields
        asset_data.update(additional_fields)

        # Execute request
        response = await client.post("/oslc/os/mxapiasset", data=asset_data)

        logger.info("Asset created successfully", assetnum=assetnum)

        # Invalidate asset search cache
        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern("search_assets:*")

        return response

    except Exception as e:
        logger.error("Error creating asset", assetnum=assetnum, error=str(e))
        raise MaximoAPIError(f"Failed to create asset: {str(e)}") from e


async def update_asset(
    assetnum: str,
    siteid: str,
    **fields_to_update
) -> Dict[str, Any]:
    """
    Update an existing asset

    Args:
        assetnum: Asset number
        siteid: Site ID
        **fields_to_update: Fields to update (e.g., description="New desc", status="ACTIVE")

    Returns:
        Updated asset dictionary
    """
    logger.info("Updating asset", assetnum=assetnum, siteid=siteid, fields=list(fields_to_update.keys()))

    try:
        client = get_maximo_client()

        # First, get the asset to get its href/ID
        asset = await get_asset(assetnum, siteid)

        # Get asset href or build endpoint
        asset_id = asset.get("_id") or asset.get("assetuid")
        endpoint = f"/oslc/os/mxapiasset/{asset_id}"

        # Execute update
        response = await client.patch(endpoint, data=fields_to_update)

        logger.info("Asset updated successfully", assetnum=assetnum)

        # Invalidate caches
        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern(f"get_asset:{assetnum}:*")
        await cache_manager.delete_pattern("search_assets:*")

        return response

    except Exception as e:
        logger.error("Error updating asset", assetnum=assetnum, error=str(e))
        raise MaximoAPIError(f"Failed to update asset: {str(e)}") from e


async def change_asset_status(
    assetnum: str,
    siteid: str,
    new_status: str,
    memo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Change asset status

    Args:
        assetnum: Asset number
        siteid: Site ID
        new_status: New status value
        memo: Optional memo for status change

    Returns:
        Updated asset dictionary
    """
    logger.info("Changing asset status", assetnum=assetnum, new_status=new_status)

    try:
        update_data = {"status": new_status}

        if memo:
            update_data["memo"] = memo

        result = await update_asset(assetnum, siteid, **update_data)

        logger.info("Asset status changed successfully", assetnum=assetnum, new_status=new_status)

        return result

    except Exception as e:
        logger.error("Error changing asset status", assetnum=assetnum, error=str(e))
        raise MaximoAPIError(f"Failed to change asset status: {str(e)}") from e
