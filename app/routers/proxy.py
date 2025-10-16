"""
Zoom API proxy router.

This module provides a catch-all proxy route that forwards requests to the Zoom API
with proper authentication using session credentials from Redis.
"""
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional

from app.utils.redis_client import get_session_data

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_zoom_access_token(client_id: str, client_secret: str, account_id: str) -> str:
    """
    Get a Zoom access token using Server-to-Server OAuth.
    
    Args:
        client_id: Zoom OAuth client ID
        client_secret: Zoom OAuth client secret
        account_id: Zoom account ID
    
    Returns:
        Access token string
    """
    token_url = "https://zoom.us/oauth/token"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            params={
                "grant_type": "account_credentials",
                "account_id": account_id
            },
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            logger.error(f"Failed to get Zoom access token: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to authenticate with Zoom: {response.text}"
            )


@router.api_route("/{api_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def zoom_proxy(api_path: str, request: Request):
    """
    Generic proxy for Zoom API endpoints.
    
    Handles authentication and forwards requests to Zoom API.
    Requires session_id in query parameters.
    
    Args:
        api_path: The API path to proxy (e.g., "users", "meetings", etc.)
        request: FastAPI request object
    
    Returns:
        JSON response from Zoom API
    """
    # Get session_id from query params
    session_id = request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_id is required"
        )
    
    # Get session data from Redis
    session_data = get_session_data(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Extract provider tokens (Zoom API credentials)
    provider_tokens = session_data.get("provider_tokens", {})
    api_base_url = provider_tokens.get("api_base_url", "https://api.zoom.us/v2")
    
    # Get OAuth credentials for Server-to-Server OAuth
    client_id = provider_tokens.get("client_id")
    client_secret = provider_tokens.get("client_secret")
    account_id = provider_tokens.get("account_id")
    
    if not client_id or not client_secret or not account_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Zoom OAuth credentials (client_id, client_secret, account_id) not found in session"
        )
    
    # Get access token using Server-to-Server OAuth
    try:
        access_token = await get_zoom_access_token(client_id, client_secret, account_id)
    except Exception as e:
        logger.error(f"Failed to get Zoom access token: {e}")
        raise
    
    # Build the full Zoom API URL
    url = f"{api_base_url}/{api_path}"
    
    # Get query parameters (excluding session_id)
    query_params = dict(request.query_params)
    query_params.pop("session_id", None)
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = None
    
    # Prepare headers for Zoom API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    logger.info(f"Proxying {request.method} request to Zoom API: {url}")
    
    try:
        # Make request to Zoom API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=url,
                params=query_params,
                json=body,
                headers=headers
            )
        
        # Return the response from Zoom API
        return JSONResponse(
            content=response.json() if response.content else {},
            status_code=response.status_code
        )
        
    except httpx.TimeoutException:
        logger.error(f"Timeout while calling Zoom API: {url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Zoom API request timed out"
        )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while calling Zoom API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with Zoom API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in Zoom proxy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
