from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class RingCentralToZoomAutoReceptionistsTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral Auto Receptionist data to Zoom format.
    
    This transformer handles the mapping of Auto Receptionist data from RingCentral's
    format to the format required by Zoom's API.
    """
    
    def __init__(self):
        """
        Initialize the RingCentralToZoomAutoReceptionistsTransformer.
        """
        super().__init__()
        self.job_type_code = "rc_zoom_ars"
        self.source_format = "ringcentral"
        self.target_format = "zoom"
        
        self.logger.info(f"RingCentralToZoomAutoReceptionistsTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral Auto Receptionist data to Zoom format.
        
        This matches exactly what the working system does in dynamic_transformer.py:
        - Copies ALL original data  
        - Maps site.id → rc_site_id for dependency resolution
        
        Args:
            data: RingCentral Auto Receptionist data dictionary
            
        Returns:
            Transformed AR record with original data plus rc_site_id mapping
        """
        try:
            # This matches dynamic_transformer.py line 154 exactly
            transformed = dict(data)  # Copy ALL original data
            
            # Fix dotted field name issue: site.id -> rc_site_id (lines 157-159)
            if 'site.id' in transformed:
                transformed['rc_site_id'] = transformed['site.id']
                self.logger.info(f"AR transformation: mapped 'site.id' -> 'rc_site_id' = '{transformed['rc_site_id']}'")
            
            self.logger.info(f"Successfully transformed ARs item using ZoomTransformerHelper logic")
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming Auto Receptionist data: {str(e)}")
            raise ValueError("Invalid input data for RingCentral Auto Receptionist transformation")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input RingCentral Auto Receptionist data.
        
        Args:
            data: RingCentral Auto Receptionist data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required fields are present
        if not data.get("id"):
            self.logger.error("Missing required field: id")
            return False
        
        if not data.get("name"):
            self.logger.error("Missing required field: name")
            return False
        
        return True
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate the output Zoom Auto Receptionist data.
        
        Args:
            data: Zoom Auto Receptionist data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required Zoom fields are present
        if not data.get("id"):
            self.logger.error("Missing required Zoom field: id")
            return False
        
        if not data.get("name"):
            self.logger.error("Missing required Zoom field: name")
            return False
        
        # If site.id was in input, rc_site_id should be in output
        if "site.id" in data and "rc_site_id" not in data:
            self.logger.warning("site.id present but no rc_site_id generated")
        
        return True