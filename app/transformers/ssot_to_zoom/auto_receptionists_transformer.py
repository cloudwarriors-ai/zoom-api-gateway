"""
SSOT to Zoom Auto Receptionists Transformer

This transformer converts SSOT auto attendant data to Zoom auto receptionist format.
"""
from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper
from app.services.field_mapping_service import FieldMappingService
from app.database.session import get_db

logger = logging.getLogger(__name__)


class SSOTToZoomAutoReceptionistsTransformer(BaseTransformer):
    """
    Transformer for converting SSOT auto attendant data to Zoom auto receptionist format.
    
    This transformer handles the mapping of auto attendant data from the organization's
    central data store to the format required by Zoom's API.
    """
    
    def __init__(self):
        """Initialize the SSOTToZoomAutoReceptionistsTransformer."""
        super().__init__()
        self.job_type_code = "ssot_to_zoom_auto_receptionists"
        self.job_type_id = 77  # JobType 77: SSOT AutoAttendant → Zoom Auto Receptionists
        self.source_format = "ssot"
        self.target_format = "zoom"
        self.target_entity = "auto_receptionist"
        
        # Get SSOT schema and transformation config
        self.ssot_schema = self.get_ssot_schema(self.job_type_code)
        self.transformation_config = self.get_transformation_config(self.job_type_code)
        
        # Initialize ZoomTransformerHelper for complex transformations
        self.helper = ZoomTransformerHelper()
        
        # Get database session
        self.db = next(get_db())
        
        # Get field mappings
        self.field_mappings = FieldMappingService.get_field_mappings(
            job_type_id=self.job_type_id,
            source_platform="ssot",
            target_entity=self.target_entity,
            db=self.db
        )
        
        self.logger.info(f"SSOTToZoomAutoReceptionistsTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SSOT auto attendant data to Zoom auto receptionist format.
        
        Args:
            data: SSOT auto attendant data dictionary
            
        Returns:
            Dictionary in Zoom auto receptionist format
        """
        if not self.validate_input(data):
            self.logger.error(f"Invalid input data: {data}")
            raise ValueError("Invalid input data for SSOT auto attendant transformation")
        
        # Apply field mappings to transform data
        transformed = FieldMappingService.apply_field_mappings(data, self.field_mappings)
        
        # Add required base structure if not present
        if "auto_receptionist" not in transformed:
            transformed["auto_receptionist"] = {}
        
        # Map complex fields that require special handling
        
        # Handle site/location mapping
        site_id_field = next((m["ssot_field"] for m in self.field_mappings 
                             if m["target_field"] == "site_id" or m["target_field"] == "auto_receptionist.site_id"), None)
        
        if site_id_field and site_id_field in data:
            site_id = data.get(site_id_field)
            if "auto_receptionist" in transformed:
                transformed["auto_receptionist"]["site_id"] = site_id
            else:
                transformed["site_id"] = site_id
        
        # Handle hours of operation
        hours_field = next((m["ssot_field"] for m in self.field_mappings 
                           if m["target_field"] == "hours_of_operation" or m["target_field"] == "auto_receptionist.hours_of_operation"), None)
        
        if hours_field and hours_field in data:
            hours_data = data.get(hours_field)
            if hours_data:
                transformed_hours = self.helper.transform_hours_of_operation(hours_data)
                if "auto_receptionist" in transformed:
                    transformed["auto_receptionist"]["hours_of_operation"] = transformed_hours
                else:
                    transformed["hours_of_operation"] = transformed_hours
        
        # Handle business hours enabled flag
        business_hours_enabled_field = next((m["ssot_field"] for m in self.field_mappings 
                                           if m["target_field"] == "business_hours_enabled" or m["target_field"] == "auto_receptionist.business_hours_enabled"), None)
        
        if business_hours_enabled_field and business_hours_enabled_field in data:
            enabled = data.get(business_hours_enabled_field, False)
            if "auto_receptionist" in transformed:
                transformed["auto_receptionist"]["business_hours_enabled"] = enabled
            else:
                transformed["business_hours_enabled"] = enabled
        
        # Handle prompt and menu options
        prompt_field = next((m["ssot_field"] for m in self.field_mappings 
                            if m["target_field"] == "prompt" or m["target_field"] == "auto_receptionist.prompt"), None)
        
        if prompt_field and prompt_field in data:
            prompt_data = data.get(prompt_field)
            if prompt_data:
                transformed_prompt = self.helper.transform_auto_receptionist_prompt(prompt_data)
                if "auto_receptionist" in transformed:
                    transformed["auto_receptionist"]["prompt"] = transformed_prompt
                else:
                    transformed["prompt"] = transformed_prompt
        
        # Ensure required fields are present
        if self.validate_output(transformed):
            self.logger.info(f"Successfully transformed SSOT auto attendant data: {transformed.get('name', 'unknown')}")
            return transformed
        else:
            self.logger.error(f"Transformation resulted in invalid Zoom auto receptionist data: {transformed}")
            raise ValueError("Transformation resulted in invalid Zoom auto receptionist data")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input SSOT auto attendant data.
        
        Args:
            data: SSOT auto attendant data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check for required fields based on field mappings
        required_fields = [m["ssot_field"] for m in self.field_mappings if m.get("is_required", False)]
        
        for field in required_fields:
            if field not in data:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate the output Zoom auto receptionist data.
        
        Args:
            data: Zoom auto receptionist data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check for minimum required fields in output
        required_fields = ["name"]
        
        for field in required_fields:
            if field not in data:
                self.logger.error(f"Missing required field in output: {field}")
                return False
        
        return True