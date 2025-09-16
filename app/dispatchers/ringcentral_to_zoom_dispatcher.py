"""
RingCentral to Zoom Transformation Dispatcher

This dispatcher handles all RingCentral to Zoom transformations by routing
job type codes to the appropriate transformer implementations.
"""
import logging
from typing import Dict, Any, Optional
from app.core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class RingCentralToZoomDispatcher:
    """Dispatcher for RingCentral to Zoom transformations."""
    
    def __init__(self):
        """Initialize the dispatcher with transformer mappings."""
        self._transformers = {}
        self._initialize_transformers()
    
    def _initialize_transformers(self):
        """Initialize transformer instances for all supported job types."""
        try:
            # Import transformers
            from app.transformers.raw_to_zoom.ringcentral_to_zoom.sites_transformer import RingCentralSitesToZoomTransformer
            from app.transformers.raw_to_zoom.ringcentral_to_zoom.users_transformer import RingCentralToZoomUsersTransformer
            from app.transformers.raw_to_zoom.ringcentral_to_zoom.call_queues_transformer import RingCentralToZoomCallQueuesTransformer
            from app.transformers.raw_to_zoom.ringcentral_to_zoom.auto_receptionists_transformer import RingCentralToZoomAutoReceptionistsTransformer
            from app.transformers.raw_to_zoom.ringcentral_to_zoom.ivr_transformer import RingCentralToZoomIVRTransformer
            
            # Map job type codes to transformer instances
            self._transformers = {
                "rc_zoom_sites": RingCentralSitesToZoomTransformer(job_type_code="rc_zoom_sites"),
                "rc_zoom_users": RingCentralToZoomUsersTransformer(),
                "rc_zoom_call_queues": RingCentralToZoomCallQueuesTransformer(),
                "rc_zoom_ars": RingCentralToZoomAutoReceptionistsTransformer(),
                "rc_zoom_ivr": RingCentralToZoomIVRTransformer()
            }
            
            logger.info(f"Initialized RingCentral to Zoom dispatcher with {len(self._transformers)} transformers")
            
        except Exception as e:
            logger.error(f"Failed to initialize RingCentral to Zoom transformers: {str(e)}")
            raise TransformationError(f"Dispatcher initialization failed: {str(e)}")
    
    def get_supported_job_types(self) -> list:
        """Get list of supported job type codes."""
        return list(self._transformers.keys())
    
    def supports_job_type(self, job_type_code: str) -> bool:
        """Check if the dispatcher supports a given job type code."""
        return job_type_code in self._transformers
    
    def transform(self, job_type_code: str, raw_data: Dict[str, Any], job: Optional[Any] = None) -> Dict[str, Any]:
        """
        Transform data using the appropriate transformer for the job type.
        
        Args:
            job_type_code: The job type code (e.g., 'rc_zoom_sites')
            raw_data: Raw data to transform
            job: Optional job instance for context
            
        Returns:
            Transformed data
            
        Raises:
            TransformationError: If job type is not supported or transformation fails
        """
        if not self.supports_job_type(job_type_code):
            supported_types = ", ".join(self.get_supported_job_types())
            raise TransformationError(
                f"Unsupported job type '{job_type_code}' for RingCentral to Zoom transformation. "
                f"Supported types: {supported_types}"
            )
        
        try:
            transformer = self._transformers[job_type_code]
            logger.info(f"Transforming data using {transformer.__class__.__name__} for job type: {job_type_code}")
            
            # Call transform method with or without job context
            if job is not None:
                transformed_data = transformer.transform(raw_data, job)
            else:
                transformed_data = transformer.transform(raw_data)
            
            logger.info(f"Successfully transformed data for job type: {job_type_code}")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Transformation failed for job type {job_type_code}: {str(e)}")
            raise TransformationError(f"Transformation failed for {job_type_code}: {str(e)}")
    
    def get_transformer_info(self, job_type_code: str) -> Dict[str, Any]:
        """
        Get information about a specific transformer.
        
        Args:
            job_type_code: The job type code
            
        Returns:
            Dictionary containing transformer information
        """
        if not self.supports_job_type(job_type_code):
            return {"error": f"Job type '{job_type_code}' not supported"}
        
        transformer = self._transformers[job_type_code]
        return {
            "job_type_code": job_type_code,
            "transformer_class": transformer.__class__.__name__,
            "transformer_module": transformer.__class__.__module__,
            "supported": True
        }