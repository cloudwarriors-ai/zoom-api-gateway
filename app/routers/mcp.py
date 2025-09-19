import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Union, Dict, Any, List
import logging

from app.database.session import get_db
from app.schemas.mcp import (
    MCPRequest, 
    MCPResponse, 
    ExtractRequest, 
    TransformRequest, 
    LoadRequest,
    StatusResponse
)
from app.database.models import MCPRequest as MCPRequestModel, SSOTFieldMapping

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/extract", response_model=MCPResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_data(
    request: ExtractRequest,
    db: Session = Depends(get_db)
):
    """
    MCP endpoint for extracting data from Zoom API
    
    This endpoint accepts extraction requests with parameters for:
    - Resource type (meetings, recordings, users, etc.)
    - Time range for data extraction
    - Filters and other extraction parameters
    
    Returns a request ID that can be used to check the status of the extraction
    """
    logger.info(f"Received extract request for resource type: {request.resource_type}")
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    # Create a new MCP request record
    mcp_request = MCPRequestModel(
        request_id=request_id,
        operation="extract",
        parameters=request.dict(),
        status="pending"
    )
    
    # Save to database
    db.add(mcp_request)
    db.commit()
    db.refresh(mcp_request)
    
    # In a real implementation, this would trigger an async task
    # to perform the actual data extraction
    
    return MCPResponse(
        request_id=request_id,
        status="accepted",
        message="Extraction request accepted and queued for processing"
    )


