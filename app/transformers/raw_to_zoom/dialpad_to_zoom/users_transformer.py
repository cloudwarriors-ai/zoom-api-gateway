from typing import Any, Dict, List, Optional
from datetime import datetime

from app.transformers.base_transformer import BaseTransformer


class DialpadUsersToZoomTransformer(BaseTransformer):
    """
    Transformer for converting Dialpad user data to RingCentral-equivalent format.
    
    This transformer takes Dialpad raw user data and converts it to match the exact
    format that RingCentral users produce after transformation, so that the same
    RingCentral→Zoom loader can be reused without modification.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the DialpadUsersToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
        
        self.logger.info("DialpadUsersToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad user data to RingCentral-equivalent format.
        
        This converts Dialpad user structure to match what RingCentral users look like
        after transformation, so the same loader can handle both sources.
        
        Args:
            data: Dialpad user data dictionary
            
        Returns:
            Transformed user record matching RingCentral transformed format
        """
        try:
            # Create the RingCentral-equivalent structure
            transformed_record = {
                # Core fields that match RingCentral structure
                "id": int(data.get('id', '0')) if str(data.get('id', '0')).isdigit() else 0,
                "extensionNumber": data.get('extension', ''),
                "name": data.get('display_name', ''),
                "type": "User",  # Default type for all users
                "status": self._map_dialpad_status_to_rc(data.get('state', 'active')),
                
                # Create URI structure like RingCentral
                "uri": f"https://dialpad-api/users/{data.get('id', '')}",
                
                # Map permissions structure
                "permissions": self._create_permissions_structure(data),
                
                # Profile image (if available)
                "profileImage": self._create_profile_image_structure(data),
                
                # Site information
                "site": self._create_site_structure(data),
                
                # User visibility
                "hidden": data.get('do_not_disturb', False),
                
                # Country assignment
                "assignedCountry": self._create_country_structure(data),
                
                # Creation time
                "creationTime": self._convert_dialpad_date(data.get('date_added')),
                
                # Preserve the original record_id
                "record_id": data.get('record_id', ''),
                
                # Create user_info structure (key transformation!)
                "user_info": self._create_user_info_structure(data)
            }
            
            self.logger.info(f"Successfully transformed Dialpad user: {data.get('id')}")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming Dialpad user data: {str(e)}")
            raise ValueError("Invalid input data for Dialpad user transformation")
    
    def _map_dialpad_status_to_rc(self, dialpad_status: str) -> str:
        """Map Dialpad user status to RingCentral equivalent."""
        status_mapping = {
            'active': 'Enabled',
            'inactive': 'Disabled',
            'pending': 'NotActivated',
            'suspended': 'Disabled'
        }
        return status_mapping.get(dialpad_status, 'Enabled')
    
    def _create_permissions_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create RingCentral-style permissions from Dialpad data.
        
        Args:
            dialpad_data: Original Dialpad user data
            
        Returns:
            RingCentral-style permissions object
        """
        return {
            "admin": {
                "enabled": dialpad_data.get('is_admin', False) or dialpad_data.get('is_super_admin', False)
            },
            "internationalCalling": {
                "enabled": dialpad_data.get('international_dialing_enabled', False)
            }
        }
    
    def _create_profile_image_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create RingCentral-style profile image structure."""
        image_url = dialpad_data.get('image_url')
        if image_url:
            return {
                "uri": image_url
            }
        return {
            "uri": f"https://dialpad-mock/users/{dialpad_data.get('id', '')}/profile-image"
        }
    
    def _create_site_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create RingCentral-style site structure from Dialpad office data.
        
        Args:
            dialpad_data: Original Dialpad user data
            
        Returns:
            RingCentral-style site object
        """
        # Try to get office/site name from group_details or use default
        site_name = "Main Site"  # Default
        
        group_details = dialpad_data.get('group_details', [])
        if group_details and len(group_details) > 0:
            # Use the first office group name if available
            office_group = next((g for g in group_details if g.get('group_type') == 'office'), None)
            if office_group:
                # For now use office ID, could be enhanced to lookup actual office name
                office_id = office_group.get('group_id', '')
                site_name = f"Office {office_id}"
        
        return {
            "name": site_name
        }
    
    def _create_country_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create RingCentral-style country assignment structure."""
        country_code = dialpad_data.get('country', 'us').upper()
        
        country_mapping = {
            'US': {'id': '1', 'name': 'United States', 'isoCode': 'US'},
            'CA': {'id': '2', 'name': 'Canada', 'isoCode': 'CA'},
            'UK': {'id': '3', 'name': 'United Kingdom', 'isoCode': 'GB'},
            'GB': {'id': '3', 'name': 'United Kingdom', 'isoCode': 'GB'},
        }
        
        country_info = country_mapping.get(country_code, country_mapping['US'])
        
        return {
            "uri": f"https://dialpad-mock/countries/{country_info['id']}",
            "id": country_info['id'],
            "name": country_info['name'],
            "isoCode": country_info['isoCode']
        }
    
    def _convert_dialpad_date(self, dialpad_date: Optional[str]) -> Optional[str]:
        """
        Convert Dialpad date format to RingCentral ISO format.
        
        Args:
            dialpad_date: Dialpad date string (e.g., "2021-06-20T19:18:00")
            
        Returns:
            RingCentral-style ISO date string (e.g., "2021-06-20T19:18:00Z")
        """
        if not dialpad_date:
            return None
            
        try:
            # If already has Z, return as-is
            if dialpad_date.endswith('Z'):
                return dialpad_date
                
            # Add Z for UTC timezone
            if 'T' in dialpad_date and not dialpad_date.endswith('Z'):
                return f"{dialpad_date}Z"
                
            return dialpad_date
            
        except Exception as e:
            self.logger.error(f"Error converting date {dialpad_date}: {str(e)}")
            return None
    
    def _create_user_info_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad user fields to RingCentral user_info structure.
        
        This is the KEY transformation that matches the RingCentral format!
        
        Args:
            dialpad_data: Dialpad user data
            
        Returns:
            RingCentral-style user_info object
        """
        try:
            # Extract email (first one from emails array)
            emails = dialpad_data.get('emails', [])
            primary_email = emails[0] if emails else ""
            
            # Extract phone number (first one from phone_numbers array)
            phone_numbers = dialpad_data.get('phone_numbers', [])
            primary_phone = phone_numbers[0] if phone_numbers else ""
            
            user_info = {
                'first_name': dialpad_data.get('first_name', ''),
                'last_name': dialpad_data.get('last_name', ''),
                'email': primary_email,
                'phone_number': primary_phone,
                'timezone': self._convert_dialpad_timezone(dialpad_data.get('timezone')),
                'type': 'User'  # Always User for regular users
            }
            
            self.logger.debug(f"Created user_info: {user_info}")
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error creating user_info structure: {str(e)}")
            return {}
    
    def _convert_dialpad_timezone(self, dialpad_timezone: Optional[str]) -> Optional[str]:
        """
        Convert Dialpad timezone to a standard format.
        
        Args:
            dialpad_timezone: Dialpad timezone string
            
        Returns:
            Standard timezone string or None
        """
        if not dialpad_timezone:
            return None
            
        # Simple timezone mapping - could be expanded
        timezone_mapping = {
            'US/Pacific': 'America/Los_Angeles',
            'US/Mountain': 'America/Denver',
            'US/Central': 'America/Chicago',
            'US/Eastern': 'America/New_York'
        }
        
        return timezone_mapping.get(dialpad_timezone, dialpad_timezone)