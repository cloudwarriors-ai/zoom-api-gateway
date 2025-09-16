from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper

logger = logging.getLogger(__name__)


class SSOTToZoomUsersTransformer(BaseTransformer):
    """
    Transformer for converting SSOT (Single Source of Truth) user data to Zoom format.
    
    This transformer handles the mapping of user data from the organization's
    central data store to the format required by Zoom's API.
    """
    
    def __init__(self):
        """
        Initialize the SSOTToZoomUsersTransformer.
        """
        super().__init__()
        self.job_type_code = "ssot_to_zoom_users"
        self.source_format = "ssot"
        self.target_format = "zoom"
        
        # Get SSOT schema and transformation config
        self.ssot_schema = self.get_ssot_schema(self.job_type_code)
        self.transformation_config = self.get_transformation_config(self.job_type_code)
        
        # Initialize ZoomTransformerHelper for complex transformations
        self.helper = ZoomTransformerHelper()
        
        self.logger.info(f"SSOTToZoomUsersTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SSOT user data to Zoom user format.
        
        Args:
            data: SSOT user data dictionary
            
        Returns:
            Dictionary in Zoom user format
        """
        if not self.validate_input(data):
            self.logger.error(f"Invalid input data: {data}")
            raise ValueError("Invalid input data for SSOT user transformation")
        
        # Create a copy of the input data to avoid modifying the original
        transformed = dict(data)
        
        # Use SSOT schema field mappings if available
        field_mappings = self.ssot_schema.get("field_mappings", {})
        
        # Build the user_info structure
        user_info = {}
        
        # Map standard fields using schema mappings
        if "first_name" in field_mappings and field_mappings["first_name"] in data:
            user_info["first_name"] = data.get(field_mappings["first_name"], "")
        else:
            user_info["first_name"] = data.get("first_name", data.get("firstName", ""))
        
        if "last_name" in field_mappings and field_mappings["last_name"] in data:
            user_info["last_name"] = data.get(field_mappings["last_name"], "")
        else:
            user_info["last_name"] = data.get("last_name", data.get("lastName", ""))
        
        if "email" in field_mappings and field_mappings["email"] in data:
            user_info["email"] = data.get(field_mappings["email"], "")
        else:
            user_info["email"] = data.get("email", "")
        
        if "phone_number" in field_mappings and field_mappings["phone_number"] in data:
            user_info["phone_number"] = data.get(field_mappings["phone_number"], "")
        else:
            user_info["phone_number"] = data.get("phone_number", data.get("phoneNumber", data.get("business_phone", "")))
        
        # Handle timezone conversion
        timezone_field = field_mappings.get("timezone", "timezone")
        timezone_data = data.get(timezone_field)
        
        if timezone_data:
            # Handle both string and object timezone formats
            if isinstance(timezone_data, dict):
                iana_timezone = self.helper.transform_timezone_to_iana(timezone_data)
            else:
                iana_timezone = ZoomTransformerHelper.convert_to_iana_timezone(str(timezone_data))
            
            if iana_timezone:
                user_info["timezone"] = iana_timezone
                self.logger.info(f"Converted timezone to IANA format: {iana_timezone}")
        
        # Handle user type mapping
        user_type_field = field_mappings.get("user_type", "user_type")
        user_type = data.get(user_type_field)
        
        if user_type:
            zoom_type = ZoomTransformerHelper.map_user_type_to_zoom(user_type)
            user_info["type"] = zoom_type
            self.logger.info(f"Mapped user type {user_type} to Zoom type {zoom_type}")
        else:
            user_info["type"] = 1  # Default to regular user
            self.logger.info(f"Set default user_info.type = 1")
        
        # Add the user_info object to the transformed data
        transformed["user_info"] = user_info
        
        # Format phone numbers if available
        phone_numbers_field = field_mappings.get("phone_numbers", "phone_numbers")
        phone_numbers = data.get(phone_numbers_field)
        
        if phone_numbers and isinstance(phone_numbers, list):
            formatted_numbers = ZoomTransformerHelper.format_user_phone_numbers(phone_numbers)
            if formatted_numbers:
                transformed["phone_numbers"] = formatted_numbers
                self.logger.info(f"Formatted {len(formatted_numbers)} phone numbers")
        
        # Generate display name from first and last name
        display_name = ZoomTransformerHelper.concat_user_display_name(
            user_info.get("first_name", ""),
            user_info.get("last_name", "")
        )
        if display_name:
            transformed["display_name"] = display_name
            self.logger.info(f"Generated display name '{display_name}'")
        
        # Add additional Zoom-specific fields
        transformed["status"] = "active"
        
        # Remove any source fields that aren't needed in the target
        for field in list(transformed.keys()):
            if field not in ["id", "user_info", "phone_numbers", "display_name", "status", "department"]:
                if field in data:  # Only delete if it was in the original data
                    del transformed[field]
        
        if not self.validate_output(transformed):
            self.logger.error(f"Invalid output data: {transformed}")
            raise ValueError("Transformation resulted in invalid Zoom user data")
        
        self.logger.info(f"Successfully transformed SSOT user data for user {transformed.get('id', 'unknown')}")
        return transformed
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input SSOT user data.
        
        Args:
            data: SSOT user data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Use SSOT schema field mappings if available
        field_mappings = self.ssot_schema.get("field_mappings", {})
        
        # Check for required fields using schema mappings
        required_fields = {
            "id": field_mappings.get("id", "id"),
            "email": field_mappings.get("email", "email")
        }
        
        for field, mapped_field in required_fields.items():
            if not data.get(mapped_field):
                self.logger.error(f"Missing required field: {mapped_field}")
                return False
        
        return True
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate the output Zoom user data.
        
        Args:
            data: Zoom user data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required Zoom fields are present
        if "user_info" not in data or not isinstance(data["user_info"], dict):
            self.logger.error("Missing or invalid user_info object")
            return False
        
        required_fields = ["first_name", "last_name", "email", "type"]
        for field in required_fields:
            if not data["user_info"].get(field):
                self.logger.error(f"Missing required Zoom field: user_info.{field}")
                return False
        
        return True