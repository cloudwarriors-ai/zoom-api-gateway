from typing import Any, Dict, List, Optional
from datetime import datetime
import random

from app.transformers.base_transformer import BaseTransformer


class DialpadAutoReceptionistsToZoomTransformer(BaseTransformer):
    """
    Transformer for converting Dialpad auto receptionist (office) data to RingCentral-equivalent format.
    
    This transformer takes Dialpad raw office data and converts it to match the exact
    format that RingCentral auto receptionists produce after transformation, so that the same
    RingCentral→Zoom loader can be reused without modification.
    
    Maps Dialpad office structure to RingCentral auto receptionist format.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the DialpadAutoReceptionistsToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
        
        self.logger.info("DialpadAutoReceptionistsToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad office data to RingCentral auto receptionist format.
        
        This converts Dialpad office structure to match what RingCentral auto receptionists look like
        after transformation, so the same loader can handle both sources.
        
        Args:
            data: Dialpad office data dictionary
            
        Returns:
            Transformed auto receptionist record matching RingCentral transformed format
        """
        try:
            # Create the RingCentral-equivalent structure  
            # Based on RingCentral jobtype 77 transformed format
            transformed_record = {
                # Core fields that match RingCentral structure
                "id": str(data.get('id', data.get('office_id', ''))),
                "name": data.get('name', ''),
                "extensionNumber": self._generate_extension_number(data, "ar"),
                "site.id": self._determine_site_id(data),
                
                # RingCentral includes detailed IVR structure, but for AR creation we focus on basics
                "ivr_details": self._build_ivr_details(data),
                
                # Add record tracking
                "record_id": data.get('record_id', f"dialpad_office_{data.get('id', 'unknown')}"),
                
                # Site mapping fields - use the field name that the loader expects
                "office_id": str(data.get('id', data.get('office_id', ''))),  # For Dialpad loader 42
                "rc_site_id": self._determine_site_id(data)  # For RingCentral loader 56 compatibility
            }
            
            self.logger.info(f"Transformed Dialpad office {data.get('id', 'unknown')} to RingCentral AR format")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming Dialpad office data: {str(e)}")
            self.logger.error(f"Input data: {data}")
            # Return a minimal valid structure to avoid breaking the pipeline
            return {
                "id": str(data.get('id', data.get('office_id', 'unknown'))),
                "name": data.get('name', 'Unknown Office'),
                "extensionNumber": str(data.get('office_id', data.get('id', '0'))),
                "site.id": "main-site",
                "record_id": data.get('record_id', f"dialpad_office_{data.get('id', 'unknown')}")
            }
    
    def _determine_site_id(self, data: Dict[str, Any]) -> str:
        """
        Determine the site ID for the office.
        
        For Dialpad to Zoom, the site ID should match the office ID since each Dialpad office
        corresponds to a Zoom site. This enables proper dependency resolution between
        the site loader and auto receptionist loader.
        
        Args:
            data: Dialpad office data
            
        Returns:
            Site ID string matching the office ID
        """
        # Use the office ID as the site ID for proper dependency mapping
        # This ensures the auto receptionist can find the corresponding site
        return str(data.get('id', data.get('office_id', '')))
    
    def _build_ivr_details(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build IVR details structure that matches RingCentral format.
        
        Args:
            data: Dialpad office data
            
        Returns:
            List of IVR detail objects
        """
        try:
            # Build basic IVR structure - the IVR configuration will be handled by the separate IVR jobtype
            ivr_detail = {
                "uri": f"https://dialpad-api/offices/{data.get('id', '')}/ivr",
                "id": str(data.get('id', data.get('office_id', ''))),
                "name": data.get('name', ''),
                "extensionNumber": str(data.get('office_id', data.get('id', ''))),
                
                # Basic prompt info if available
                "prompt": self._build_prompt_info(data),
                
                # Site information
                "site": {
                    "id": self._determine_site_id(data)
                }
            }
            
            return [ivr_detail]
            
        except Exception as e:
            self.logger.error(f"Error building IVR details: {str(e)}")
            # Return minimal structure
            return [{
                "id": str(data.get('id', data.get('office_id', ''))),
                "name": data.get('name', ''),
                "site": {"id": "main-site"}
            }]
    
    def _build_prompt_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build prompt information from available data.
        
        Args:
            data: Dialpad office data
            
        Returns:
            Prompt information dictionary
        """
        # Default prompt structure
        prompt_info = {
            "mode": "TextToSpeech",
            "text": f"Thank you for calling {data.get('name', 'our office')}.",
            "language": {
                "uri": "https://platform.ringcentral.com/restapi/v1.0/dictionary/language/1033",
                "id": "1033",
                "name": "English (United States)",
                "localeCode": "en_US"
            }
        }
        
        # If Dialpad has specific greeting text, we could use that
        # For now, use a standard greeting
        return prompt_info
    
    def _map_dialpad_status_to_rc(self, dialpad_status: str) -> str:
        """
        Map Dialpad office status to RingCentral equivalent.
        
        Args:
            dialpad_status: Dialpad status string
            
        Returns:
            RingCentral-compatible status string
        """
        status_mapping = {
            'active': 'Enabled',
            'inactive': 'Disabled',
            'suspended': 'Disabled',
            'enabled': 'Enabled',
            'disabled': 'Disabled'
        }
        
        return status_mapping.get(dialpad_status.lower() if dialpad_status else '', 'Enabled')
    
    def _extract_business_hours(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and format business hours from Dialpad office data.
        
        Args:
            data: Dialpad office data
            
        Returns:
            Business hours information
        """
        # Extract hours from various possible fields
        hours = {}
        
        # Map Dialpad day names to standard format
        day_mapping = {
            'monday_hours': 'monday',
            'tuesday_hours': 'tuesday', 
            'wednesday_hours': 'wednesday',
            'thursday_hours': 'thursday',
            'friday_hours': 'friday',
            'saturday_hours': 'saturday',
            'sunday_hours': 'sunday'
        }
        
        for dialpad_field, standard_day in day_mapping.items():
            if dialpad_field in data and data[dialpad_field]:
                day_hours = data[dialpad_field]
                if isinstance(day_hours, list) and len(day_hours) >= 2:
                    hours[standard_day] = {
                        'start': day_hours[0],
                        'end': day_hours[1]
                    }
        
        return hours
    
    def validate_transformation(self, original_data: Dict[str, Any], transformed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the transformation was successful.
        
        Args:
            original_data: Original Dialpad data
            transformed_data: Transformed data
            
        Returns:
            Validation result dictionary
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = ["id", "name", "extensionNumber", "site.id"]
        
        for field in required_fields:
            if not transformed_data.get(field):
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["is_valid"] = False
        
        # Check data consistency
        if str(transformed_data.get("id", "")) != str(original_data.get("id", "")):
            validation_result["warnings"].append("ID field transformation may have changed the value")
        
        return validation_result
    
    def _generate_extension_number(self, data: Dict[str, Any], extension_type: str) -> str:
        """
        Generate a unique 3-digit extension number for the auto receptionist.
        
        Args:
            data: Office data
            extension_type: Type of extension ("ar" for auto receptionist, "cq" for call queue)
            
        Returns:
            3-digit extension number as string
        """
        office_id = str(data.get('id', data.get('office_id', '')))
        
        # Create a deterministic but unique extension based on office ID and type
        # This ensures the same office will always get the same extension for the same type
        seed_value = f"{office_id}_{extension_type}"
        random.seed(hash(seed_value) % 1000000)  # Use hash to create deterministic seed
        
        # Generate 3-digit extension in range 200-999 to avoid conflicts with common ranges
        # 100-199: Often reserved for users
        # 200-299: Call queues  
        # 300-399: Auto receptionists
        if extension_type == "ar":
            extension = random.randint(300, 399)  # Auto receptionist range
        elif extension_type == "cq":
            extension = random.randint(200, 299)  # Call queue range
        else:
            extension = random.randint(400, 999)  # General range
            
        return str(extension)