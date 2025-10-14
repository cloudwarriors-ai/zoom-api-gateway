#!/usr/bin/env python3

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.utils import get_redis_client, SessionManager, ProviderManager

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize managers
redis_client = get_redis_client()
sm = SessionManager(redis_client)
pm = ProviderManager(
    redis_host=redis_client.connection_pool.connection_kwargs['host'],
    redis_port=redis_client.connection_pool.connection_kwargs['port'],
    redis_db=redis_client.connection_pool.connection_kwargs['db']
)


# Pydantic models
class ConnectRequest(BaseModel):
    tenant: str = Field(..., min_length=1, max_length=100, description="Tenant identifier")
    app: str = Field(..., min_length=1, max_length=100, description="Application identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "tenant": "cloudwarriors",
                "app": "zoom-gw"
            }
        }


class ConnectResponseData(BaseModel):
    session_id: str = Field(..., description="UUID of created session")
    tenant: str = Field(..., description="Tenant identifier")
    app: str = Field(..., description="Application identifier")
    expires_in: int = Field(300, description="Session TTL in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant": "cloudwarriors",
                "app": "zoom-gw",
                "expires_in": 300
            }
        }


class ConnectResponse(BaseModel):
    success: bool = Field(True, description="Operation success flag")
    data: ConnectResponseData
    message: str = Field(..., description="Human-readable result message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "tenant": "cloudwarriors",
                    "app": "zoom-gw",
                    "expires_in": 300
                },
                "message": "Zoom session created successfully"
            }
        }


class DisconnectResponse(BaseModel):
    success: bool = Field(..., description="Operation success flag")
    message: str = Field(..., description="Human-readable result message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Session disconnected successfully"
            }
        }


class StatusResponseData(BaseModel):
    authenticated: bool = Field(False, description="Zoom API authentication status")
    tenant: Optional[str] = Field(None, description="Tenant identifier from session")
    app: Optional[str] = Field(None, description="Application identifier from session")
    session_id: Optional[str] = Field(None, description="Session UUID if validated")
    expires_at: Optional[str] = Field(None, description="Session expiry timestamp (ISO 8601)")

    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "tenant": "cloudwarriors",
                "app": "zoom-gw",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "expires_at": "2025-10-14T18:20:23Z"
            }
        }


class StatusResponse(BaseModel):
    success: bool = Field(True, description="Operation success flag")
    data: StatusResponseData

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "authenticated": True,
                    "tenant": "cloudwarriors",
                    "app": "zoom-gw",
                    "expires_at": "2025-10-14T18:20:23Z"
                }
            }
        }


# Auth endpoints
@router.post("/connect",
    response_model=ConnectResponse,
    status_code=200,
    responses={
        200: {"description": "Session created successfully"},
        400: {"description": "Invalid request body"},
        404: {"description": "System credentials or provider tokens not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Authentication"]
)
async def auth_connect(body: ConnectRequest):
    """
    Issue a session for tenant/app using pre-seeded credentials in Redis.

    Creates a new session with 5-minute TTL bundling system credentials
    and provider tokens for use by the Django API Gateway.
    """
    try:
        system_creds = pm.get_system_credentials(body.tenant, body.app)
        if not system_creds:
            logger.warning(f"System credentials not found: tenant={body.tenant} app={body.app}")
            raise HTTPException(
                status_code=404,
                detail=f"System credentials not found for tenant={body.tenant} app={body.app}"
            )

        provider_data = pm.get_provider(body.tenant, 'zoom')
        if not provider_data:
            logger.warning(f"Provider 'zoom' not found for tenant={body.tenant}")
            raise HTTPException(
                status_code=404,
                detail=f"Provider 'zoom' not found for tenant={body.tenant}"
            )

        provider_tokens = {
            'api_key': provider_data.get('api_key'),
            'api_secret': provider_data.get('api_secret'),
            'account_id': provider_data.get('account_id', ''),
            'api_base_url': provider_data.get('api_base_url', 'https://api.zoom.us/v2')
        }

        session_data = sm.create_session(
            tenant=body.tenant,
            app=body.app,
            system_creds=system_creds,
            provider_tokens=provider_tokens
        )

        logger.info(f"Session created: {session_data['session_id']} for tenant={body.tenant} app={body.app}")

        return ConnectResponse(
            success=True,
            data=ConnectResponseData(
                session_id=session_data['session_id'],
                tenant=body.tenant,
                app=body.app,
                expires_in=300
            ),
            message="Zoom session created successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect",
    response_model=DisconnectResponse,
    status_code=200,
    responses={
        200: {"description": "Session disconnected successfully"},
        400: {"description": "Missing session_id parameter"},
        404: {"description": "Session not found or already expired"},
        500: {"description": "Internal server error"}
    },
    tags=["Authentication"]
)
async def auth_disconnect(session_id: str = Query(..., description="Session UUID to disconnect")):
    """
    Revoke a session by removing it from Redis.

    Once disconnected, the session_id becomes invalid and cannot be used
    for authenticated requests. This is idempotent - calling multiple times
    with the same session_id will return 404 after the first call.
    """
    try:
        deleted = sm.delete_session(session_id)

        if deleted:
            logger.info(f"Session disconnected: {session_id}")
            return DisconnectResponse(
                success=True,
                message="Session disconnected successfully"
            )
        else:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session disconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status",
    response_model=StatusResponse,
    status_code=200,
    responses={
        200: {"description": "Authentication status retrieved"},
        401: {"description": "Invalid or expired session"},
        500: {"description": "Internal server error"}
    },
    tags=["Authentication"]
)
async def auth_status(
    session_id: Optional[str] = Query(None, description="Optional session UUID to validate"),
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID for provider status")
):
    """
    Get authentication status for Zoom provider and optionally validate a session.

    Without session_id: Returns boolean flag for Zoom authentication state.
    With session_id: Validates session and returns augmented data with tenant/app/expiry.
    """
    try:
        if session_id:
            session_data = sm.get_session(session_id)

            if not session_data:
                logger.warning(f"Invalid session: {session_id}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Invalid or expired session: {session_id}"
                )

            tenant = session_data.get('tenant')
            app = session_data.get('app')
            expires_at = session_data.get('expires_at')

            provider_tokens = session_data.get('provider_tokens', {})
            has_api_key = bool(provider_tokens.get('api_key'))

            logger.info(f"Session validated: {session_id} tenant={tenant} app={app}")

            return StatusResponse(
                success=True,
                data=StatusResponseData(
                    authenticated=has_api_key,
                    tenant=tenant,
                    app=app,
                    session_id=session_id,
                    expires_at=expires_at
                )
            )

        elif tenant_id:
            try:
                provider_data = pm.get_provider(tenant_id, 'zoom')
                has_api_key = bool(provider_data and provider_data.get('api_key'))
            except:
                has_api_key = False

            return StatusResponse(
                success=True,
                data=StatusResponseData(
                    authenticated=has_api_key,
                    tenant=tenant_id
                )
            )

        else:
            return StatusResponse(
                success=True,
                data=StatusResponseData(
                    authenticated=False
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
