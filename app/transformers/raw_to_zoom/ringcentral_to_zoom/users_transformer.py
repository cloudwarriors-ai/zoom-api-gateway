from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer
from app.utils.zoom_transformer_ported import ZoomTransformerHelper

logger = logging.getLogger(__name__)


class RingCentralToZoomUsersTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral user data to Zoom format.
    
    This transformer handles the mapping of user data from RingCentral's
    format to the format required by Zoom's API.
    """
    
    def __init__(self):
        """
        Initialize the RingCentralToZoomUsersTransformer.
        """
        super().__init__()
        self.job_type_code = "ringcentral_zoom_users"
        self.source_format = "ringcentral"
        self.target_format = "zoom"
        
        # Get transformation config
        self.transformation_config = self.get_transformation_config(self.job_type_code)
        
        # Initialize ZoomTransformerHelper for complex transformations
        self.helper = ZoomTransformerHelper()
        
        self.logger.info(f"RingCentralToZoomUsersTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral user data to Zoom user format.
        
        This matches exactly what ZoomTransformerHelper.transform_user_data() does:
        - Copies original data  
        - Maps contact fields to user_info
        - Removes contact field
        - Maps RingCentral type directly (no conversion)
        
        Args:
            data: RingCentral user data dictionary
            
        Returns:
            Transformed user record with original data plus user_info
        """
        try:
            # This matches ZoomTransformerHelper.transform_user_data() exactly  
            transformed = dict(data)  # Copy original
            
            # Transform contact fields to user_info structure
            if 'contact' in data:
                contact = data['contact']
                transformed['user_info'] = {
                    'first_name': contact.get('firstName', ''),
                    'last_name': contact.get('lastName', ''),
                    'email': contact.get('email', ''),
                    'phone_number': contact.get('businessPhone', ''),
                    'timezone': self.helper.transform_timezone_to_iana(data.get('regionalSettings', {}))
                }
                # Remove original field after transformation
                del transformed['contact']
            
            # Map RingCentral type to user_info.type, with fallback to 1
            if 'user_info' not in transformed:
                transformed['user_info'] = {}
            
            # Use RingCentral type if available, otherwise default to 1
            # NOTE: The working system does NOT convert the type - it uses it directly
            if 'type' in data and data['type']:
                transformed['user_info']['type'] = data['type']
                self.logger.info(f"Mapped RingCentral type {data['type']} to user_info.type for user {transformed.get('id', 'unknown')}")
            else:
                transformed['user_info']['type'] = 1  # Default fallback
                self.logger.info(f"Set default user_info.type = 1 for user {transformed.get('id', 'unknown')}")
            
            self.logger.info(f"Successfully transformed user data for user {transformed.get('id', 'unknown')}")
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming user data: {str(e)}")
            raise ValueError("Invalid input data for RingCentral user transformation")
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input RingCentral user data.
        
        Args:
            data: RingCentral user data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required fields are present
        if not data.get("id"):
            self.logger.error("Missing required field: id")
            return False
        
        # Ensure contact object exists
        if "contact" not in data or not isinstance(data["contact"], dict):
            self.logger.error("Missing or invalid contact object")
            return False
        
        # Ensure contact has email
        if not data["contact"].get("email"):
            self.logger.error("Missing required field: contact.email")
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
        
        required_fields = ["first_name", "last_name", "email"]
        for field in required_fields:
            if not data["user_info"].get(field):
                self.logger.error(f"Missing required Zoom field: user_info.{field}")
                return False
        
        return True