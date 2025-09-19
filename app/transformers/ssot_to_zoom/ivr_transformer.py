"""
SSOT to Zoom IVR Transformer

This transformer converts SSOT IVR data to Zoom IVR format.
"""
from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper
from app.services.field_mapping_service import FieldMappingService
from app.database.session import get_db

logger = logging.getLogger(__name__)


class SSOTToZoomIVRTransformer(BaseTransformer):
    """
    Transformer for converting SSOT IVR data to Zoom IVR format.
    
    This transformer handles the mapping of IVR data from the organization's
    central data store to the format required by Zoom's API.
    """
    
    def __init__(self):
        """Initialize the SSOTToZoomIVRTransformer."""
        super().__init__()
        self.job_type_code = "ssot_to_zoom_ivr"
        self.job_type_id = 78  # JobType 78: SSOT IVR → Zoom IVR
        self.source_format = "ssot"
        self.target_format = "zoom"
        self.target_entity = "ivr"
        
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
        
        self.logger.info(f"SSOTToZoomIVRTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SSOT IVR data to Zoom IVR format.
        
        Args:
            data: SSOT IVR data dictionary
            
        Returns:
            Dictionary in Zoom IVR format
        """
        if not self.validate_input(data):
            self.logger.error(f"Invalid input data: {data}")
            raise ValueError("Invalid input data for SSOT IVR transformation")
        
        # Apply field mappings to transform data
        transformed = FieldMappingService.apply_field_mappings(data, self.field_mappings)
        
        # Add required base structure if not present
        if "ivr_setting" not in transformed:
            transformed["ivr_setting"] = {}
        
        # Map complex fields that require special handling
        
        # Handle site/location mapping
        site_id_field = next((m["ssot_field"] for m in self.field_mappings 
                             if m["target_field"] == "site_id" or m["target_field"] == "ivr_setting.site_id"), None)
        
        if site_id_field and site_id_field in data:
            site_id = data.get(site_id_field)
            if "ivr_setting" in transformed:
                transformed["ivr_setting"]["site_id"] = site_id
            else:
                transformed["site_id"] = site_id
        
        # Handle audio prompt
        audio_prompt_field = next((m["ssot_field"] for m in self.field_mappings 
                                  if m["target_field"] == "audio_prompt" or m["target_field"] == "ivr_setting.audio_prompt"), None)
        
        if audio_prompt_field and audio_prompt_field in data:
            audio_prompt_data = data.get(audio_prompt_field)
            if audio_prompt_data:
                transformed_prompt = self.helper.transform_ivr_audio_prompt(audio_prompt_data)
                if "ivr_setting" in transformed:
                    transformed["ivr_setting"]["audio_prompt"] = transformed_prompt
                else:
                    transformed["audio_prompt"] = transformed_prompt
        
        # Handle menu options
        menu_options_field = next((m["ssot_field"] for m in self.field_mappings 
                                  if m["target_field"] == "menu_options" or m["target_field"] == "ivr_setting.menu_options"), None)
        
        if menu_options_field and menu_options_field in data:
            menu_options_data = data.get(menu_options_field)
            if menu_options_data:
                transformed_options = self.helper.transform_ivr_menu_options(menu_options_data)
                if "ivr_setting" in transformed:
                    transformed["ivr_setting"]["menu_options"] = transformed_options
                else:
                    transformed["menu_options"] = transformed_options
        
        # Handle hours of operation
        hours_field = next((m["ssot_field"] for m in self.field_mappings 
                           if m["target_field"] == "hours_of_operation" or m["target_field"] == "ivr_setting.hours_of_operation"), None)
        
        if hours_field and hours_field in data:
            hours_data = data.get(hours_field)
            if hours_data:
                transformed_hours = self.helper.transform_hours_of_operation(hours_data)
                if "ivr_setting" in transformed:
                    transformed["ivr_setting"]["hours_of_operation"] = transformed_hours
                else:
                    transformed["hours_of_operation"] = transformed_hours
        
        # Ensure required fields are present
        if self.validate_output(transformed):
            self.logger.info(f"Successfully transformed SSOT IVR data: {transformed.get('name', 'unknown')}")
            return transformed
        else:
            self.logger.error(f"Transformation resulted in invalid Zoom IVR data: {transformed}")
            raise ValueError("Transformation resulted in invalid Zoom IVR data")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input SSOT IVR data.
        
        Args:
            data: SSOT IVR data to validate
            
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
        Validate the output Zoom IVR data.
        
        Args:
            data: Zoom IVR data to validate
            
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