from typing import Any, Dict, List, Optional

from app.transformers.base_transformer import BaseTransformer


class RingCentralSitesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral site data to Zoom location format.
    
    This transformer handles the mapping of site/location data from RingCentral's
    format to the format required by Zoom's API.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the RingCentralSitesToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
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
        
        This matches exactly what ZoomTransformerHelper.transform_sites_data() does:
        - Preserves ALL original data
        - Adds default_emergency_address transformation from businessAddress
        
        Args:
            data: RingCentral site data dictionary
            
        Returns:
            Transformed site record with original data plus default_emergency_address
        """
        try:
            # This matches the logic from ZoomTransformerHelper.transform_sites_data() exactly
            transformed_record = data.copy()  # Preserve ALL original data
            
            # Add the emergency address transformation (the main transformation)
            transformed_record['default_emergency_address'] = self.transform_emergency_address(
                data.get('businessAddress', {})
            )
            
            self.logger.info(f"Successfully transformed site: {data.get('id')}")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming site data: {str(e)}")
            raise ValueError("Invalid input data for RingCentral site transformation")
    
    
    def transform_emergency_address(self, business_address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral businessAddress to Zoom default_emergency_address format.
        
        Args:
            business_address: RingCentral businessAddress object
            
        Returns:
            Transformed emergency address for Zoom
        """
        if not business_address:
            return {}
            
        try:
            # Get country and convert to ISO code
            country_name = business_address.get('country', '')
            country_iso = self.convert_country_to_iso(country_name) if country_name else ''
            
            transformed_address = {
                'address_line1': business_address.get('street', ''),
                'city': business_address.get('city', ''),
                'state_code': business_address.get('state', ''),
                'zip': business_address.get('zip', ''),
                'country': country_iso
            }
            
            self.logger.debug(f"Transformed emergency address: {transformed_address}")
            return transformed_address
            
        except Exception as e:
            self.logger.error(f"Error transforming emergency address: {str(e)}")
            return {}
    
    def _transform_regional_settings(self, regional_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform regional settings with timezone conversion.
        
        Args:
            regional_settings: Regional settings object
            
        Returns:
            Transformed regional settings
        """
        if not regional_settings:
            return {}
            
        try:
            # Extract timezone and convert to IANA
            timezone = regional_settings.get('timezone', {})
            iana_timezone = self.transform_timezone_to_iana(timezone)
            
            return {
                'timezone': iana_timezone
            }
            
        except Exception as e:
            self.logger.error(f"Error transforming regional settings: {str(e)}")
            return {}
    
    def transform_timezone_to_iana(self, timezone_data: Dict[str, Any]) -> Optional[str]:
        """
        Transform timezone data to IANA format.
        
        Args:
            timezone_data: Timezone object from source platform
            
        Returns:
            IANA timezone string or None
        """
        if not timezone_data:
            return None
            
        try:
            # Handle RingCentral timezone format to IANA conversion
            if isinstance(timezone_data, dict):
                if 'id' in timezone_data:
                    # Map RingCentral timezone IDs to IANA format
                    rc_to_iana_map = {
                        '58': 'America/New_York',
                        '59': 'America/Chicago', 
                        '60': 'America/Denver',
                        '61': 'America/Los_Angeles',
                        '62': 'America/Phoenix',
                        '63': 'America/Anchorage',
                        '64': 'Pacific/Honolulu'
                    }
                    return rc_to_iana_map.get(str(timezone_data['id']))
                    
                if 'name' in timezone_data:
                    # Handle timezone name to IANA conversion
                    name_to_iana_map = {
                        'Eastern Time': 'America/New_York',
                        'Central Time': 'America/Chicago',
                        'Mountain Time': 'America/Denver', 
                        'Pacific Time': 'America/Los_Angeles',
                        'Alaska Time': 'America/Anchorage',
                        'Hawaii Time': 'Pacific/Honolulu'
                    }
                    return name_to_iana_map.get(timezone_data['name'])
            
            elif isinstance(timezone_data, str):
                # Handle direct string timezone values
                return timezone_data if timezone_data.startswith('America/') or timezone_data.startswith('Pacific/') else None
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error converting timezone to IANA: {str(e)}")
            return None
    
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
            'Canada': 'CA',
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
        
        return country_mapping.get(country_name, country_name)
    
