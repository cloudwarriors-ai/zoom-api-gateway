from typing import Any, Dict, List, Optional
import yaml

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper


class SitesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting SSOT (Single Source of Truth) site data to Zoom format.
    
    This transformer handles the mapping of site/location data from the organization's
    central data store to the format required by Zoom's API.
    """
    
    def __init__(self, job_type_code: str = "rc_zoom_sites"):
        """
        Initialize the SitesToZoomTransformer.
        
        Args:
            job_type_code: Job type code for the transformation
        """
        super().__init__()
        self.job_type_code = job_type_code
        self.source_format = "ssot"
        self.target_format = "zoom"
        
        # Get SSOT schema and transformation config
        self.ssot_schema = self.get_ssot_schema(job_type_code)
        self.transformation_config = self.get_transformation_config(job_type_code)
        
        # Initialize ZoomTransformerHelper for complex transformations
        self.helper = ZoomTransformerHelper()
        
        self.logger.info(f"SitesToZoomTransformer initialized for job_type_code: {job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SSOT site data to Zoom location format.
        
        Args:
            data: SSOT site data dictionary
            
        Returns:
            Dictionary in Zoom location format
        """
        if not self.validate_input(data):
            self.logger.error(f"Invalid input data: {data}")
            raise ValueError("Invalid input data for site transformation")
        
        # Create a copy of the input data to avoid modifying the original
        transformed = dict(data)
        
        # Use SSOT schema field mappings if available
        field_mappings = self.ssot_schema.get("field_mappings", {})
        
        # Transform business address to emergency address using ZoomTransformerHelper
        if "businessAddress" in data:
            business_address = data["businessAddress"]
            emergency_address = self.helper.transform_emergency_address(business_address)
            transformed["default_emergency_address"] = emergency_address
            # Remove the original businessAddress field to avoid confusion
            if "businessAddress" in transformed:
                del transformed["businessAddress"]
            self.logger.info("Transformed emergency address using ZoomTransformerHelper")
        
        # Generate auto receptionist name with smart processing
        if "name" in data:
            site_name = data["name"]
            ar_name = ZoomTransformerHelper.process_auto_receptionist_name(site_name)
            transformed["auto_receptionist_name"] = ar_name
            self.logger.info(f"Generated AR name '{ar_name}' for site '{site_name}'")
        
        # Transform regional settings timezone
        if "regionalSettings" in data and isinstance(data["regionalSettings"], dict):
            regional_settings = data["regionalSettings"].copy()
            if "timezone" in regional_settings:
                timezone_data = regional_settings["timezone"]
                # Handle both string and object timezone formats
                if isinstance(timezone_data, dict):
                    iana_timezone = self.helper.transform_timezone_to_iana(timezone_data)
                else:
                    iana_timezone = ZoomTransformerHelper.convert_to_iana_timezone(str(timezone_data))
                
                if iana_timezone:
                    regional_settings["timezone"] = iana_timezone
                    transformed["regionalSettings"] = regional_settings
                    self.logger.info(f"Converted timezone to IANA format: {iana_timezone}")
        
        # Add additional Zoom-specific fields
        transformed["status"] = "active"
        
        if not self.validate_output(transformed):
            self.logger.error(f"Invalid output data: {transformed}")
            raise ValueError("Transformation resulted in invalid Zoom site data")
        
        return transformed
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input SSOT site data.
        
        Args:
            data: SSOT site data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required fields are present
        name_mapping = self.transformation_config.get("name_mapping", {})
        site_name_field = name_mapping.get("site_name", "name")
        
        if not data.get(site_name_field):
            self.logger.error(f"Missing required field: {site_name_field}")
            return False
        
        return True
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate the output Zoom location data.
        
        Args:
            data: Zoom location data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required Zoom fields are present
        required_fields = ["name", "address_line1", "city", "state", "country"]
        
        for field in required_fields:
            if not data.get(field):
                self.logger.error(f"Missing required Zoom field: {field}")
                return False
        
        return True