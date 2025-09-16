from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class MCPRequest(BaseModel):
    """Base model for all MCP requests"""
    version: str = Field("1.0", description="MCP protocol version")
    request_type: str = Field(..., description="Type of MCP request")
    
    class Config:
        schema_extra = {
            "example": {
                "version": "1.0",
                "request_type": "extract"
            }
        }


class ExtractRequest(MCPRequest):
    """Request model for extracting data from Zoom API"""
    request_type: str = "extract"
    resource_type: str = Field(..., description="Type of resource to extract (meetings, recordings, users, etc.)")
    time_range: Optional[Dict[str, str]] = Field(
        None, 
        description="Time range for data extraction (start_time, end_time in ISO format)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional filters for the extraction"
    )
    pagination: Optional[Dict[str, int]] = Field(
        None, 
        description="Pagination parameters (page_size, page_number)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "version": "1.0",
                "request_type": "extract",
                "resource_type": "meetings",
                "time_range": {
                    "start_time": "2023-01-01T00:00:00Z",
                    "end_time": "2023-01-31T23:59:59Z"
                },
                "filters": {
                    "type": "scheduled",
                    "status": "completed"
                },
                "pagination": {
                    "page_size": 100,
                    "page_number": 1
                }
            }
        }


class TransformRequest(MCPRequest):
    """Request model for transforming extracted Zoom data"""
    request_type: str = "transform"
    extract_job_id: str = Field(..., description="ID of the extraction job containing data to transform")
    job_type_code: str = Field(..., description="Job type code for the transformation (e.g., 'rc_zoom_sites')")
    source_platform: str = Field(..., description="Source platform for the data")
    target_platform: str = Field(..., description="Target platform for the transformed data")
    data: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
        ..., 
        description="Data to transform"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "version": "1.0",
                "request_type": "transform",
                "extract_job_id": "123e4567-e89b-12d3-a456-426614174000",
                "job_type_code": "rc_zoom_sites",
                "source_platform": "ringcentral",
                "target_platform": "zoom",
                "data": {
                    "id": "123",
                    "name": "Main Office",
                    "businessAddress": {
                        "street": "123 Main St",
                        "city": "San Francisco",
                        "state": "CA",
                        "zip": "94105",
                        "country": "US"
                    }
                }
            }
        }


class LoadRequest(MCPRequest):
    """Request model for loading transformed data to target platform"""
    request_type: str = "load"
    transform_job_id: str = Field(..., description="ID of the transformation job containing data to load")
    target_platform: str = Field(..., description="Target platform for data loading")
    target_resource: str = Field(..., description="Target resource type in the destination platform")
    options: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional options for the load operation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "version": "1.0",
                "request_type": "load",
                "transform_job_id": "123e4567-e89b-12d3-a456-426614174000",
                "target_platform": "ringcentral",
                "target_resource": "meetings",
                "options": {
                    "update_existing": True,
                    "batch_size": 50
                }
            }
        }


class MCPResponse(BaseModel):
    """Standard response model for MCP operations"""
    request_id: str = Field(..., description="Unique identifier for the request")
    status: str = Field(..., description="Status of the request (accepted, in_progress, completed, failed)")
    message: str = Field(..., description="Human-readable message about the request")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details about the operation")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "accepted",
                "message": "Request accepted and queued for processing",
                "details": None
            }
        }


class StatusResponse(BaseModel):
    """Response model for status check operations"""
    request_id: str
    operation: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    results: Optional[Dict[str, Any]] = Field(None, description="Operation results if completed")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "operation": "extract",
                "status": "in_progress",
                "created_at": "2023-07-24T10:30:00Z",
                "updated_at": "2023-07-24T10:35:00Z",
                "error_message": None,
                "progress": 45.5,
                "results": None
            }
        }


class ExtractResult(BaseModel):
    """Model for extraction results"""
    job_id: str
    resource_type: str
    total_records: int
    extracted_records: int
    resource_ids: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "resource_type": "meetings",
                "total_records": 150,
                "extracted_records": 150,
                "resource_ids": ["123", "456", "789"]
            }
        }


class TransformResult(BaseModel):
    """Model for transformation results"""
    job_id: str
    source_records: int
    transformed_records: int
    target_format: str
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "source_records": 150,
                "transformed_records": 148,
                "target_format": "ringcentral"
            }
        }


class LoadResult(BaseModel):
    """Model for load results"""
    job_id: str
    total_records: int
    loaded_records: int
    skipped_records: int
    target_platform: str
    target_resource: str
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_records": 148,
                "loaded_records": 145,
                "skipped_records": 3,
                "target_platform": "ringcentral",
                "target_resource": "meetings"
            }
        }