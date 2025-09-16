from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class RingCentralToZoomCallQueuesTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral call queue data to Zoom format.
    
    This transformer handles the mapping of call queue data from RingCentral's
    format to the format required by Zoom's API, specifically the business hours
    transformation to custom_hours_settings.
    """
    
    # Weekday name to number mapping (Zoom API format) - from ZoomTransformerHelper
    WEEKDAY_MAPPING = {
        'sunday': 1,
        'monday': 2,
        'tuesday': 3,
        'wednesday': 4,
        'thursday': 5,
        'friday': 6,
        'saturday': 7
    }
    
    def __init__(self):
        """
        Initialize the RingCentralToZoomCallQueuesTransformer.
        """
        super().__init__()
        self.job_type_code = "rc_zoom_call_queues"
        self.source_format = "ringcentral"
        self.target_format = "zoom"
        
        self.logger.info(f"RingCentralToZoomCallQueuesTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral call queue data to Zoom format.
        
        This matches exactly what the working system does in dynamic_transformer.py:
        - Copies ALL original data
        - Extracts business_hours[0] if exists
        - Calls transform_business_hours_data() equivalent
        - Adds custom_hours_settings to the result
        
        Args:
            data: RingCentral call queue data dictionary
            
        Returns:
            Transformed call queue record with original data plus custom_hours_settings
        """
        try:
            # This matches dynamic_transformer.py line 102 exactly
            transformed = dict(data)  # Copy ALL original data
            
            # Check for business_hours data like the working system does (lines 103-106)
            if ('business_hours' in data and 
                len(data['business_hours']) > 0 and 
                'schedule' in data['business_hours'][0]):
                
                # Create the structure that transform_business_hours_data expects
                helper_input = {'business_hours': data['business_hours'][0]}
                self.logger.info(f"Calling transform_business_hours_data with: {helper_input}")
                
                # Transform the business hours data using our implementation
                transformed_result = self.transform_business_hours_data(helper_input)
                
                # Add the transformed custom_hours_settings (lines 112-114)
                if 'custom_hours_settings' in transformed_result:
                    transformed['custom_hours_settings'] = transformed_result['custom_hours_settings']
                    self.logger.info(f"Successfully transformed business hours")
                else:
                    self.logger.warning(f"transform_business_hours_data did not return custom_hours_settings")
            else:
                self.logger.info(f"No business hours data found for call queue transformation")
            
            self.logger.info(f"Successfully transformed call queue data for: {transformed.get('name', 'unknown')}")
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming call queue data: {str(e)}")
            raise ValueError("Invalid input data for RingCentral call queue transformation")
    
    def transform_business_hours_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform business hours data from weeklyRanges format to Zoom's custom_hours_settings array.
        
        This matches exactly what ZoomTransformerHelper.transform_business_hours_data() does.
        
        Args:
            record: The record containing business_hours.schedule.weeklyRanges data
            
        Returns:
            Record with transformed custom_hours_settings array
        """
        if not isinstance(record, dict):
            return record
            
        # Make a copy to avoid modifying the original
        transformed_record = record.copy()
        
        # Check if business hours data exists
        business_hours = record.get('business_hours')
        if not business_hours:
            self.logger.info("No business_hours data found in record")
            return transformed_record
            
        schedule = business_hours.get('schedule', {})
        weekly_ranges = schedule.get('weeklyRanges', {})
        
        if not weekly_ranges:
            self.logger.info("No weeklyRanges data found in business_hours")
            return transformed_record
            
        self.logger.info(f"Transforming weeklyRanges with {len(weekly_ranges)} days: {list(weekly_ranges.keys())}")
        
        # Transform to custom_hours_settings array
        custom_hours_settings = []
        
        for day_name, time_ranges in weekly_ranges.items():
            day_name_lower = day_name.lower()
            
            if day_name_lower not in self.WEEKDAY_MAPPING:
                self.logger.warning(f"Unknown weekday: {day_name}, skipping")
                continue
                
            weekday_number = self.WEEKDAY_MAPPING[day_name_lower]
            
            # Handle multiple time ranges per day (if any)
            if isinstance(time_ranges, list) and time_ranges:
                for time_range in time_ranges:
                    if isinstance(time_range, dict) and 'from' in time_range and 'to' in time_range:
                        custom_hours_settings.append({
                            'weekday': weekday_number,
                            'from': time_range['from'],
                            'to': time_range['to'],
                            'type': 2  # Custom hours
                        })
                        self.logger.info(f"Added custom hours for {day_name}: {time_range['from']}-{time_range['to']}")
        
        if custom_hours_settings:
            # Add the transformed data to the record
            transformed_record['custom_hours_settings'] = custom_hours_settings
            self.logger.info(f"Successfully transformed {len(custom_hours_settings)} time slots to custom_hours_settings")
        else:
            self.logger.warning("No valid time ranges found in weeklyRanges data")
            
        return transformed_record
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input RingCentral call queue data.
        
        Args:
            data: RingCentral call queue data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required fields are present
        if not data.get("id"):
            self.logger.error("Missing required field: id")
            return False
        
        if not data.get("name"):
            self.logger.error("Missing required field: name")
            return False
        
        return True
    
    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate the output Zoom call queue data.
        
        Args:
            data: Zoom call queue data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Ensure required Zoom fields are present
        if not data.get("id"):
            self.logger.error("Missing required Zoom field: id")
            return False
        
        if not data.get("name"):
            self.logger.error("Missing required Zoom field: name")
            return False
        
        # If business_hours existed in input, custom_hours_settings should exist in output
        if "business_hours" in data and "custom_hours_settings" not in data:
            self.logger.warning("business_hours present but no custom_hours_settings generated")
        
        return True