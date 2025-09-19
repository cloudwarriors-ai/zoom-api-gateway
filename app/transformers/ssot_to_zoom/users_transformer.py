from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper
from app.services.field_mapping_service import FieldMappingService
from app.database.session import get_db

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
        self.job_type_id = 39  # JobType 39: SSOT Person → Zoom Users
        self.source_format = "ssot"
        self.target_format = "zoom"
        self.target_entity = "user"
        
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
        
        # If we have field mappings, use them
        if self.field_mappings:
            # Apply base field mappings
            transformed = FieldMappingService.apply_field_mappings(data, self.field_mappings)
            
            # Check if we need to create a user_info structure
            if "user_info" not in transformed:
                # Get all mappings for user_info fields
                user_info_mappings = [m for m in self.field_mappings if m["target_field"].startswith("user_info.")]
                
                # Apply nested field mappings to create user_info structure
                if user_info_mappings:
                    user_info_data = FieldMappingService.apply_nested_field_mappings(data, user_info_mappings, "user_info")
                    # Merge with existing transformed data
                    transformed.update(user_info_data)
        else:
            # Fall back to old transformation logic
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
            
            # Add the user_info object to the transformed data
            transformed["user_info"] = user_info
        
        # Handle special fields and complex transformations regardless of mapping approach
        
        # Check if user_info exists, create if not
        if "user_info" not in transformed:
            transformed["user_info"] = {}
            
        # Handle timezone conversion
        timezone_field = next((m["ssot_field"] for m in self.field_mappings 
                              if m["target_field"] == "user_info.timezone"), None)
                              
        if timezone_field and timezone_field in data:
            timezone_data = data.get(timezone_field)
            if timezone_data:
                # Handle both string and object timezone formats
                if isinstance(timezone_data, dict):
                    iana_timezone = self.helper.transform_timezone_to_iana(timezone_data)
                else:
                    iana_timezone = ZoomTransformerHelper.convert_to_iana_timezone(str(timezone_data))
                
                if iana_timezone:
                    transformed["user_info"]["timezone"] = iana_timezone
                    self.logger.info(f"Converted timezone to IANA format: {iana_timezone}")
        
        # Handle user type mapping
        user_type_field = next((m["ssot_field"] for m in self.field_mappings 
                               if m["target_field"] == "user_info.type"), None)
                               
        if user_type_field and user_type_field in data:
            user_type = data.get(user_type_field)
            if user_type:
                zoom_type = ZoomTransformerHelper.map_user_type_to_zoom(user_type)
                transformed["user_info"]["type"] = zoom_type
                self.logger.info(f"Mapped user type {user_type} to Zoom type {zoom_type}")
        
        # Set default user type if not already set
        if "type" not in transformed.get("user_info", {}):
            transformed["user_info"]["type"] = 1  # Default to regular user
            self.logger.info("Set default user_info.type = 1")
        
        # Format phone numbers if available
        phone_numbers_field = next((m["ssot_field"] for m in self.field_mappings 
                                   if m["target_field"] == "phone_numbers"), None)
                                   
        if phone_numbers_field and phone_numbers_field in data:
            phone_numbers = data.get(phone_numbers_field)
            if phone_numbers and isinstance(phone_numbers, list):
                formatted_numbers = ZoomTransformerHelper.format_user_phone_numbers(phone_numbers)
                if formatted_numbers:
                    transformed["phone_numbers"] = formatted_numbers
                    self.logger.info(f"Formatted {len(formatted_numbers)} phone numbers")
        
        # Generate display name from first and last name if not already set
        if "display_name" not in transformed:
            user_info = transformed.get("user_info", {})
            display_name = ZoomTransformerHelper.concat_user_display_name(
                user_info.get("first_name", ""),
                user_info.get("last_name", "")
            )
            if display_name:
                transformed["display_name"] = display_name
                self.logger.info(f"Generated display name '{display_name}'")
        
        # Add additional Zoom-specific fields if not already set
        if "status" not in transformed:
            transformed["status"] = "active"
        
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
        # If we have field mappings, check required fields based on them
        if self.field_mappings:
            required_fields = [m["ssot_field"] for m in self.field_mappings if m.get("is_required", False)]
            
            for field in required_fields:
                if field not in data:
                    self.logger.error(f"Missing required field: {field}")
                    return False
                    
            return True
        else:
            # Fall back to old validation logic
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