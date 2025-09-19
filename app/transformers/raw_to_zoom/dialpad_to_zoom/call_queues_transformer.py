from typing import Any, Dict, List, Optional
from datetime import datetime
import random

from app.transformers.base_transformer import BaseTransformer
from app.transformers.raw_to_zoom.dialpad_to_zoom.autoreceptionists_transformer import DialpadAutoReceptionistsToZoomTransformer


class DialpadCallQueuesToZoomTransformer(BaseTransformer):
    """
    Transformer for converting Dialpad call queue data to RingCentral-equivalent format.
    
    This transformer takes Dialpad raw call queue data and converts it to match the exact
    format that RingCentral call queues produce after transformation, so that the same
    RingCentral→Zoom loader can be reused without modification.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the DialpadCallQueuesToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
        
        # Initialize AR transformer instance to reuse extension generation method
        self._ar_transformer = DialpadAutoReceptionistsToZoomTransformer()
        
        self.logger.info("DialpadCallQueuesToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad call queue data to RingCentral-equivalent format.
        
        This converts Dialpad call queue structure to match what RingCentral call queues look like
        after transformation, so the same loader can handle both sources.
        
        Args:
            data: Dialpad call queue data dictionary
            
        Returns:
            Transformed call queue record matching RingCentral transformed format
        """
        try:
            # Create the RingCentral-equivalent structure
            transformed_record = {
                # Core fields that match RingCentral structure
                "uri": f"https://dialpad-api/callqueues/{data.get('id', '')}",
                "id": data.get('id', ''),
                "extensionNumber": self._ar_transformer._generate_extension_number(data, "cq"),
                "name": data.get('name', ''),
                
                # Create site structure like RingCentral
                "site": self._create_site_structure(data),
                
                # Members array (empty for now, could be enhanced to include operators)
                "members": [],
                
                # Create queue_settings structure
                "queue_settings": self._create_queue_settings_structure(data),
                
                # Create business_hours structure from Dialpad hours
                "business_hours": self._create_business_hours_structure(data),
                
                # Empty arrays for greetings and call_handling (could be enhanced)
                "greetings": [],
                "call_handling": [],
                
                # Create basic answering rules
                "answering_rules": self._create_answering_rules_structure(data),
                
                # Preserve the original record_id
                "record_id": data.get('record_id', '')
            }
            
            self.logger.info(f"Successfully transformed Dialpad call queue: {data.get('id')}")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming Dialpad call queue data: {str(e)}")
            raise ValueError("Invalid input data for Dialpad call queue transformation")
    
    def _create_site_structure(self, dialpad_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create RingCentral-style site structure from Dialpad office data.
        
        Args:
            dialpad_data: Original Dialpad call queue data
            
        Returns:
            RingCentral-style site object
        """
        # Use the actual office/site name from the call queue data
        # The site name should match what's in the dependency data for proper lookup mapping
        site_name = dialpad_data.get('name', '')
        
        return {
            "id": dialpad_data.get('office_id', ''),
            "name": site_name
        }
    
    def _create_queue_settings_structure(self, dialpad_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create RingCentral-style queue_settings from Dialpad data.
        
        Args:
            dialpad_data: Original Dialpad call queue data
            
        Returns:
            List with RingCentral-style queue settings object
        """
        # Map Dialpad state to RingCentral status
        status_mapping = {
            'active': 'Enabled',
            'inactive': 'Disabled',
            'suspended': 'NotActivated'
        }
        status = status_mapping.get(dialpad_data.get('state', 'active'), 'Enabled')
        
        return [{
            "id": dialpad_data.get('id', ''),
            "name": dialpad_data.get('name', ''),
            "extensionNumber": self._ar_transformer._generate_extension_number(dialpad_data, "cq"),
            "status": status,
            "editableMemberStatus": False,
            "site": self._create_site_structure(dialpad_data)
        }]
    
    def _create_business_hours_structure(self, dialpad_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create RingCentral-style business_hours from Dialpad hour data.
        
        Args:
            dialpad_data: Original Dialpad call queue data
            
        Returns:
            List with RingCentral-style business hours object
        """
        try:
            # Extract weekly schedule from Dialpad data
            weekly_ranges = {}
            
            # Map Dialpad day fields to RingCentral format
            day_mapping = {
                'monday_hours': 'monday',
                'tuesday_hours': 'tuesday', 
                'wednesday_hours': 'wednesday',
                'thursday_hours': 'thursday',
                'friday_hours': 'friday'
            }
            
            for dialpad_day, rc_day in day_mapping.items():
                day_hours = dialpad_data.get(dialpad_day, [])
                if day_hours and len(day_hours) >= 2:
                    weekly_ranges[rc_day] = [{
                        "from": day_hours[0],  # Start time like "08:00"
                        "to": day_hours[1]     # End time like "18:00"
                    }]
            
            return [{
                "uri": f"https://dialpad-api/callqueues/{dialpad_data.get('id', '')}/business-hours",
                "schedule": {
                    "weeklyRanges": weekly_ranges
                } if weekly_ranges else {}
            }]
            
        except Exception as e:
            self.logger.error(f"Error creating business hours: {str(e)}")
            return [{
                "uri": f"https://dialpad-api/callqueues/{dialpad_data.get('id', '')}/business-hours",
                "schedule": {}
            }]
    
    def _create_answering_rules_structure(self, dialpad_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create RingCentral-style answering rules from Dialpad routing options.
        
        Args:
            dialpad_data: Original Dialpad call queue data
            
        Returns:
            List with RingCentral-style answering rules
        """
        try:
            queue_id = dialpad_data.get('id', '')
            
            # Create basic business hours and after hours rules
            rules = [
                {
                    "uri": f"https://dialpad-api/callqueues/{queue_id}/answering-rule/after-hours-rule",
                    "id": "after-hours-rule",
                    "type": "AfterHours", 
                    "enabled": True
                },
                {
                    "uri": f"https://dialpad-api/callqueues/{queue_id}/answering-rule/business-hours-rule",
                    "id": "business-hours-rule",
                    "type": "BusinessHours",
                    "enabled": True
                }
            ]
            
            return rules
            
        except Exception as e:
            self.logger.error(f"Error creating answering rules: {str(e)}")
            return []