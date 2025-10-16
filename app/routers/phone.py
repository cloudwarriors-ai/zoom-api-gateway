#!/usr/bin/env python3

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import requests

from app.utils import get_redis_client, SessionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize managers
redis_client = get_redis_client()
sm = SessionManager(redis_client)

ZOOM_API_BASE_URL = "https://api.zoom.us/v2"


def get_token_from_session(session_id: str) -> str:
    """Get Zoom access token from session ID."""
    session_data = sm.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found or expired")
    
    provider_tokens = session_data.get("provider_tokens", {})
    access_token = provider_tokens.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token found in session")
    
    return access_token


def make_zoom_request(method: str, endpoint: str, token: str, params: dict = None, data: dict = None):
    """Make a request to Zoom API."""
    url = f"{ZOOM_API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.exceptions.HTTPError as e:
        logger.error(f"Zoom API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.text
        )
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Phone Users
@router.get("/phone/users", tags=["Phone Users"])
async def list_phone_users(
    session_id: str = Query(..., description="Session ID from auth/connect"),
    page_size: int = Query(30, ge=1, le=300),
    next_page_token: Optional[str] = Query(None)
):
    """List all Zoom Phone users."""
    token = get_token_from_session(session_id)
    params = {"page_size": page_size}
    if next_page_token:
        params["next_page_token"] = next_page_token
    
    return make_zoom_request("GET", "/phone/users", token, params=params)


@router.get("/phone/users/{user_id}", tags=["Phone Users"])
async def get_phone_user(
    user_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get detailed information for a specific phone user."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/users/{user_id}", token)


