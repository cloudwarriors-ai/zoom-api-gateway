from typing import Any, Dict, List, Optional

from app.transformers.base_transformer import BaseTransformer


class SitesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting SSOT (Single Source of Truth) site data to Zoom format.
    
    This transformer handles the mapping of site/location data from the organization's
    central data store to the format required by Zoom's API.
    """
    
    def __init__(self, config_id: Optional[str] = None):
        """
        Initialize the SitesToZoomTransformer.
        
        Args:
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        if config_id:
            self.transformation_config = self.get_transformation_config(config_id)
        else:
            # Use default configuration if none specified
            self.transformation_config = {
                "name_mapping": {"site_name": "name"},
                "address_mapping": {
                    "street_address": "address_line1",
                    "city": "city",
                    "state_province": "state",
                    "postal_code": "zip",
                    "country": "country"
                },
                "defaults": {
                    "country": "US"
                }
            }
        
        self.logger.info("SitesToZoomTransformer initialized")
    
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
        
        zoom_site = {}
        
        # Map site name
        name_mapping = self.transformation_config.get("name_mapping", {})
        zoom_site["name"] = data.get(name_mapping.get("site_name", "name"), "")
        
        # Map address fields
        address_mapping = self.transformation_config.get("address_mapping", {})
        for ssot_field, zoom_field in address_mapping.items():
            zoom_site[zoom_field] = data.get(ssot_field, "")
        
        # Apply defaults for missing fields
        defaults = self.transformation_config.get("defaults", {})
        for field, default_value in defaults.items():
            zoom_field = address_mapping.get(field)
            if zoom_field and not zoom_site.get(zoom_field):
                zoom_site[zoom_field] = default_value
        
        # Add additional Zoom-specific fields
        zoom_site["status"] = "active"
        
        if not self.validate_output(zoom_site):
            self.logger.error(f"Invalid output data: {zoom_site}")
            raise ValueError("Transformation resulted in invalid Zoom site data")
        
        return zoom_site
    
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