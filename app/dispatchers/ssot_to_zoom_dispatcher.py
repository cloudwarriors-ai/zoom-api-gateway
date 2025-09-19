"""
SSOT to Zoom Dispatcher

This dispatcher handles transformations from SSOT format to Zoom format.
It routes requests to the appropriate transformer based on the job type.
"""
import logging
from typing import Dict, Any, List, Optional

from app.transformers.ssot_to_zoom.users_transformer import SSOTToZoomUsersTransformer
from app.transformers.ssot_to_zoom.sites_transformer import SitesToZoomTransformer
from app.transformers.ssot_to_zoom.call_queues_transformer import SSOTToZoomCallQueuesTransformer
from app.transformers.base_transformer import BaseTransformer
from app.core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class SSOTToZoomDispatcher:
    """
    Dispatcher for transforming data from SSOT format to Zoom format.
    
    This dispatcher routes transformation requests to the appropriate transformer
    based on the job type code. It implements the necessary interface expected
    by the PlatformDispatcherFactory.
    """
    
    def __init__(self):
        """Initialize the SSOT to Zoom dispatcher."""
        self.transformers = {}
        self.job_type_mapping = {
            # Map job type codes to transformer classes
            "ssot_to_zoom_users": SSOTToZoomUsersTransformer,
            "ssot_to_zoom_sites": SitesToZoomTransformer,
            "ssot_to_zoom_call_queues": SSOTToZoomCallQueuesTransformer,
            # Add the other job types as they're implemented
            # "ssot_to_zoom_auto_receptionists": SSOTToZoomAutoReceptionistsTransformer,
            # "ssot_to_zoom_ivr": SSOTToZoomIVRTransformer,
        }
        
        # Map job type IDs to their respective job type codes
        self.job_type_id_mapping = {
            39: "ssot_to_zoom_users",         # SSOT Person → Zoom Users
            33: "ssot_to_zoom_sites",         # SSOT Location → Zoom Sites
            45: "ssot_to_zoom_call_queues",   # SSOT CallGroup → Zoom Call Queues
            77: "ssot_to_zoom_auto_receptionists", # SSOT AutoAttendant → Zoom Auto Receptionists
            78: "ssot_to_zoom_ivr",           # SSOT IVR → Zoom IVR
        }
        
        logger.info("SSOTToZoomDispatcher initialized")
    
    def get_transformer(self, job_type_code: str) -> BaseTransformer:
        """
        Get a transformer instance for the given job type code.
        
        Args:
            job_type_code: Job type code (e.g., 'ssot_to_zoom_users')
            
        Returns:
            Transformer instance
            
        Raises:
            TransformationError: If no transformer is available for the job type
        """
        # Check if we have a cached transformer
        if job_type_code in self.transformers:
            return self.transformers[job_type_code]
        
        # Check if we have a transformer class for this job type
        if job_type_code not in self.job_type_mapping:
            raise TransformationError(f"No transformer available for job type: {job_type_code}")
        
        # Create and cache the transformer
        transformer_class = self.job_type_mapping[job_type_code]
        transformer = transformer_class()
        self.transformers[job_type_code] = transformer
        
        logger.info(f"Created transformer for job type: {job_type_code}")
        return transformer
    
    def transform(self, job_type_code: str, data: Dict[str, Any], job: Optional[Any] = None) -> Dict[str, Any]:
        """
        Transform data from SSOT format to Zoom format.
        
        Args:
            job_type_code: Job type code or job type ID
            data: Source data in SSOT format
            job: Optional job context
            
        Returns:
            Transformed data in Zoom format
            
        Raises:
            TransformationError: If transformation fails
        """
        try:
            # Handle job type ID input
            if isinstance(job_type_code, (int, str)) and str(job_type_code).isdigit():
                job_type_id = int(job_type_code)
                if job_type_id in self.job_type_id_mapping:
                    job_type_code = self.job_type_id_mapping[job_type_id]
                    logger.info(f"Mapped job type ID {job_type_id} to code: {job_type_code}")
                else:
                    raise TransformationError(f"Unknown job type ID: {job_type_id}")
            
            # Get the appropriate transformer
            transformer = self.get_transformer(job_type_code)
            
            # Transform the data
            logger.info(f"Transforming data with job type: {job_type_code}")
            transformed_data = transformer.transform(data)
            
            logger.info(f"Successfully transformed data for job type: {job_type_code}")
            return transformed_data
            
        except TransformationError as e:
            # Re-raise transformation errors
            logger.error(f"Transformation error for job type {job_type_code}: {str(e)}")
            raise
        except Exception as e:
            # Wrap other exceptions
            error_msg = f"Failed to transform data for job type {job_type_code}: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise TransformationError(error_msg)
    
    def get_supported_job_types(self) -> List[str]:
        """
        Get a list of supported job type codes.
        
        Returns:
            List of supported job type codes
        """
        return list(self.job_type_mapping.keys())