@router.patch("/phone/users/{user_id}", tags=["Phone Users"])
async def update_phone_user(
    user_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Update phone user settings (extension, policies, etc.)."""
    token = get_token_from_session(session_id)
    data = await request.json()
    return make_zoom_request("PATCH", f"/phone/users/{user_id}", token, data=data)


@router.get("/phone/users/{user_id}/phone_numbers", tags=["Phone Users"])
async def get_user_phone_numbers(
    user_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get phone numbers assigned to a user."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/users/{user_id}/phone_numbers", token)


@router.post("/phone/users/{user_id}/phone_numbers", tags=["Phone Users"])
async def assign_user_phone_numbers(
    user_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Assign phone numbers to a user."""
    token = get_token_from_session(session_id)
    data = await request.json()
    return make_zoom_request("POST", f"/phone/users/{user_id}/phone_numbers", token, data=data)


@router.delete("/phone/users/{user_id}/phone_numbers/{phone_number_id}", tags=["Phone Users"])
async def unassign_user_phone_number(
    user_id: str,
    phone_number_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Unassign a phone number from a user."""
    token = get_token_from_session(session_id)
    return make_zoom_request("DELETE", f"/phone/users/{user_id}/phone_numbers/{phone_number_id}", token)


# Phone Numbers
@router.get("/phone/numbers", tags=["Phone Numbers"])
async def list_phone_numbers(
    session_id: str = Query(..., description="Session ID from auth/connect"),
    page_size: int = Query(30, ge=1, le=100),
    next_page_token: Optional[str] = Query(None)
):
    """List all phone numbers."""
    token = get_token_from_session(session_id)
    params = {"page_size": page_size}
    if next_page_token:
        params["next_page_token"] = next_page_token
    
    return make_zoom_request("GET", "/phone/numbers", token, params=params)


@router.get("/phone/numbers/{number_id}", tags=["Phone Numbers"])
async def get_phone_number(
    number_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get detailed information for a specific phone number."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/numbers/{number_id}", token)


@router.patch("/phone/numbers/{number_id}", tags=["Phone Numbers"])
async def update_phone_number(
    number_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Update phone number settings."""
    token = get_token_from_session(session_id)
    data = await request.json()
    return make_zoom_request("PATCH", f"/phone/numbers/{number_id}", token, data=data)


# Call Logs
@router.get("/phone/call_logs", tags=["Call Logs"])
async def list_call_logs(
    session_id: str = Query(..., description="Session ID from auth/connect"),
    page_size: int = Query(30, ge=1, le=300),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    type: Optional[str] = Query(None)
):
    """Retrieve call history and logs."""
    token = get_token_from_session(session_id)
    params = {"page_size": page_size}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if type:
        params["type"] = type
    
    return make_zoom_request("GET", "/phone/call_logs", token, params=params)


@router.get("/phone/call_logs/{call_id}", tags=["Call Logs"])
async def get_call_log(
    call_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get detailed information for a specific call."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/call_logs/{call_id}", token)


# Call Queues
@router.get("/phone/call_queues", tags=["Call Queues"])
async def list_call_queues(
    session_id: str = Query(..., description="Session ID from auth/connect"),
    page_size: int = Query(30, ge=1, le=100),
    next_page_token: Optional[str] = Query(None)
):
    """List all call queues."""
    token = get_token_from_session(session_id)
    params = {"page_size": page_size}
    if next_page_token:
        params["next_page_token"] = next_page_token
    
    return make_zoom_request("GET", "/phone/call_queues", token, params=params)


@router.get("/phone/call_queues/{queue_id}", tags=["Call Queues"])
async def get_call_queue(
    queue_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get detailed information for a specific call queue."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/call_queues/{queue_id}", token)


@router.patch("/phone/call_queues/{queue_id}", tags=["Call Queues"])
async def update_call_queue(
    queue_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Update call queue settings."""
    token = get_token_from_session(session_id)
    data = await request.json()
    return make_zoom_request("PATCH", f"/phone/call_queues/{queue_id}", token, data=data)


@router.get("/phone/call_queues/{queue_id}/members", tags=["Call Queues"])
async def get_call_queue_members(
    queue_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get list of members in a call queue."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", f"/phone/call_queues/{queue_id}/members", token)


@router.post("/phone/call_queues/{queue_id}/members", tags=["Call Queues"])
async def add_call_queue_members(
    queue_id: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Add members to a call queue (max 10 per request)."""
    token = get_token_from_session(session_id)
    data = await request.json()
    return make_zoom_request("POST", f"/phone/call_queues/{queue_id}/members", token, data=data)


@router.delete("/phone/call_queues/{queue_id}/members/{member_id}", tags=["Call Queues"])
async def remove_call_queue_member(
    queue_id: str,
    member_id: str,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Remove a member from a call queue."""
    token = get_token_from_session(session_id)
    return make_zoom_request("DELETE", f"/phone/call_queues/{queue_id}/members/{member_id}", token)


# Auto Receptionists
@router.get("/phone/auto_receptionists", tags=["Auto Receptionists"])
async def list_auto_receptionists(
    session_id: str = Query(..., description="Session ID from auth/connect"),
    page_size: int = Query(30, ge=1, le=100),
    next_page_token: Optional[str] = Query(None)
):
    """List all auto receptionists."""
    token = get_token_from_session(session_id)
    params = {"page_size": page_size}
    if next_page_token:
        params["next_page_token"] = next_page_token
    
    return make_zoom_request("GET", "/phone/auto_receptionists", token, params=params)


# Settings
@router.get("/phone/settings", tags=["Settings"])
async def get_phone_settings(
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get account-level phone settings."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", "/phone/settings", token)


@router.get("/phone/blocked_numbers", tags=["Settings"])
async def get_blocked_numbers(
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """Get list of blocked phone numbers."""
    token = get_token_from_session(session_id)
    return make_zoom_request("GET", "/phone/blocked_numbers", token)


# Generic Phone Proxy
@router.api_route("/phone-proxy/{api_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], tags=["Proxy"])
async def phone_proxy(
    api_path: str,
    request: Request,
    session_id: str = Query(..., description="Session ID from auth/connect")
):
    """
    Generic proxy endpoint for any Zoom Phone API call.
    
    This endpoint forwards requests to the Zoom API with proper authentication.
    Use this for any Zoom Phone endpoint not explicitly implemented above.
    
    Example: GET /phone-proxy/phone/users?session_id={session_id}
    """
    token = get_token_from_session(session_id)
    
    # Get query parameters (excluding session_id)
    params = dict(request.query_params)
    if "session_id" in params:
        del params["session_id"]
    
    # Get request body for POST/PUT/PATCH
    data = None
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            data = await request.json()
        except Exception:
            data = None
    
    # Make request to Zoom API
    return make_zoom_request(request.method, f"/{api_path}", token, params=params, data=data)
