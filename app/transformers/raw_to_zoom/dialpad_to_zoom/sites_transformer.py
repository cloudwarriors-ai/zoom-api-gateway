from typing import Any, Dict, List, Optional

from app.transformers.base_transformer import BaseTransformer


class DialpadSitesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting Dialpad site data to RingCentral-equivalent format.
    
    This transformer takes Dialpad raw site data and converts it to match the exact
    format that RingCentral sites produce after transformation, so that the same
    RingCentral→Zoom loader can be reused without modification.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the DialpadSitesToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
        
        self.logger.info("DialpadSitesToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad site data to RingCentral-equivalent format.
        
        This converts Dialpad site structure to match what RingCentral sites look like
        after transformation, so the same loader can handle both sources.
        
        Args:
            data: Dialpad site data dictionary
            
        Returns:
            Transformed site record matching RingCentral transformed format
        """
        try:
            # Create the RingCentral-equivalent structure
            transformed_record = {
                # Core fields that match RingCentral structure
                "id": data.get('id', ''),
                "name": data.get('name', ''),
                "uri": f"https://dialpad-api/offices/{data.get('id', '')}",
                "extensionNumber": data.get('office_id', data.get('id', '')),
                
                # Create regionalSettings structure like RingCentral
                "regionalSettings": self._create_regional_settings(data),
                
                # Site access (default value)
                "siteAccess": "Unlimited",
                
                # Create callerIdName from site name
                "callerIdName": data.get('name', '').upper(),
                
                # Preserve the original record_id
                "record_id": data.get('record_id', ''),
                
                # Transform e911_address to default_emergency_address (key transformation!)
                "default_emergency_address": self._transform_emergency_address(
                    data.get('e911_address', {})
                )
            }
            
            self.logger.info(f"Successfully transformed Dialpad site: {data.get('id')}")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming Dialpad site data: {str(e)}")
            raise ValueError("Invalid input data for Dialpad site transformation")
    
    def _create_regional_settings(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create RingCentral-style regionalSettings from Dialpad data.
        
        Args:
            dialpad_data: Original Dialpad site data
            
        Returns:
            RingCentral-style regionalSettings object
        """
        try:
            dialpad_timezone = dialpad_data.get('timezone', 'US/Pacific')
            iana_timezone = self._convert_dialpad_timezone_to_iana(dialpad_timezone)
            
            return {
                "timezone": {
                    "uri": f"https://dialpad-mock/timezones/{iana_timezone}",
                    "id": "60",  # Default to Pacific timezone ID
                    "name": iana_timezone,
                    "description": self._get_timezone_description(iana_timezone),
                    "bias": self._get_timezone_bias(iana_timezone)
                },
                "homeCountry": {
                    "uri": "https://dialpad-mock/countries/1",
                    "id": "1",
                    "name": "United States",
                    "isoCode": "US",
                    "callingCode": "1"
                },
                "language": {
                    "id": "1033",
                    "name": "English (United States)",
                    "localeCode": "en-US"
                },
                "greetingLanguage": {
                    "id": "1033", 
                    "name": "English (United States)",
                    "localeCode": "en-US"
                },
                "formattingLocale": {
                    "id": "1033",
                    "name": "English (United States)", 
                    "localeCode": "en-US"
                },
                "timeFormat": "24h"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating regional settings: {str(e)}")
            return {}
    
    def _convert_dialpad_timezone_to_iana(self, dialpad_timezone: str) -> str:
        """
        Convert Dialpad timezone format to IANA format.
        
        Args:
            dialpad_timezone: Dialpad timezone string
            
        Returns:
            IANA timezone string
        """
        timezone_mapping = {
            'US/Pacific': 'Pacific/Honolulu',
            'US/Mountain': 'America/Denver',
            'US/Central': 'America/Chicago',
            'US/Eastern': 'America/New_York',
            'America/Los_Angeles': 'America/Los_Angeles',
            'America/Denver': 'America/Denver',
            'America/Chicago': 'America/Chicago',
            'America/New_York': 'America/New_York',
            'Pacific/Honolulu': 'Pacific/Honolulu'
        }
        
        return timezone_mapping.get(dialpad_timezone, 'Pacific/Honolulu')
    
    def _get_timezone_description(self, iana_timezone: str) -> str:
        """Get timezone description."""
        descriptions = {
            'Pacific/Honolulu': 'Hawaii',
            'America/Los_Angeles': 'Pacific Time (US & Canada)',
            'America/Denver': 'Mountain Time (US & Canada)',
            'America/Chicago': 'Central Time (US & Canada)',
            'America/New_York': 'Eastern Time (US & Canada)'
        }
        return descriptions.get(iana_timezone, 'Hawaii')
    
    def _get_timezone_bias(self, iana_timezone: str) -> str:
        """Get timezone bias (offset from UTC in minutes)."""
        biases = {
            'Pacific/Honolulu': '-600',  # UTC-10
            'America/Los_Angeles': '-480',  # UTC-8
            'America/Denver': '-420',  # UTC-7
            'America/Chicago': '-360',  # UTC-6
            'America/New_York': '-300'  # UTC-5
        }
        return biases.get(iana_timezone, '-600')
    
    def _transform_emergency_address(self, e911_address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad e911_address to RingCentral default_emergency_address format.
        
        This is the KEY transformation that allows reusing the RingCentral loader!
        
        Args:
            e911_address: Dialpad e911_address object
            
        Returns:
            RingCentral-style default_emergency_address for Zoom
        """
        if not e911_address:
            return {}
            
        try:
            # Map Dialpad e911_address fields to RingCentral businessAddress equivalent
            transformed_address = {
                'address_line1': e911_address.get('address', ''),
                'city': e911_address.get('city', ''),
                'state_code': e911_address.get('state', ''),
                'zip': e911_address.get('zip', ''),
                'country': self.convert_country_to_iso(e911_address.get('country', ''))
            }
            
            self.logger.debug(f"Transformed emergency address: {transformed_address}")
            return transformed_address
            
        except Exception as e:
            self.logger.error(f"Error transforming emergency address: {str(e)}")
            return {}
    
    def convert_country_to_iso(self, country_name: str) -> str:
        """
        Convert country name to ISO 3166-1 alpha-2 code.
        
        Args:
            country_name: Country name to convert
            
        Returns:
            ISO country code
        """
        # Country name to ISO code mapping
        country_mapping = {
            'United States': 'US',
            'United States of America': 'US', 
            'USA': 'US',
            'US': 'US',
            'us': 'US',  # Handle lowercase
            'Canada': 'CA',
            'ca': 'CA',  # Handle lowercase
            'United Kingdom': 'GB',
            'Great Britain': 'GB',
            'UK': 'GB',
            'Australia': 'AU',
            'Germany': 'DE',
            'France': 'FR',
            'Japan': 'JP',
            'China': 'CN',
            'India': 'IN',
            'Brazil': 'BR',
            'Mexico': 'MX'
        }
        
        return country_mapping.get(country_name, country_name.upper() if country_name else '')