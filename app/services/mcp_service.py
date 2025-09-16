"""
MCP Service for the Zoom Platform Microservice.

This module provides service classes for handling MCP (Microservice Communication Protocol)
requests and routing them to appropriate services.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import Depends, status

from app.database.session import get_db
from app.database.models import MCPRequest as MCPRequestModel
from app.schemas.mcp import (
    MCPRequest, 
    MCPResponse, 
    ExtractRequest, 
    TransformRequest, 
    LoadRequest,
    StatusResponse,
    TransformResult
)
from app.core.exceptions import (
    CustomException, 
    NotFoundException, 
    ValidationException,
    DatabaseException
)
from app.services.transformer_service import TransformerService


class MCPService:
    """
    Service for handling MCP protocol requests.
    
    This service routes MCP requests to the appropriate services and
    formats responses according to the MCP protocol.
    """
    
    def __init__(self, db: Session = None, transformer_service: TransformerService = None):
        """
        Initialize the MCP service.
        
        Args:
            db: Database session
            transformer_service: Transformer service instance
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = db
        self.transformer_service = transformer_service or TransformerService()
    
    def handle_request(self, request: MCPRequest, db: Session = None) -> MCPResponse:
        """
        Handle an MCP request.
        
        This method routes the request to the appropriate handler based on request_type.
        
        Args:
            request: The MCP request
            db: Database session (optional, overrides the one from constructor)
            
        Returns:
            MCP response
            
        Raises:
            ValidationException: If the request type is invalid
        """
        # Use the provided db or the one from constructor
        db_session = db or self.db
        if db_session is None:
            self.logger.error("No database session available")
            raise DatabaseException(detail="Database session not available")
        
        # Route based on request type
        try:
            if request.request_type == "extract":
                return self._handle_extract_request(request, db_session)
            elif request.request_type == "transform":
                return self._handle_transform_request(request, db_session)
            elif request.request_type == "load":
                return self._handle_load_request(request, db_session)
            else:
                self.logger.error(f"Invalid request type: {request.request_type}")
                raise ValidationException(detail=f"Invalid request type: {request.request_type}")
        except CustomException:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            # Log and convert other exceptions
            self.logger.error(f"Error handling MCP request: {str(e)}")
            raise ValidationException(detail=f"Error handling MCP request: {str(e)}")
    
    def _handle_extract_request(self, request: ExtractRequest, db: Session) -> MCPResponse:
        """
        Handle an extract request.
        
        Args:
            request: The extract request
            db: Database session
            
        Returns:
            MCP response
        """
        self.logger.info(f"Handling extract request for resource: {request.resource_type}")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create a new MCP request record
        try:
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
            
            # In a production implementation, this would trigger an async task
            # to perform the actual data extraction
            
            return MCPResponse(
                request_id=request_id,
                status="accepted",
                message=f"Extraction request accepted for {request.resource_type}",
                details={"resource_type": request.resource_type}
            )
        except Exception as e:
            db.rollback()
            self.logger.error(f"Database error handling extract request: {str(e)}")
            raise DatabaseException(detail=f"Database error: {str(e)}")
    
    def _handle_transform_request(self, request: TransformRequest, db: Session) -> MCPResponse:
        """
        Handle a transform request.
        
        Args:
            request: The transform request
            db: Database session
            
        Returns:
            MCP response
        """
        self.logger.info(f"Handling transform request for job: {request.extract_job_id}")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        try:
            # Create a new MCP request record
            mcp_request = MCPRequestModel(
                request_id=request_id,
                operation="transform",
                parameters=request.dict(),
                status="pending"
            )
            
            # Save to database
            db.add(mcp_request)
            db.commit()
            db.refresh(mcp_request)
            
            # In a production implementation, this would trigger an async task
            # to perform the actual data transformation
            
            return MCPResponse(
                request_id=request_id,
                status="accepted",
                message=f"Transform request accepted for job {request.extract_job_id}",
                details={
                    "extract_job_id": request.extract_job_id,
                    "target_format": request.target_format
                }
            )
        except Exception as e:
            db.rollback()
            self.logger.error(f"Database error handling transform request: {str(e)}")
            raise DatabaseException(detail=f"Database error: {str(e)}")
    
    def _handle_load_request(self, request: LoadRequest, db: Session) -> MCPResponse:
        """
        Handle a load request.
        
        Args:
            request: The load request
            db: Database session
            
        Returns:
            MCP response
        """
        self.logger.info(f"Handling load request for job: {request.transform_job_id}")
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        try:
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
            
            # In a production implementation, this would trigger an async task
            # to perform the actual data loading
            
            return MCPResponse(
                request_id=request_id,
                status="accepted",
                message=f"Load request accepted for job {request.transform_job_id}",
                details={
                    "transform_job_id": request.transform_job_id,
                    "target_platform": request.target_platform,
                    "target_resource": request.target_resource
                }
            )
        except Exception as e:
            db.rollback()
            self.logger.error(f"Database error handling load request: {str(e)}")
            raise DatabaseException(detail=f"Database error: {str(e)}")
    
    def get_request_status(self, request_id: str, db: Session = None) -> StatusResponse:
        """
        Get the status of an MCP request.
        
        Args:
            request_id: The request ID
            db: Database session (optional)
            
        Returns:
            Status response
            
        Raises:
            NotFoundException: If the request is not found
        """
        # Use the provided db or the one from constructor
        db_session = db or self.db
        if db_session is None:
            self.logger.error("No database session available")
            raise DatabaseException(detail="Database session not available")
        
        self.logger.info(f"Getting status for request: {request_id}")
        
        try:
            # Query the database for the request
            mcp_request = db_session.query(MCPRequestModel).filter(
                MCPRequestModel.request_id == request_id
            ).first()
            
            if not mcp_request:
                self.logger.warning(f"Request ID not found: {request_id}")
                raise NotFoundException(detail=f"Request ID {request_id} not found")
            
            # Create and return the status response
            return StatusResponse(
                request_id=mcp_request.request_id,
                operation=mcp_request.operation,
                status=mcp_request.status,
                created_at=mcp_request.created_at,
                updated_at=mcp_request.updated_at,
                error_message=mcp_request.error_message,
                progress=mcp_request.progress,
                results=mcp_request.results
            )
        except NotFoundException:
            # Re-raise NotFoundException
            raise
        except Exception as e:
            self.logger.error(f"Error getting request status: {str(e)}")
            raise DatabaseException(detail=f"Database error: {str(e)}")
    
    def update_request_status(self, 
                            request_id: str, 
                            status: str, 
                            progress: Optional[float] = None,
                            error_message: Optional[str] = None,
                            results: Optional[Dict[str, Any]] = None,
                            db: Session = None) -> StatusResponse:
        """
        Update the status of an MCP request.
        
        Args:
            request_id: The request ID
            status: The new status
            progress: Progress percentage (0-100)
            error_message: Error message (if any)
            results: Operation results (if completed)
            db: Database session (optional)
            
        Returns:
            Updated status response
            
        Raises:
            NotFoundException: If the request is not found
        """
        # Use the provided db or the one from constructor
        db_session = db or self.db
        if db_session is None:
            self.logger.error("No database session available")
            raise DatabaseException(detail="Database session not available")
        
        self.logger.info(f"Updating status for request: {request_id} to {status}")
        
        try:
            # Query the database for the request
            mcp_request = db_session.query(MCPRequestModel).filter(
                MCPRequestModel.request_id == request_id
            ).first()
            
            if not mcp_request:
                self.logger.warning(f"Request ID not found: {request_id}")
                raise NotFoundException(detail=f"Request ID {request_id} not found")
            
            # Update the request
            mcp_request.status = status
            mcp_request.updated_at = datetime.utcnow()
            
            if progress is not None:
                mcp_request.progress = progress
                
            if error_message is not None:
                mcp_request.error_message = error_message
                
            if results is not None:
                mcp_request.results = results
            
            # Commit changes
            db_session.commit()
            db_session.refresh(mcp_request)
            
            # Create and return the updated status response
            return StatusResponse(
                request_id=mcp_request.request_id,
                operation=mcp_request.operation,
                status=mcp_request.status,
                created_at=mcp_request.created_at,
                updated_at=mcp_request.updated_at,
                error_message=mcp_request.error_message,
                progress=mcp_request.progress,
                results=mcp_request.results
            )
        except NotFoundException:
            # Re-raise NotFoundException
            raise
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"Error updating request status: {str(e)}")
            raise DatabaseException(detail=f"Database error: {str(e)}")
    
    def execute_transform(self, 
                        extract_job_id: str,
                        job_type_code: str,
                        source_platform: str,
                        target_platform: str,
                        data: Union[Dict[str, Any], List[Dict[str, Any]]],
                        db: Session = None) -> TransformResult:
        """
        Execute a transformation using the transformer service.
        
        Args:
            extract_job_id: The ID of the extraction job
            job_type_code: The job type code for the transformation
            source_platform: The source platform
            target_platform: The target platform
            data: The data to transform
            db: Database session (optional)
            
        Returns:
            Transform result
            
        Raises:
            ValidationException: If the transformation fails
        """
        self.logger.info(f"Executing transformation for job_type_code={job_type_code} from {source_platform} to {target_platform}")
        
        try:
            # Use the transformer service to transform the data
            source_record_count = len(data) if isinstance(data, list) else 1
            
            transformed_data = self.transformer_service.transform_data(
                job_type_code=job_type_code,
                source_platform=source_platform,
                target_platform=target_platform,
                data=data
            )
            
            transformed_record_count = len(transformed_data) if isinstance(transformed_data, list) else 1
            
            # Create and return the result
            return TransformResult(
                job_id=extract_job_id,
                source_records=source_record_count,
                transformed_records=transformed_record_count,
                target_format=target_platform
            )
        except (NotFoundException, ValidationException):
            # Re-raise these exceptions
            raise
        except Exception as e:
            self.logger.error(f"Error executing transformation: {str(e)}")
            raise ValidationException(detail=f"Transformation error: {str(e)}")