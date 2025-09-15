from typing import Any, Dict, List, Optional

from app.transformers.base_transformer import BaseTransformer


class RingCentralSitesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral site data to Zoom location format.
    
    This transformer handles the mapping of site/location data from RingCentral's
    format to the format required by Zoom's API.
    """
    
    def __init__(self, config_id: Optional[str] = None):
        """
        Initialize the RingCentralSitesToZoomTransformer.
        
        Args:
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        if config_id:
            self.transformation_config = self.get_transformation_config(config_id)
        else:
            # Use default configuration if none specified
            self.transformation_config = {
                "field_mapping": {
                    "name": "name",
                    "address.street": "address_line1",
                    "address.city": "city",
                    "address.state": "state",
                    "address.zip": "zip",
                    "address.country": "country",
                    "status": "status"
                },
                "status_mapping": {
                    "Active": "active",
                    "Inactive": "inactive"
                },
                "defaults": {
                    "country": "US"
                }
            }
        
        self.logger.info("RingCentralSitesToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral site data to Zoom location format.
        
        Args:
            data: RingCentral site data dictionary
            
        Returns:
            Dictionary in Zoom location format
        """
        if not self.validate_input(data):
            self.logger.error(f"Invalid input data: {data}")
            raise ValueError("Invalid input data for RingCentral site transformation")
        
        zoom_site = {}
        
        # Map fields using the configured mapping
        field_mapping = self.transformation_config.get("field_mapping", {})
        for rc_field, zoom_field in field_mapping.items():
            # Handle nested fields with dot notation
            if "." in rc_field:
                parts = rc_field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                zoom_site[zoom_field] = value if value is not None else ""
            else:
                zoom_site[zoom_field] = data.get(rc_field, "")
        
        # Map status using status mapping
        status_mapping = self.transformation_config.get("status_mapping", {})
        rc_status = data.get("status", "")
        zoom_site["status"] = status_mapping.get(rc_status, "inactive")
        
        # Apply defaults for missing fields
        defaults = self.transformation_config.get("defaults", {})
        for field, default_value in defaults.items():
            if field in field_mapping.values() and not zoom_site.get(field):
                zoom_site[field] = default_value
        
        # Special handling for address formats
        # RingCentral might have a secondary address line
        if "address" in data and "street2" in data["address"] and data["address"]["street2"]:
            zoom_site["address_line2"] = data["address"]["street2"]
        
        if not self.validate_output(zoom_site):
            self.logger.error(f"Invalid output data: {zoom_site}")
            raise ValueError("Transformation resulted in invalid Zoom site data")
        
        return zoom_site
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input RingCentral site data.
        
        Args:
            data: RingCentral site data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required fields are present
        if not data.get("name"):
            self.logger.error("Missing required field: name")
            return False
        
        # Ensure address object exists
        if "address" not in data or not isinstance(data["address"], dict):
            self.logger.error("Missing or invalid address object")
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