@router.post("/transform", response_model=MCPResponse, status_code=status.HTTP_202_ACCEPTED)
async def transform_data(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    MCP endpoint for transforming data
    
    This endpoint accepts transformation requests with:
    - Job type code for the transformation
    - Source and target platforms
    - Data to transform
    
    Returns a request ID that can be used to check the status of the transformation
    """
    logger.info(f"Received transform request: {request}")
    
    # Import platform dispatcher factory
    from app.dispatchers.platform_dispatcher_factory import PlatformDispatcherFactory
    from app.core.exceptions import TransformationError
    
    try:
        # Handle raw MCP payload from main ETL system
        if "method" in request and "params" in request:
            method = request["method"]
            params = request["params"]
            
            if method == "transform_raw":
                job_type_code = params.get("job_type")
                source_platform = params.get("source_format", "ringcentral") 
                target_platform = params.get("target_format", "zoom")
                raw_data = params.get("raw_data", {})
            elif method == "transform_from_ssot":
                job_type_code = params.get("job_type")
                source_platform = "ssot"
                target_platform = "zoom"
                raw_data = params.get("ssot_data", {})
            else:
                raise ValueError(f"Unsupported MCP method: {method}")
        else:
            raise ValueError("Invalid MCP request format - missing method and params")
        
        logger.info(f"Processing transformation: {source_platform} -> {target_platform}, job_type: {job_type_code}")
        
        # Use platform dispatcher factory to handle transformation
        transformed_data = PlatformDispatcherFactory.transform_data(
            source_platform=source_platform,
            target_platform=target_platform,
            job_type_code=job_type_code,
            raw_data=raw_data,
            job=None
        )
        
        logger.info(f"Transform completed successfully for job_type: {job_type_code}")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create a new MCP request record (exclude large data from parameters)
        parameters_to_store = {k: v for k, v in request.items() if k != "raw_data"}
        mcp_request = MCPRequestModel(
            request_id=request_id,
            operation="transform",
            parameters=parameters_to_store,
            status="completed"
        )
        
        # Save to database
        db.add(mcp_request)
        db.commit()
        db.refresh(mcp_request)
        
        return MCPResponse(
            request_id=request_id,
            status="completed",
            message=f"Transformation completed for job_type_code: {job_type_code}",
            details={
                "transformed_data": transformed_data,
                "job_type_code": job_type_code,
                "source_platform": source_platform,
                "target_platform": target_platform
            }
        )
    except TransformationError as e:
        logger.error(f"Transformation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transformation error: {str(e)}"
        )
    except Exception as e:
        import traceback
        logger.error(f"Error transforming data: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transforming data: {str(e)}"
        )


@router.post("/load", response_model=MCPResponse, status_code=status.HTTP_202_ACCEPTED)
async def load_data(
    request: LoadRequest,
    db: Session = Depends(get_db)
):
    """
    MCP endpoint for loading transformed data to target platform
    
    This endpoint accepts load requests with:
    - Source data reference (from a previous transformation)
    - Target platform information
    - Load options and configurations
    
    Returns a request ID that can be used to check the status of the load operation
    """
    logger.info(f"Received load request for transform job: {request.transform_job_id}")
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    # Create a new MCP request record
    mcp_request = MCPRequestModel(
        request_id=request_id,
        operation="load",
        parameters=request.dict(),
        status="pending"
    )
    
    # Save to database
    db.add(mcp_request)
    db.commit()
    db.refresh(mcp_request)
    
    # In a real implementation, this would trigger an async task
    # to perform the actual data loading
    
    return MCPResponse(
        request_id=request_id,
        status="accepted",
        message="Load request accepted and queued for processing"
    )


@router.get("/status/{request_id}", response_model=StatusResponse)
async def get_status(
    request_id: str,
    db: Session = Depends(get_db)
):
    """
    Check the status of an MCP request
    
    Returns the current status of the request, including:
    - Operation type
    - Current status
    - Progress information
    - Results or error messages if available
    """
    logger.info(f"Checking status for request ID: {request_id}")
    
    # Query the database for the request
    mcp_request = db.query(MCPRequestModel).filter(MCPRequestModel.request_id == request_id).first()
    
    if not mcp_request:
        logger.warning(f"Request ID not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request ID {request_id} not found"
        )
    
    return StatusResponse(
        request_id=mcp_request.request_id,
        operation=mcp_request.operation,
        status=mcp_request.status,
        created_at=mcp_request.created_at,
        updated_at=mcp_request.updated_at,
        error_message=mcp_request.error_message
    )


@router.get("/platforms")
async def get_supported_platforms():
    """
    Get all supported platform combinations for transformations.
    
    Returns:
        Dictionary with supported source->target platform combinations
        and available job types for each combination.
    """
    from app.dispatchers.platform_dispatcher_factory import PlatformDispatcherFactory
    
    try:
        # Get supported platform combinations
        supported_platforms = PlatformDispatcherFactory.get_supported_platforms()
        
        # Get detailed information for each combination
        platform_details = {}
        for source_platform, target_platforms in supported_platforms.items():
            platform_details[source_platform] = {}
            
            for target_platform in target_platforms:
                try:
                    # Get dispatcher for this combination
                    dispatcher = PlatformDispatcherFactory.get_dispatcher(source_platform, target_platform)
                    
                    # Get supported job types
                    supported_job_types = dispatcher.get_supported_job_types()
                    
                    platform_details[source_platform][target_platform] = {
                        "supported_job_types": supported_job_types,
                        "dispatcher_class": dispatcher.__class__.__name__
                    }
                except Exception as e:
                    platform_details[source_platform][target_platform] = {
                        "error": f"Failed to get dispatcher info: {str(e)}"
                    }
        
        return {
            "supported_combinations": platform_details,
            "summary": {
                "total_source_platforms": len(supported_platforms),
                "total_combinations": sum(len(targets) for targets in supported_platforms.values())
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting supported platforms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting supported platforms: {str(e)}"
        )


# Data Migration Endpoints
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.schemas.mcp import FieldMappingModel

class JobTypeData(BaseModel):
    id: int
    uuid: str
    code: str
    name: str
    description: Optional[str] = None
    source_platform_id: Optional[int] = None
    target_platform_id: Optional[int] = None
    prompt: Optional[str] = None
    is_extraction_only: bool = False
    jobtype_dependencies: Optional[Dict[str, Any]] = None

class ExtractorData(BaseModel):
    id: int
    uuid: str
    job_type_id: int
    platform_id: int
    extraction_plan: Dict[str, Any]
    group_id: Optional[int] = None
    is_default: bool = False

class LoaderData(BaseModel):
    id: int
    uuid: str
    job_type_id: int
    platform_id: int
    loading_plan: Dict[str, Any]
    group_id: Optional[int] = None
    is_default: bool = False

class TransformerData(BaseModel):
    id: int
    uuid: str
    name: str
    description: Optional[str] = None
    job_type_id: int
    transformation_config: str
    is_active: bool = True
    is_default: bool = False
    group_id: Optional[int] = None


@router.post("/job-types")
async def create_job_type(data: JobTypeData, db: Session = Depends(get_db)):
    """Create or update job type configuration."""
    from app.database.models import JobTypeConfig
    
    # Check if already exists
    existing = db.query(JobTypeConfig).filter(JobTypeConfig.id == data.id).first()
    
    if existing:
        # Update existing
        for key, value in data.dict().items():
            setattr(existing, key, value)
        db.commit()
        logger.info(f"Updated JobType {data.id}")
    else:
        # Create new
        job_type = JobTypeConfig(**data.dict())
        db.add(job_type)
        db.commit()
        logger.info(f"Created JobType {data.id}")
    
    return {"status": "success", "action": "updated" if existing else "created"}


@router.post("/extractors")
async def create_extractor(data: ExtractorData, db: Session = Depends(get_db)):
    """Create or update extractor configuration."""
    from app.database.models import ExtractorConfig
    
    existing = db.query(ExtractorConfig).filter(ExtractorConfig.id == data.id).first()
    
    if existing:
        for key, value in data.dict().items():
            setattr(existing, key, value)
        db.commit()
        logger.info(f"Updated ExtractorConfig {data.id}")
    else:
        extractor = ExtractorConfig(**data.dict())
        db.add(extractor)
        db.commit()
        logger.info(f"Created ExtractorConfig {data.id}")
    
    return {"status": "success", "action": "updated" if existing else "created"}


@router.post("/loaders")
async def create_loader(data: LoaderData, db: Session = Depends(get_db)):
    """Create or update loader configuration."""
    from app.database.models import LoaderConfig
    
    existing = db.query(LoaderConfig).filter(LoaderConfig.id == data.id).first()
    
    if existing:
        for key, value in data.dict().items():
            setattr(existing, key, value)
        db.commit()
        logger.info(f"Updated LoaderConfig {data.id}")
    else:
        loader = LoaderConfig(**data.dict())
        db.add(loader)
        db.commit()
        logger.info(f"Created LoaderConfig {data.id}")
    
    return {"status": "success", "action": "updated" if existing else "created"}


@router.post("/transformers")
async def create_transformer(data: TransformerData, db: Session = Depends(get_db)):
    """Create or update transformer configuration.""" 
    from app.database.models import TransformerConfig
    
    existing = db.query(TransformerConfig).filter(TransformerConfig.id == data.id).first()
    
    if existing:
        for key, value in data.dict().items():
            setattr(existing, key, value)
        db.commit()
        logger.info(f"Updated TransformerConfig {data.id}")
    else:
        transformer = TransformerConfig(**data.dict())
        db.add(transformer)
        db.commit()
        logger.info(f"Created TransformerConfig {data.id}")
    
    return {"status": "success", "action": "updated" if existing else "created"}


@router.get("/job-types/count")
async def count_job_types(db: Session = Depends(get_db)):
    """Get count of job types."""
    from app.database.models import JobTypeConfig
    count = db.query(JobTypeConfig).count()
    return {"count": count}


@router.get("/extractors/count")
async def count_extractors(db: Session = Depends(get_db)):
    """Get count of extractors."""
    from app.database.models import ExtractorConfig
    count = db.query(ExtractorConfig).count()
    return {"count": count}


@router.get("/loaders/count")
async def count_loaders(db: Session = Depends(get_db)):
    """Get count of loaders."""
    from app.database.models import LoaderConfig
    count = db.query(LoaderConfig).count()
    return {"count": count}


@router.get("/transformers/count")
async def count_transformers(db: Session = Depends(get_db)):
    """Get count of transformers."""
    from app.database.models import TransformerConfig
    count = db.query(TransformerConfig).count()
    return {"count": count}


# Field Mapping Endpoints
@router.post("/field-mappings")
async def create_field_mapping(mapping: FieldMappingModel, db: Session = Depends(get_db)):
    """Create or update a field mapping."""
    from app.services.field_mapping_service import FieldMappingService
    
    try:
        result = FieldMappingService.create_or_update_field_mapping(mapping.dict(), db)
        return result
    except Exception as e:
        logger.error(f"Error creating field mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating field mapping: {str(e)}"
        )


@router.post("/field-mappings/bulk")
async def bulk_create_field_mappings(mappings: List[FieldMappingModel], db: Session = Depends(get_db)):
    """Create or update multiple field mappings in bulk."""
    from app.services.field_mapping_service import FieldMappingService
    
    try:
        result = FieldMappingService.bulk_create_field_mappings(
            [mapping.dict() for mapping in mappings], db
        )
        return result
    except Exception as e:
        logger.error(f"Error creating field mappings in bulk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating field mappings in bulk: {str(e)}"
        )


@router.get("/field-mappings")
async def get_field_mappings(
    job_type_id: int,
    source_platform: str = "ssot",
    target_entity: str = None,
    db: Session = Depends(get_db)
):
    """Get field mappings for a specific job type and source platform."""
    from app.services.field_mapping_service import FieldMappingService
    
    try:
        if target_entity:
            # Get mappings for specific target entity
            mappings = FieldMappingService.get_field_mappings(
                job_type_id=job_type_id,
                source_platform=source_platform,
                target_entity=target_entity,
                db=db
            )
        else:
            # Get all mappings for the job type and source platform
            query = db.query(SSOTFieldMapping).filter(
                SSOTFieldMapping.job_type_id == job_type_id,
                SSOTFieldMapping.source_platform == source_platform
            )
            mappings = [
                {
                    "id": mapping.id,
                    "job_type_id": mapping.job_type_id,
                    "source_platform": mapping.source_platform,
                    "target_entity": mapping.target_entity,
                    "ssot_field": mapping.ssot_field,
                    "target_field": mapping.target_field,
                    "transformation_rule": mapping.transformation_rule,
                    "is_required": mapping.is_required,
                    "description": mapping.description
                }
                for mapping in query.all()
            ]
            
        return {"mappings": mappings, "count": len(mappings)}
    except Exception as e:
        logger.error(f"Error retrieving field mappings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving field mappings: {str(e)}"
        )


@router.delete("/field-mappings/{mapping_id}")
async def delete_field_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """Delete a field mapping."""
    from app.services.field_mapping_service import FieldMappingService
    
    try:
        result = FieldMappingService.delete_field_mapping(mapping_id, db)
        return result
    except Exception as e:
        logger.error(f"Error deleting field mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting field mapping: {str(e)}"
        )