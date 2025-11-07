"""
MCP Tools for Maximo User Management
Provides user status query and account unlock operations
"""
from typing import Any, Dict, List, Optional

from src.clients.maximo_client import get_maximo_client, MaximoAPIError
from src.middleware.cache import cached, get_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


@cached('user_detail')
async def get_user_status(
    userid: str,
    _headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Get user account details and status

    Args:
        userid: User ID (login username)
        _headers: Internal parameter for additional headers (e.g., maxauth from frontend)

    Returns:
        User details dictionary including status, locked status, and failed login count
    """
    logger.info("Getting user status", userid=userid)

    try:
        client = get_maximo_client()

        # Build query parameters
        params = {
            "oslc.select": "userid,personid,displayname,status,loginid,lockedout,failedlogincount,emailaddress,primaryphone",
            "lean": "1",
        }

        # Build where clause
        params["oslc.where"] = f'userid="{userid}"'

        # Execute request
        response = await client.get("/oslc/os/mxuser", params=params, headers=_headers)

        # Extract user from response
        members = response.get("member", [])
        if not members:
            raise MaximoAPIError(f"User not found: {userid}", status_code=404)

        user = members[0]

        # Add human-readable status information
        user_info = {
            **user,
            "is_locked": user.get("lockedout", False),
            "is_active": user.get("status") == "ACTIVE",
            "failed_login_count": user.get("failedlogincount", 0),
        }

        logger.info("User status retrieved successfully", userid=userid, status=user.get("status"))

        return user_info

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error getting user status", userid=userid, error=str(e))
        raise MaximoAPIError(f"Failed to get user status: {str(e)}") from e


@cached('user_search')
async def search_users(
    query: Optional[str] = None,
    status: Optional[str] = None,
    personid: Optional[str] = None,
    locked_only: bool = False,
    page_size: int = 100,
    _headers: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search users with filters

    Args:
        query: Search query (searches in userid, displayname, personid)
        status: User status filter (e.g., ACTIVE, INACTIVE)
        personid: Person ID filter
        locked_only: If True, only return locked accounts
        page_size: Maximum number of results (default: 100)
        _headers: Internal parameter for additional headers (e.g., maxauth from frontend)

    Returns:
        List of user dictionaries
    """
    logger.info("Searching users", query=query, status=status, locked_only=locked_only)

    try:
        client = get_maximo_client()

        # Build query parameters
        params = {
            "oslc.select": "userid,personid,displayname,status,loginid,lockedout,failedlogincount,emailaddress",
            "oslc.pageSize": str(page_size),
            "lean": "1",
        }

        # Build where clause
        where_parts = []

        if query:
            # Search in userid, displayname, and personid
            where_parts.append(f'(userid~"{query}" or displayname~"{query}" or personid~"{query}")')

        if status:
            where_parts.append(f'status="{status}"')

        if personid:
            where_parts.append(f'personid="{personid}"')

        if locked_only:
            where_parts.append('lockedout=1')

        if where_parts:
            params["oslc.where"] = " and ".join(where_parts)

        # Execute request
        response = await client.get("/oslc/os/mxuser", params=params, headers=_headers)

        # Extract users from response
        users = response.get("member", [])

        # Add human-readable information to each user
        enhanced_users = []
        for user in users:
            user_info = {
                **user,
                "is_locked": user.get("lockedout", False),
                "is_active": user.get("status") == "ACTIVE",
                "failed_login_count": user.get("failedlogincount", 0),
            }
            enhanced_users.append(user_info)

        logger.info("User search completed", count=len(enhanced_users))

        return enhanced_users

    except Exception as e:
        logger.error("Error searching users", error=str(e))
        raise MaximoAPIError(f"Failed to search users: {str(e)}") from e


async def unlock_user_account(
    userid: str,
    memo: Optional[str] = None,
    _headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Unlock a user account by resetting lock status and failed login count

    Args:
        userid: User ID to unlock
        memo: Optional memo for the unlock operation
        _headers: Internal parameter for additional headers

    Returns:
        Updated user dictionary
    """
    logger.info("Unlocking user account", userid=userid)

    try:
        client = get_maximo_client()

        # First, get the user to get its ID
        user = await get_user_status(userid, _headers=_headers)

        # Get user ID or build endpoint
        user_id = user.get("_id") or user.get("maxuserid")
        if not user_id:
            # If no _id, try to extract from href
            href = user.get("href", "")
            if href:
                user_id = href.split("/")[-1]
            else:
                raise MaximoAPIError(f"Cannot determine user ID for: {userid}")

        endpoint = f"/oslc/os/mxuser/{user_id}"

        # Build update data to unlock account
        update_data = {
            "status": "ACTIVE",
            "lockedout": 0,
            "failedlogincount": 0,
        }

        if memo:
            update_data["memo"] = memo

        # Execute update
        response = await client.patch(endpoint, data=update_data, headers=_headers)

        logger.info("User account unlocked successfully", userid=userid)

        # Invalidate caches
        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern(f"get_user_status:{userid}:*")
        await cache_manager.delete_pattern("search_users:*")

        return response

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error unlocking user account", userid=userid, error=str(e))
        raise MaximoAPIError(f"Failed to unlock user account: {str(e)}") from e


async def update_user(
    userid: str,
    _headers: Optional[Dict[str, str]] = None,
    **fields_to_update
) -> Dict[str, Any]:
    """
    Update an existing user

    Args:
        userid: User ID
        _headers: Internal parameter for additional headers
        **fields_to_update: Fields to update (e.g., status="ACTIVE", emailaddress="user@example.com")

    Returns:
        Updated user dictionary
    """
    logger.info("Updating user", userid=userid, fields=list(fields_to_update.keys()))

    try:
        client = get_maximo_client()

        # First, get the user to get its ID
        user = await get_user_status(userid, _headers=_headers)

        # Get user ID or build endpoint
        user_id = user.get("_id") or user.get("maxuserid")
        if not user_id:
            href = user.get("href", "")
            if href:
                user_id = href.split("/")[-1]
            else:
                raise MaximoAPIError(f"Cannot determine user ID for: {userid}")

        endpoint = f"/oslc/os/mxuser/{user_id}"

        # Execute update
        response = await client.patch(endpoint, data=fields_to_update, headers=_headers)

        logger.info("User updated successfully", userid=userid)

        # Invalidate caches
        cache_manager = get_cache_manager()
        await cache_manager.delete_pattern(f"get_user_status:{userid}:*")
        await cache_manager.delete_pattern("search_users:*")

        return response

    except MaximoAPIError:
        raise
    except Exception as e:
        logger.error("Error updating user", userid=userid, error=str(e))
        raise MaximoAPIError(f"Failed to update user: {str(e)}") from e
