"""
Zoom Transformer Helper - Platform-specific data transformations for Zoom (Ported)

This module is a direct port of the ZoomTransformerHelper class from the monolithic ETL system.
It contains all platform-specific transformation logic for backward compatibility.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ZoomTransformerHelper:
    """
    Base helper class for Zoom platform data transformations.
    
    This class contains all transformation logic that was previously in loader helpers
    but should be executed during the transform phase, not the load phase.
    """
    
    # Weekday name to number mapping (Zoom API format) - from ZoomBusinessHoursHelper
    WEEKDAY_MAPPING = {
        'sunday': 1,
        'monday': 2,
        'tuesday': 3,
        'wednesday': 4,
        'thursday': 5,
        'friday': 6,
        'saturday': 7
    }
    
    # IVR-related constants - from ZoomIVRHelper
    ACTIONS_WITHOUT_TARGET = [-1, 21, 22, 23]  # Disabled, Repeat, Return to root, Return to previous
    
    # Input key mappings from RingCentral to Zoom
    INPUT_KEY_MAPPINGS = {
        'Star': '*',
        'Hash': '#',
        'NoInput': 'timeout',
        # Numbers stay the same: '1' -> '1', '2' -> '2', etc.
    }
    
    # RingCentral to IANA timezone mappings - from TimezoneConverter
    RC_TO_IANA_MAPPING = {
        # US Timezones
        'Pacific Standard Time': 'America/Los_Angeles',
        'Pacific Daylight Time': 'America/Los_Angeles', 
        'Mountain Standard Time': 'America/Denver',
        'Mountain Daylight Time': 'America/Denver',
        'Central Standard Time': 'America/Chicago',
        'Central Daylight Time': 'America/Chicago',
        'Eastern Standard Time': 'America/New_York',
        'Eastern Daylight Time': 'America/New_York',
        'Atlantic Standard Time': 'America/Halifax',
        'Atlantic Daylight Time': 'America/Halifax',
        'Alaska Standard Time': 'America/Anchorage',
        'Alaska Daylight Time': 'America/Anchorage',
        'Hawaii Standard Time': 'Pacific/Honolulu',
        
        # International Timezones
        'Greenwich Mean Time': 'Europe/London',
        'British Summer Time': 'Europe/London',
        'Central European Time': 'Europe/Paris',
        'Central European Summer Time': 'Europe/Paris',
        'Eastern European Time': 'Europe/Bucharest',
        'Eastern European Summer Time': 'Europe/Bucharest',
        'Japan Standard Time': 'Asia/Tokyo',
        'China Standard Time': 'Asia/Shanghai',
        'Australian Eastern Standard Time': 'Australia/Sydney',
        'Australian Eastern Daylight Time': 'Australia/Sydney',
        
        # Additional common mappings
        'UTC': 'UTC',
        'GMT': 'UTC',
        'PST': 'America/Los_Angeles',
        'PDT': 'America/Los_Angeles',
        'MST': 'America/Denver', 
        'MDT': 'America/Denver',
        'CST': 'America/Chicago',
        'CDT': 'America/Chicago',
        'EST': 'America/New_York',
        'EDT': 'America/New_York',
    }
    
    def __init__(self):
        """Initialize the Zoom transformer helper."""
        self.logger = logger.getChild(self.__class__.__name__)
    
    def transform_emergency_address(self, business_address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral businessAddress to Zoom default_emergency_address format.
        
        This transformation was previously done in JobType 33 loader config as:
        'default_emergency_address': {
            'type': 'copy_from', 
            'source': 'businessAddress', 
            'mapping': {
                'address_line1': 'street', 
                'city': 'city', 
                'state_code': 'state', 
                'zip': 'zip', 
                'country': 'country'
            }
        }
        
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
            country_iso = ZoomTransformerHelper.convert_country_to_iso(country_name) if country_name else ''
            
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
    
    def transform_timezone_to_iana(self, timezone_data: Dict[str, Any]) -> Optional[str]:
        """
        Transform timezone data to IANA format.
        
        This handles the 'convert_to_iana' transformation that was in loader config.
        
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
    
    def transform_user_data(self, user_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform user data for JobType 39 (RingCentral to Zoom - Users).
        
        This applies all the transformations for user records:
        - Contact field mapping: contact.* → user_info.*  
        - Timezone conversion
        - Default user type fallback
        
        Args:
            user_record: Raw user record from RingCentral
            
        Returns:
            Transformed user record ready for loading
        """
        transformed = dict(user_record)  # Copy original
        
        # Transform contact fields to user_info structure
        if 'contact' in user_record:
            contact = user_record['contact']
            transformed['user_info'] = {
                'first_name': contact.get('firstName', ''),
                'last_name': contact.get('lastName', ''),
                'email': contact.get('email', ''),
                'phone_number': contact.get('businessPhone', ''),
                'timezone': self.transform_timezone_to_iana(user_record.get('regionalSettings', {}))
            }
            # Remove original field after transformation
            del transformed['contact']
        
        # Map RingCentral type to user_info.type, with fallback to 1
        if 'user_info' not in transformed:
            transformed['user_info'] = {}
        
        # Use RingCentral type if available, otherwise default to 1
        if 'type' in user_record and user_record['type']:
            transformed['user_info']['type'] = user_record['type']
            logger.info(f"Mapped RingCentral type {user_record['type']} to user_info.type for user {transformed.get('id', 'unknown')}")
        else:
            transformed['user_info']['type'] = 1  # Default fallback
            logger.info(f"Set default user_info.type = 1 for user {transformed.get('id', 'unknown')}")
        
        logger.info(f"Successfully transformed user data for user {transformed.get('id', 'unknown')}")
        return transformed
    
    @staticmethod
    def transform_business_hours_data(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform business hours data from weeklyRanges format to Zoom's custom_hours_settings array.
        
        Migrated from ZoomBusinessHoursHelper.transform_business_hours_data() for JobType 45.
        
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
            logger.info("No business_hours data found in record")
            return transformed_record
            
        schedule = business_hours.get('schedule', {})
        weekly_ranges = schedule.get('weeklyRanges', {})
        
        if not weekly_ranges:
            logger.info("No weeklyRanges data found in business_hours")
            return transformed_record
            
        logger.info(f"Transforming weeklyRanges with {len(weekly_ranges)} days: {list(weekly_ranges.keys())}")
        
        # Transform to custom_hours_settings array
        custom_hours_settings = []
        
        for day_name, time_ranges in weekly_ranges.items():
            day_name_lower = day_name.lower()
            
            if day_name_lower not in ZoomTransformerHelper.WEEKDAY_MAPPING:
                logger.warning(f"Unknown weekday: {day_name}, skipping")
                continue
                
            weekday_number = ZoomTransformerHelper.WEEKDAY_MAPPING[day_name_lower]
            
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
                        logger.info(f"Added custom hours for {day_name}: {time_range['from']}-{time_range['to']}")
        
        if custom_hours_settings:
            # Add the transformed data to the record
            transformed_record['custom_hours_settings'] = custom_hours_settings
            logger.info(f"Successfully transformed {len(custom_hours_settings)} time slots to custom_hours_settings")
        else:
            logger.warning("No valid time ranges found in weeklyRanges data")
            
        return transformed_record
    
    @staticmethod
    def map_input_key(rc_input: str) -> str:
        """
        Map RingCentral input key to Zoom format.
        
        Migrated from ZoomIVRHelper.map_input_key() for IVR transformation.
        
        Args:
            rc_input: RingCentral input key ('Star', 'Hash', '1', '2', etc.)
            
        Returns:
            Zoom-compatible input key ('*', '#', '1', '2', etc.)
        """
        mapped_key = ZoomTransformerHelper.INPUT_KEY_MAPPINGS.get(rc_input, rc_input)
        if mapped_key != rc_input:
            logger.info(f"INPUT_MAPPING: Mapped '{rc_input}' → '{mapped_key}'")
        return mapped_key
    
    @staticmethod
    def get_extension_type_from_job_group(job_group_id: int, extension_id: str) -> Optional[str]:
        """
        Determine the extension type (user, call_queue, auto_receptionist) by examining
        DataRecord entries in the current job group.
        
        Migrated from ZoomIVRHelper.get_extension_type_from_job_group() for IVR transformation.
        
        Args:
            job_group_id: The job group ID to search within
            extension_id: The RingCentral extension ID to classify
            
        Returns:
            'user', 'call_queue', 'auto_receptionist', or None if not found
        """
        try:
            # In the microservice, we'll need to implement this differently
            # as we don't have direct access to the Django ORM
            # This is just a stub for compatibility
            logger.warning("get_extension_type_from_job_group not fully implemented in microservice")
            return None
            
        except Exception as e:
            logger.error(f"IVR_MAPPING: Error determining extension type for {extension_id}: {str(e)}")
            return None
    
    @staticmethod
    def resolve_rc_extension_to_zoom_id(job_group_id: int, rc_extension_id: str, extension_type: str) -> Optional[str]:
        """
        Resolve RingCentral extension ID to corresponding Zoom user/queue/AR ID.
        
        Args:
            job_group_id: The job group ID to search within
            rc_extension_id: The RingCentral extension ID to resolve
            extension_type: Type of extension ('user', 'call_queue', 'auto_receptionist')
            
        Returns:
            Zoom ID (user_id, queue_id, or AR ID) or None if not found
        """
        logger.info(f"IVR_RESOLVE: CALLED with job_group_id={job_group_id}, rc_extension_id={rc_extension_id}, extension_type={extension_type}")
        try:
            # In the microservice, we'll need to implement this differently
            # as we don't have direct access to the Django ORM
            # This is just a stub for compatibility
            logger.warning("resolve_rc_extension_to_zoom_id not fully implemented in microservice")
            return None
            
        except Exception as e:
            logger.error(f"IVR_RESOLVE: Error resolving RC extension {rc_extension_id} to Zoom ID: {str(e)}")
            return None
    
    @staticmethod
    def map_rc_action_to_zoom(rc_action: str, target_type: str) -> int:
        """
        Map RingCentral action string to appropriate Zoom action integer based on target type.
        
        Migrated from ZoomIVRHelper.map_rc_action_to_zoom() for IVR transformation.
        
        Args:
            rc_action: RingCentral action string (Connect, Voicemail, etc.)
            target_type: Target extension type ('user', 'call_queue', 'auto_receptionist')
            
        Returns:
            Zoom action integer code
        """
        # Target-specific action mappings
        type_specific_mappings = {
            'user': {
                'Connect': 2,           # Forward to user
                'Voicemail': 200,       # Leave voicemail to user
                'Transfer': 10,         # Forward to phone number
                'ConnectToOperator': 2, # Forward to user (operator)
                'DialByName': 4,        # Forward to common area (closest match)
            },
            'call_queue': {
                'Connect': 7,           # Forward to call queue
                'Voicemail': 400,       # Leave voicemail to call queue
                'Transfer': 10,         # Forward to phone number
                'ConnectToOperator': 7, # Forward to call queue (operator queue)
                'DialByName': 4,        # Forward to common area
            },
            'auto_receptionist': {
                'Connect': 6,           # Forward to auto receptionist
                'Voicemail': 300,       # Leave voicemail to auto receptionist
                'Transfer': 10,         # Forward to phone number
                'ConnectToOperator': 6, # Forward to auto receptionist
                'DialByName': 4,        # Forward to common area
            }
        }
        
        # Universal actions (same for all target types)
        universal_mappings = {
            'Repeat': 21,                    # Repeat menu greeting
            'ReturnToRoot': 22,              # Return to root menu
            'ReturnToPrevious': 23,          # Return to previous menu
            'Disconnect': -1,                # Disabled
            'ReturnToTopLevelMenu': 22,      # Return to root menu
            'DoNothing': -1,                 # Disabled
        }
        
        # Check universal actions first
        if rc_action in universal_mappings:
            action_code = universal_mappings[rc_action]
            logger.info(f"ACTION_MAPPING: Universal action '{rc_action}' → {action_code}")
            return action_code
        
        # Check target-specific mappings
        if target_type in type_specific_mappings:
            target_mappings = type_specific_mappings[target_type]
            if rc_action in target_mappings:
                action_code = target_mappings[rc_action]
                logger.info(f"ACTION_MAPPING: '{rc_action}' for {target_type} → {action_code}")
                return action_code
        
        # Fallback for unknown actions
        logger.warning(f"ACTION_MAPPING: Unknown action '{rc_action}' for target_type '{target_type}', using -1 (disabled)")
        return -1
    
    @staticmethod  
    def process_ivr_payload(resolved_item: Dict[str, Any], job_group_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a resolved IVR item to handle Zoom-specific requirements with enhanced action mapping.
        
        Migrated from ZoomIVRHelper.process_ivr_payload() for IVR transformation.
        
        Args:
            resolved_item: The resolved payload item with placeholders replaced
            job_group_id: Optional job group ID for extension type detection
            
        Returns:
            Processed payload item with correct structure for Zoom API
        """
        if not isinstance(resolved_item, dict):
            return resolved_item
            
        # Make a copy to avoid modifying the original
        processed_item = resolved_item.copy()
        
        # Map input key from RingCentral format to Zoom format
        if 'key' in processed_item:
            rc_key = processed_item['key']
            zoom_key = ZoomTransformerHelper.map_input_key(rc_key)
            processed_item['key'] = zoom_key
        
        # Process action mapping with enhanced target type detection
        if 'action' in processed_item:
            rc_action = processed_item.get('action')
            extension_id = None
            target_type = 'user'  # Default fallback
            
            # Extract extension ID from target if available
            if 'target' in processed_item and isinstance(processed_item['target'], dict):
                extension_id = processed_item['target'].get('extension_id')
            
            # Try to determine extension type using job group data
            if job_group_id and extension_id:
                detected_type = ZoomTransformerHelper.get_extension_type_from_job_group(job_group_id, extension_id)
                if detected_type:
                    target_type = detected_type
                    logger.info(f"IVR_PROCESSING: Detected extension {extension_id} as {target_type}")
                else:
                    logger.warning(f"IVR_PROCESSING: Could not detect type for extension {extension_id}, using default 'user'")
            
            # Map RingCentral action to appropriate Zoom action code
            if rc_action:
                zoom_action_code = ZoomTransformerHelper.map_rc_action_to_zoom(rc_action, target_type)
                processed_item['action'] = zoom_action_code
                logger.info(f"IVR_PROCESSING: Mapped RC action '{rc_action}' to Zoom code {zoom_action_code} for {target_type}")
            
            # Handle target field based on action requirements
            numeric_action = processed_item.get('action')
            
            # Remove target field for actions that don't need it
            if numeric_action in ZoomTransformerHelper.ACTIONS_WITHOUT_TARGET:
                if 'target' in processed_item:
                    del processed_item['target']
                    logger.info(f"IVR_PROCESSING: Removed target field for action {numeric_action} (doesn't need target)")
            
            # For actions that need target but have empty/invalid extension_id, remove target
            elif 'target' in processed_item:
                target = processed_item['target']
                if isinstance(target, dict):
                    target_extension_id = target.get('extension_id')
                    # If extension_id is empty, None, or still a placeholder, remove target
                    if not target_extension_id or target_extension_id.startswith('{'):
                        del processed_item['target']
                        logger.info(f"IVR_PROCESSING: Removed target field for action {numeric_action} (empty extension_id)")
                    else:
                        # Update target type in the target object for Zoom API
                        zoom_target_type_mapping = {
                            'user': 'user',
                            'call_queue': 'call_queue', 
                            'auto_receptionist': 'auto_receptionist'
                        }
                        processed_item['target']['type'] = zoom_target_type_mapping.get(target_type, 'user')
                        logger.info(f"IVR_PROCESSING: Set target type to {processed_item['target']['type']}")
        
        return processed_item
    
    @staticmethod
    def process_audio_prompt_mapping(prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process audio prompt data for Zoom IVR configuration.
        
        Migrated from ZoomIVRHelper.process_audio_prompt_mapping() for IVR transformation.
        
        Args:
            prompt_data: RingCentral prompt data containing audio information
            
        Returns:
            Processed prompt data formatted for Zoom API
        """
        if not isinstance(prompt_data, dict):
            return prompt_data
            
        processed_prompt = {}
        
        # Map RingCentral prompt fields to Zoom format
        if 'audio' in prompt_data:
            audio_data = prompt_data['audio']
            if isinstance(audio_data, dict):
                # Extract audio URI or ID
                audio_uri = audio_data.get('uri') or audio_data.get('id')
                if audio_uri:
                    processed_prompt['audio_prompt_id'] = audio_uri
                    logger.info(f"PROMPT_MAPPING: Mapped audio URI/ID {audio_uri}")
        
        # Handle text prompts as fallback
        if 'text' in prompt_data:
            processed_prompt['text_prompt'] = prompt_data['text']
            logger.info(f"PROMPT_MAPPING: Added text prompt")
        
        # Default prompt mode
        processed_prompt['mode'] = prompt_data.get('mode', 'Audio')
        
        logger.info(f"PROMPT_MAPPING: Processed prompt with mode {processed_prompt.get('mode')}")
        return processed_prompt
    
    @staticmethod
    def process_hours_type_mapping(hours_data: Dict[str, Any]) -> str:
        """
        Process business hours data to determine Zoom hours_type.
        
        Migrated from ZoomIVRHelper.process_hours_type_mapping() for IVR transformation.
        
        Args:
            hours_data: RingCentral hours/schedule data
            
        Returns:
            Zoom hours_type string ('business_hours', 'custom', etc.)
        """
        if not isinstance(hours_data, dict):
            logger.warning("HOURS_MAPPING: Invalid hours data, using 'business_hours'")
            return 'business_hours'
        
        # Check for custom schedule patterns
        if 'weeklyRanges' in hours_data:
            weekly_ranges = hours_data['weeklyRanges']
            if isinstance(weekly_ranges, dict) and weekly_ranges:
                logger.info("HOURS_MAPPING: Found weeklyRanges, using 'custom'")
                return 'custom'
        
        # Check for holiday schedule
        if 'holidaySchedule' in hours_data:
            logger.info("HOURS_MAPPING: Found holidaySchedule, using 'custom'")
            return 'custom'
        
        # Check for after-hours handling
        if 'afterHours' in hours_data or 'closed_hours' in hours_data:
            logger.info("HOURS_MAPPING: Found after-hours config, using 'custom'")
            return 'custom'
        
        # Default to business hours
        logger.info("HOURS_MAPPING: Using default 'business_hours'")
        return 'business_hours'
    
    @staticmethod
    def transform_ivr_action(action: Dict[str, Any], job_group_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Transform a single IVR action from RingCentral format to Zoom format.
        
        Migrated logic from ZoomIVRHelper for individual action transformation.
        
        Args:
            action: Single IVR action from RingCentral ivr_details[0].actions
            job_group_id: Optional job group ID for extension type detection
            
        Returns:
            Transformed action in Zoom format, or None if transformation fails
        """
        if not isinstance(action, dict):
            logger.warning(f"Invalid action format, expected dict: {action}")
            return None
            
        try:
            logger.info(f"IVR_DEBUG: transform_ivr_action START")
            transformed = {}
            
            # Handle both RingCentral format and already-transformed Zoom format
            
            # 1. Handle key field (input mapping)
            if 'input' in action:
                # RingCentral format - transform input to key
                rc_input = action.get('input', '')
                transformed['key'] = ZoomTransformerHelper.map_input_key(rc_input)
            elif 'key' in action:
                # Already in Zoom format - keep existing key
                transformed['key'] = action.get('key')
            
            # 2. Determine target type from extension information  
            target_type = 'user'  # Default fallback
            extension_id = None
            
            # Handle both RingCentral format (extension.id) and Zoom format (target.extension_id)
            if 'extension' in action and isinstance(action['extension'], dict):
                extension_id = action['extension'].get('id')
            elif 'target' in action and isinstance(action['target'], dict):
                extension_id = action['target'].get('extension_id')
                
            # Try to determine extension type using job group data
            logger.info(f"IVR_DEBUG: job_group_id={job_group_id}, extension_id={extension_id}")
            if job_group_id and extension_id:
                logger.info(f"IVR_DEBUG: Calling get_extension_type_from_job_group({job_group_id}, {extension_id})")
                detected_type = ZoomTransformerHelper.get_extension_type_from_job_group(job_group_id, extension_id)
                logger.info(f"IVR_DEBUG: get_extension_type_from_job_group returned: {detected_type}")
                if detected_type:
                    target_type = detected_type
                    logger.info(f"IVR_PROCESSING: Detected extension {extension_id} as {target_type}")
                else:
                    logger.warning(f"IVR_PROCESSING: Could not detect type for extension {extension_id}, using default 'user'")
            else:
                logger.warning(f"IVR_DEBUG: Skipping extension type detection - job_group_id={job_group_id}, extension_id={extension_id}")
            
            # 3. Handle action field (action mapping)
            if isinstance(action.get('action'), str):
                # RingCentral format - transform string action to integer code
                rc_action = action.get('action', '')
                zoom_action_code = ZoomTransformerHelper.map_rc_action_to_zoom(rc_action, target_type)
            else:
                # Already in Zoom format - keep existing action code
                zoom_action_code = action.get('action')
            transformed['action'] = zoom_action_code
            
            # 4. Handle target field based on action requirements
            # Actions that don't need a target field: [-1, 21, 22, 23] (Disabled, Repeat, Return to root, Return to previous)
            ACTIONS_WITHOUT_TARGET = [-1, 21, 22, 23]
            
            if zoom_action_code not in ACTIONS_WITHOUT_TARGET and extension_id:
                # Keep RingCentral extension ID - let loader handle Zoom ID resolution via dependencies
                zoom_target_type_mapping = {
                    'user': 'user',
                    'call_queue': 'call_queue', 
                    'auto_receptionist': 'auto_receptionist'
                }
                transformed['target'] = {
                    'type': zoom_target_type_mapping.get(target_type, 'user'),
                    'extension_id': extension_id  # Keep RC extension ID for loader to resolve
                }
                logger.info(f"IVR_PROCESSING: Set target type to {target_type} with RC extension_id {extension_id} for loader resolution")
            
            logger.info(f"IVR_MAPPING: Transformed action '{action.get('action')}' input '{action.get('input')}' → code {zoom_action_code} for {target_type}")
            return transformed
            
        except Exception as e:
            logger.error(f"IVR_DEBUG: Error transforming IVR action {action}: {str(e)}")
            import traceback
            logger.error(f"IVR_DEBUG: Full traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def build_enhanced_ivr_payload(record_data: Dict[str, Any], job_group_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build complete IVR payload with support for all Zoom IVR features.
        
        Migrated from ZoomIVRHelper.build_enhanced_ivr_payload() for IVR transformation.
        
        Args:
            record_data: The source record data from RingCentral
            job_group_id: Optional job group ID for extension type detection
            
        Returns:
            Complete Zoom IVR payload with all supported features
        """
        payload = {}
        
        # Process basic IVR actions
        if 'actions' in record_data:
            actions = record_data['actions']
            if isinstance(actions, list):
                processed_actions = []
                for action in actions:
                    processed_action = ZoomTransformerHelper.process_ivr_payload(action, job_group_id)
                    processed_actions.append(processed_action)
                payload['key_actions'] = processed_actions
                logger.info(f"ENHANCED_PAYLOAD: Processed {len(processed_actions)} IVR actions")
        
        # Process audio prompt
        if 'prompt' in record_data:
            prompt_data = ZoomTransformerHelper.process_audio_prompt_mapping(record_data['prompt'])
            payload.update(prompt_data)
            logger.info("ENHANCED_PAYLOAD: Added audio prompt data")
        
        # Process hours type
        if 'schedule' in record_data or 'hours' in record_data:
            hours_data = record_data.get('schedule') or record_data.get('hours')
            hours_type = ZoomTransformerHelper.process_hours_type_mapping(hours_data)
            payload['hours_type'] = hours_type
            logger.info(f"ENHANCED_PAYLOAD: Set hours_type to {hours_type}")
        
        logger.info(f"ENHANCED_PAYLOAD: Built complete payload with {len(payload)} components")
        return payload
    
    # === SITES TRANSFORMATION METHODS ===
    # Migrated from ZoomSitesHelper for sites-specific transformations
    
    @staticmethod
    def process_auto_receptionist_name(site_name: str, max_length: int = 30) -> str:
        """
        Process site name for Auto Receptionist creation with Zoom's character limit.
        
        Migrated from ZoomSitesHelper.process_auto_receptionist_name() for sites transformation.
        
        Adds abbreviated suffix while respecting Zoom's AR naming constraints.
        Uses "(NIU)" as an abbreviated form of "(NOT IN USE)" to save space.
        
        Args:
            site_name: The original site name
            max_length: Maximum allowed length (default 30 for Zoom AR)
            
        Returns:
            Processed AR name that fits within the character limit
            
        Examples:
            "Short Site" -> "Short Site (NIU)" (16 chars, truncated to "Short Site (N)")
            "Very Long Site Name" -> "Very Long (NIU)" (15 chars)
            "Site" -> "Site (NIU)" (10 chars)
        """
        if not site_name or not isinstance(site_name, str):
            logger.warning(f"Invalid site_name provided: {site_name}")
            return "Unknown (NIU)"[:max_length]
        
        # Clean and normalize the site name
        clean_name = site_name.strip()
        suffix = " (NIU)"  # Abbreviated form of "(NOT IN USE)"
        
        # If the full name + suffix fits, use it
        full_name = clean_name + suffix
        if len(full_name) <= max_length:
            logger.info(f"AR name fits within limit: '{full_name}' ({len(full_name)} chars)")
            return full_name
        
        # Calculate available space for the base name
        available_for_base = max_length - len(suffix)
        
        if available_for_base > 0:
            # Truncate base name to fit with suffix
            truncated_base = clean_name[:available_for_base].rstrip()
            result = truncated_base + suffix
            logger.info(f"AR name truncated to fit: '{site_name}' -> '{result}' ({len(result)} chars)")
            return result
        else:
            # Suffix itself is too long for the limit (shouldn't happen with 30 char limit)
            result = suffix[:max_length]
            logger.warning(f"Suffix too long for limit, using: '{result}' ({len(result)} chars)")
            return result
    
    @staticmethod
    def apply_sites_transformation(record: Dict[str, Any], transform_config: Dict[str, Any]) -> Any:
        """
        Apply sites-specific transformation to a record field.
        
        Migrated from ZoomSitesHelper.apply_sites_transformation() for sites transformation.
        
        Args:
            record: The record containing source data
            transform_config: Configuration for the transformation
            
        Returns:
            Transformed value
        """
        transform_type = transform_config.get('type')
        
        if transform_type == 'zoom_sites_ar_name' or (transform_type == 'template' and ZoomTransformerHelper.is_sites_transformation(transform_config)):
            # Handle both direct AR name processing and template-based transformations
            max_length = transform_config.get('max_length', 30)
            
            if transform_type == 'zoom_sites_ar_name':
                # Direct AR name processing
                source_field = transform_config.get('source', 'name')
                site_name = record.get(source_field, '')
                return ZoomTransformerHelper.process_auto_receptionist_name(site_name, max_length)
            
            elif transform_type == 'template':
                # Handle template-based transformations that need length limits
                template = transform_config.get('template', '')
                
                # For now, handle the specific case of "{name} (NOT IN USE)"
                if template == "{name} (NOT IN USE)" or template == "{name} (Not in use)":
                    site_name = record.get('name', '')
                    return ZoomTransformerHelper.process_auto_receptionist_name(site_name, max_length)
                
                # For other templates, apply basic length limiting if max_length is specified
                if 'max_length' in transform_config:
                    # This is a simple fallback - replace {name} with actual name and truncate
                    result = template
                    for key, value in record.items():
                        if f"{{{key}}}" in result:
                            result = result.replace(f"{{{key}}}", str(value))
                    
                    if len(result) > max_length:
                        result = result[:max_length].rstrip()
                        logger.info(f"Template result truncated to {max_length} chars: '{result}'")
                    
                    return result
        
        # Fallback for unknown transformation types
        logger.warning(f"Unknown sites transformation type: {transform_type}")
        return record.get(transform_config.get('source', 'name'), '')
    
    @staticmethod
    def is_sites_transformation(transform_config: Dict[str, Any]) -> bool:
        """
        Check if this transformation is sites-related and needs special processing.
        
        Migrated from ZoomSitesHelper.is_sites_transformation() for sites transformation.
        
        Only returns True for transformations that are explicitly sites-specific,
        avoiding interference with standalone AR jobs.
        
        Args:
            transform_config: Transformation configuration dictionary
            
        Returns:
            True if this is a sites-specific transformation
        """
        if not isinstance(transform_config, dict):
            return False
        
        transform_type = transform_config.get('type')
        
        # Only match the explicit sites transformation type
        # Do NOT match based on field names or templates to avoid interfering with standalone AR jobs
        return transform_type == 'zoom_sites_ar_name'
    
    @staticmethod
    def validate_ar_name_length(ar_name: str, max_length: int = 30) -> Dict[str, Any]:
        """
        Validate that an AR name meets Zoom's length requirements.
        
        Migrated from ZoomSitesHelper.validate_ar_name_length() for sites transformation.
        
        Args:
            ar_name: The AR name to validate
            max_length: Maximum allowed length
            
        Returns:
            Dictionary with validation result and details
        """
        if not ar_name:
            return {
                'valid': False,
                'reason': 'AR name is empty',
                'length': 0,
                'max_length': max_length
            }
        
        length = len(ar_name)
        
        if length > max_length:
            return {
                'valid': False,
                'reason': f'AR name exceeds {max_length} character limit',
                'length': length,
                'max_length': max_length,
                'excess_chars': length - max_length
            }
        
        return {
            'valid': True,
            'reason': 'AR name meets length requirements',
            'length': length,
            'max_length': max_length,
            'remaining_chars': max_length - length
        }
    
    # === TIMEZONE TRANSFORMATION METHODS ===
    # Migrated from TimezoneConverter for timezone transformations
    
    @staticmethod
    def convert_to_iana_timezone(rc_timezone: str) -> str:
        """
        Convert RingCentral timezone format to IANA timezone format.
        
        Migrated from TimezoneConverter.convert_to_iana_timezone() for timezone transformation.
        
        Args:
            rc_timezone: RingCentral timezone string or existing IANA timezone
            
        Returns:
            IANA timezone string (e.g., 'America/Los_Angeles')
        """
        if not rc_timezone:
            logger.warning("No timezone provided, defaulting to America/Los_Angeles")
            return 'America/Los_Angeles'

        # Check if it's already in IANA format (e.g., America/New_York)
        if '/' in rc_timezone and (
            rc_timezone.startswith('America/') or 
            rc_timezone.startswith('Europe/') or 
            rc_timezone.startswith('Asia/') or 
            rc_timezone.startswith('Pacific/') or
            rc_timezone == 'UTC'
        ):
            return rc_timezone

        # Direct mapping lookup for RingCentral formats
        if rc_timezone in ZoomTransformerHelper.RC_TO_IANA_MAPPING:
            iana_timezone = ZoomTransformerHelper.RC_TO_IANA_MAPPING[rc_timezone]
            logger.info(f"Converted timezone: {rc_timezone} → {iana_timezone}")
            return iana_timezone
        
        # Fallback: try to parse common patterns
        rc_lower = rc_timezone.lower().strip()
        
        # Check for Pacific variations
        if 'pacific' in rc_lower:
            logger.info(f"Pacific timezone detected: {rc_timezone} → America/Los_Angeles")
            return 'America/Los_Angeles'
        
        # Check for Mountain variations
        elif 'mountain' in rc_lower:
            logger.info(f"Mountain timezone detected: {rc_timezone} → America/Denver")
            return 'America/Denver'
        
        # Check for Central variations  
        elif 'central' in rc_lower:
            logger.info(f"Central timezone detected: {rc_timezone} → America/Chicago")
            return 'America/Chicago'
        
        # Check for Eastern variations
        elif 'eastern' in rc_lower:
            logger.info(f"Eastern timezone detected: {rc_timezone} → America/New_York")
            return 'America/New_York'
        
        # Default fallback
        logger.warning(f"Unknown timezone format: {rc_timezone}, defaulting to America/Los_Angeles")
        return 'America/Los_Angeles'
    
    # === VALIDATION TRANSFORMATION METHODS ===
    # Migrated from ValidationService for data validation and transformation
    
    @staticmethod
    def apply_minimum_length_transformation(value: Any, config: Dict[str, Any]) -> str:
        """
        Apply minimum length transformation with padding.
        
        Migrated from ValidationService._apply_minimum_length_transformation() for data validation.
        
        Args:
            value: The value to transform
            config: Configuration containing min_length, padding_char, padding_direction
            
        Returns:
            Transformed string with minimum length applied
        """
        if value is None:
            return value
        
        str_value = str(value)
        
        # Support both new and legacy field names
        min_length = config.get('min_length', config.get('minimum_length', 3))
        pad_with = config.get('padding_char', config.get('pad_with', '0'))
        pad_direction = config.get('padding_direction', config.get('pad_direction', 'left'))
        
        if len(str_value) >= min_length:
            return str_value
        
        if pad_direction == 'right':
            return str_value.ljust(min_length, pad_with)
        else:  # left padding (default)
            return str_value.rjust(min_length, pad_with)
    
    @staticmethod
    def apply_custom_extension_format(value: Any, config: Dict[str, Any]) -> str:
        """
        Apply custom extension format transformation for Zoom compatibility.
        
        Migrated from ValidationService._apply_custom_extension_format() for data validation.
        
        Args:
            value: Extension value to format
            config: Configuration containing prefix, min_length
            
        Returns:
            Formatted extension string
        """
        logger.debug(f"EXTENSION_DEBUG: Input value='{value}' (type: {type(value)}), config={config}")
        
        if value is None:
            logger.debug(f"EXTENSION_DEBUG: Value is None, returning as-is")
            return value
        
        str_value = str(value).strip()
        prefix = config.get('prefix', '10')
        min_length = config.get('min_length', 3)
        
        logger.debug(f"EXTENSION_DEBUG: str_value='{str_value}', prefix='{prefix}', min_length={min_length}")
        
        # If already long enough, return as-is
        if len(str_value) >= min_length:
            logger.debug(f"EXTENSION_DEBUG: Value '{str_value}' already meets min_length {min_length}, returning as-is")
            return str_value
        
        # For single digits, prepend prefix (e.g., 2 -> 102, 3 -> 103)
        if len(str_value) == 1 and str_value.isdigit():
            result = prefix + str_value
            logger.info(f"EXTENSION_DEBUG: Single digit transformation: '{str_value}' → '{result}' (prefix: '{prefix}')")
            return result
        
        # For two digits, just prepend one digit from prefix
        elif len(str_value) == 2 and str_value.isdigit():
            result = prefix[0] + str_value
            logger.info(f"EXTENSION_DEBUG: Two digit transformation: '{str_value}' → '{result}' (prefix[0]: '{prefix[0]}')")
            return result
        
        # Fallback: just return the original value
        logger.warning(f"EXTENSION_DEBUG: Could not transform '{str_value}' (len={len(str_value)}, isdigit={str_value.isdigit()}), returning as-is")
        return str_value
    
    @staticmethod
    def extract_nested_field(record: Dict[str, Any], field_path: str) -> Any:
        """
        Extract nested field value using dot notation (e.g., 'extension.id').
        
        Migrated from ValidationService._extract_nested_field() for data validation.
        
        Args:
            record: The record to extract from
            field_path: Dot notation path (e.g., 'extension.id')
            
        Returns:
            Extracted field value or None if not found
        """
        logger.debug(f"EXTRACT_NESTED: Extracting '{field_path}' from record")
        
        if not field_path:
            logger.warning(f"EXTRACT_NESTED: Empty field path provided")
            return None
        
        # Split the path by dots
        path_parts = field_path.split('.')
        current_value = record
        
        try:
            for part in path_parts:
                if isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                    logger.debug(f"EXTRACT_NESTED: Found '{part}' = {current_value}")
                else:
                    logger.warning(f"EXTRACT_NESTED: Could not find '{part}' in {type(current_value)} {current_value}")
                    return None
            
            logger.info(f"EXTRACT_NESTED: Successfully extracted '{field_path}' = {current_value}")
            return current_value
            
        except Exception as e:
            logger.error(f"EXTRACT_NESTED: Error extracting '{field_path}': {str(e)}")
            return None
    
    # === PAYLOAD PROCESSOR TRANSFORMATION METHODS ===
    # Migrated from PayloadProcessorService for payload transformations
    
    @staticmethod
    def apply_concat_transformation(record: Dict[str, Any], transformation: str) -> str:
        """
        Apply concatenation transformation: concat(field1, field2, "literal").
        
        Migrated from PayloadProcessorService.apply_concat_transformation() for payload processing.
        
        Args:
            record: The record containing source data
            transformation: The concat transformation string
            
        Returns:
            Concatenated result string
        """
        # Extract content between parentheses
        content = transformation[7:-1]  # Remove "concat(" and ")"
        
        # Parse arguments (simple CSV parsing)
        args = []
        current_arg = ""
        in_quotes = False
        
        for char in content:
            if char == '"' and not in_quotes:
                in_quotes = True
            elif char == '"' and in_quotes:
                in_quotes = False
                args.append(current_arg)
                current_arg = ""
            elif char == ',' and not in_quotes:
                if current_arg.strip():
                    args.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char
        
        # Add the last argument
        if current_arg.strip():
            args.append(current_arg.strip())
        
        # Build concatenated result
        result_parts = []
        for arg in args:
            if arg.startswith('"') and arg.endswith('"'):
                # String literal
                result_parts.append(arg[1:-1])
            else:
                # Field reference
                value = ZoomTransformerHelper.get_nested_field(record, arg)
                if value is not None:
                    result_parts.append(str(value))
        
        return ' '.join(result_parts)
    
    @staticmethod
    def apply_user_type_mapping(record: Dict[str, Any], transformation: str) -> int:
        """
        Apply user type mapping transformation.
        
        Migrated from PayloadProcessorService.apply_user_type_mapping() for payload processing.
        
        Args:
            record: The record containing source data
            transformation: The transformation string
            
        Returns:
            Mapped user type as integer
        """
        # Extract field name from map_user_type(field)
        field_name = transformation[14:-1]  # Remove "map_user_type(" and ")"
        
        user_type = ZoomTransformerHelper.get_nested_field(record, field_name)
        if user_type == 'User':
            return 1
        elif user_type == 'DigitalUser':
            return 2
        else:
            return 1  # Default to User
    
    @staticmethod
    def apply_phone_number_formatting(record: Dict[str, Any], transformation: str) -> List[Dict[str, str]]:
        """
        Apply phone number formatting transformation.
        
        Migrated from PayloadProcessorService.apply_phone_number_formatting() for payload processing.
        
        Args:
            record: The record containing source data
            transformation: The transformation string
            
        Returns:
            Formatted phone number array
        """
        # Extract field name from format_phone(field)
        field_name = transformation[13:-1]  # Remove "format_phone(" and ")"
        
        phone_number = ZoomTransformerHelper.get_nested_field(record, field_name)
        if not phone_number:
            return []
        
        # Format as Zoom expects
        return [{"number": str(phone_number), "type": "office"}]
    
    @staticmethod
    def get_nested_field(record: Dict[str, Any], field_path: str) -> Any:
        """
        Get a nested field value using dot notation with array support.
        
        Migrated from PayloadProcessorService.get_nested_field() for payload processing.
        
        Args:
            record: The record to extract from
            field_path: Dot notation path with array support
            
        Returns:
            Field value or None if not found
        """
        try:
            # First, check if the field_path exists as a literal key (for fields like 'zoomMapping.action')
            if field_path in record:
                logger.debug(f"Found literal field '{field_path}' with value: {record[field_path]}")
                return record[field_path]
            
            # If not found as literal, try nested navigation with array support
            value = record
            path_parts = field_path.split('.')
            
            for part in path_parts:
                # Check if this part contains array notation
                if '[' in part and ']' in part:
                    # Extract the key and array index/wildcard
                    key_part = part[:part.index('[')]
                    index_part = part[part.index('[') + 1:part.index(']')]
                    
                    # Navigate to the array
                    if isinstance(value, dict) and key_part in value:
                        array_value = value[key_part]
                        logger.debug(f"Navigated to array '{key_part}', current value: {array_value}")
                        
                        if isinstance(array_value, list):
                            if index_part == '*':
                                # Return the entire array for wildcard
                                value = array_value
                                logger.debug(f"Returning entire array for wildcard: {len(array_value)} items")
                            else:
                                # Try to get specific index
                                try:
                                    index = int(index_part)
                                    if 0 <= index < len(array_value):
                                        value = array_value[index]
                                        logger.debug(f"Navigated to array index [{index}], current value: {value}")
                                    else:
                                        logger.debug(f"Array index [{index}] out of bounds for array of length {len(array_value)}")
                                        return None
                                except ValueError:
                                    logger.debug(f"Invalid array index '{index_part}' - not an integer")
                                    return None
                        else:
                            logger.debug(f"Field '{key_part}' is not an array: {type(array_value)}")
                            return None
                    else:
                        logger.debug(f"Cannot traverse '{key_part}' - current value is not a dict or key not found")
                        return None
                else:
                    # Regular field navigation
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                        logger.debug(f"Navigated to '{part}', current value: {value}")
                    else:
                        logger.debug(f"Cannot traverse '{part}' - current value is not a dict: {type(value)}")
                        return None
            
            logger.debug(f"Successfully resolved nested field path '{field_path}' to value: {value}")
            return value
        except Exception as e:
            logger.error(f"Error resolving field path '{field_path}': {str(e)}")
            return None
    
    @staticmethod
    def convert_country_to_iso(country_name: str) -> str:
        """
        Convert country name to ISO 3166-1 alpha-2 code.
        
        Migrated from PayloadProcessorService._convert_country_to_iso() for payload processing.
        
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
    
    @staticmethod
    def normalize_address_field(value: str) -> str:
        """
        Normalize address field casing for API compatibility.
        
        Migrated from PayloadProcessorService._normalize_address_field() for payload processing.
        
        Args:
            value: Address field value to normalize
            
        Returns:
            Normalized address field string
        """
        if not value or not isinstance(value, str):
            return value
        
        # First apply title case
        normalized = value.title()
        
        # Handle common abbreviations and special cases
        replacements = {
            ' Po ': ' PO ',      # PO Box
            ' Ne ': ' NE ',      # Northeast
            ' Nw ': ' NW ',      # Northwest
            ' Se ': ' SE ',      # Southeast
            ' Sw ': ' SW ',      # Southwest
            ' Ct ': ' CT ',      # Court
            ' St ': ' ST ',      # Street
            ' Ave ': ' AVE ',    # Avenue
            ' Blvd ': ' BLVD ',  # Boulevard
            ' Dr ': ' DR ',      # Drive
            ' Ln ': ' LN ',      # Lane
            ' Rd ': ' RD ',      # Road
            ' Apt ': ' APT ',    # Apartment
            ' Ste ': ' STE ',    # Suite
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Handle cases at the end of string
        end_replacements = {
            ' Ct': ' CT',
            ' St': ' ST',
            ' Ave': ' AVE',
            ' Blvd': ' BLVD',
            ' Dr': ' DR',
            ' Ln': ' LN',
            ' Rd': ' RD',
        }
        
        for old, new in end_replacements.items():
            if normalized.endswith(old):
                normalized = normalized[:-len(old)] + new
        
        return normalized
    
    @staticmethod
    def apply_timezone_conversion(record: Dict[str, Any], transformation: str) -> str:
        """
        Apply timezone conversion transformation.
        
        Migrated from PayloadProcessorService._apply_timezone_conversion() for payload processing.
        
        Args:
            record: The record containing source data
            transformation: The transformation string
            
        Returns:
            Converted timezone string
        """
        # Extract field name from convert_timezone_to_iana(field)
        field_name = transformation[25:-1]  # Remove "convert_timezone_to_iana(" and ")"
        timezone_value = ZoomTransformerHelper.get_nested_field(record, field_name)
        if timezone_value:
            return ZoomTransformerHelper.convert_to_iana_timezone(timezone_value)
        return timezone_value
    
    @staticmethod
    def get_nested_field_with_multi_lookup(record: Dict[str, Any], field_path: str) -> List[Any]:
        """
        Get nested field values supporting multi-lookup for array patterns.
        
        Migrated from PayloadProcessorService.get_nested_field_with_multi_lookup() for payload processing.
        
        Args:
            record: The record to extract from
            field_path: Dot notation path with [*] wildcard support
            
        Returns:
            List of field values
        """
        try:
            # Check if field_path contains [*] wildcard
            if '[*]' in field_path:
                # Split path into parts before and after [*]
                base_path = field_path[:field_path.index('[*]')]
                remaining_path = field_path[field_path.index('[*]') + 3:]
                
                # Remove leading dot if present
                if remaining_path.startswith('.'):
                    remaining_path = remaining_path[1:]
                
                # Get the array using base path
                array_value = ZoomTransformerHelper.get_nested_field(record, base_path)
                
                if isinstance(array_value, list):
                    results = []
                    for item in array_value:
                        if remaining_path:
                            # Navigate further into each array item
                            item_value = ZoomTransformerHelper.get_nested_field(item, remaining_path)
                            # CRITICAL: Always append to preserve array indices, even for null values
                            results.append(item_value)
                        else:
                            # Return the item itself if no remaining path
                            results.append(item)
                    
                    logger.debug(f"Multi-lookup for '{field_path}' returned {len(results)} results")
                    return results
                else:
                    logger.debug(f"Base path '{base_path}' is not an array: {type(array_value)}")
                    return []
            else:
                # Regular single field lookup
                value = ZoomTransformerHelper.get_nested_field(record, field_path)
                return [value] if value is not None else []
                
        except Exception as e:
            logger.error(f"Error in multi-lookup for field path '{field_path}': {str(e)}")
            return []
    
    def transform_sites_data(self, sites_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform sites data for JobType 33 (RingCentral to Zoom - Sites).
        
        This applies all the transformations that were previously in the loader config:
        - Emergency address transformation
        - Timezone conversion
        - Auto receptionist naming
        
        Args:
            sites_records: List of site records from extraction
            
        Returns:
            List of transformed site records ready for loading
        """
        transformed_records = []
        
        for record in sites_records:
            try:
                transformed_record = {
                    # Copy basic fields
                    'id': record.get('id'),
                    'name': record.get('name'),
                    'caller_id_name': record.get('callerIdName'),
                    
                    # Transform emergency address
                    'default_emergency_address': self.transform_emergency_address(
                        record.get('businessAddress', {})
                    ),
                    
                    # Generate auto receptionist name
                    'auto_receptionist_name': f"{record.get('name', '')} (NOT IN USE)",
                    
                    # Transform regional settings
                    'regionalSettings': self._transform_regional_settings(record.get('regionalSettings', {}))
                }
                
                transformed_records.append(transformed_record)
                
            except Exception as e:
                self.logger.error(f"Error transforming site record {record.get('id', 'unknown')}: {str(e)}")
                continue
        
        self.logger.info(f"Transformed {len(transformed_records)} site records")
        return transformed_records
    
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

    @staticmethod
    def replace_template_placeholders(template: str, record: Dict[str, Any]) -> str:
        """
        Replace template placeholders with values from record.

        Migrated from PayloadProcessor._replace_template_placeholders() for template processing.

        Args:
            template: Template string with placeholders
            record: Source record dictionary

        Returns:
            String with placeholders replaced
        """
        try:
            result = template

            # Find and replace all {field_path} placeholders (single braces)
            import re
            pattern = r'\{([^}]+)\}'
            matches = re.findall(pattern, template)

            for field_path in matches:
                field_path = field_path.strip()
                value = ZoomTransformerHelper.get_nested_field(record, field_path)

                if value is not None:
                    result = result.replace(f"{{{field_path}}}", str(value))
                else:
                    result = result.replace(f"{{{field_path}}}", "")

            return result

        except Exception as e:
            logger.error(f"Error replacing template placeholders: {str(e)}")
            return template

    # === USERS TRANSFORMATION METHODS ===
    # Migrated from Users loader transformations for JobType 39

    @staticmethod
    def map_user_type_to_zoom(rc_user_type: str) -> int:
        """
        Map RingCentral user type to Zoom user type integer.

        Migrated from Users loader transformation for JobType 39.

        Args:
            rc_user_type: RingCentral user type string

        Returns:
            Zoom user type integer (1=User, 2=DigitalUser, 99=Other)
        """
        user_type_mapping = {
            'User': 1,
            'DigitalUser': 2,
            'FlexibleUser': 1,  # Map to regular user
            'FaxUser': 99,
            'VirtualUser': 99,
            'Department': 99,
            'Announcement': 99,
            'Voicemail': 99,
            'SharedLinesGroup': 99,
            'PagingOnly': 99,
            'IvrMenu': 99,
            'ApplicationExtension': 99,
            'ParkLocation': 99,
            'Limited': 99,
            'Bot': 99,
            'ProxyAdmin': 99,
            'DelegatedLinesGroup': 99,
            'Site': 99
        }

        zoom_type = user_type_mapping.get(rc_user_type, 99)
        if zoom_type == 99 and rc_user_type:
            logger.warning(f"Unknown RingCentral user type '{rc_user_type}', mapping to 99 (Other)")
        else:
            logger.info(f"Mapped RingCentral user type '{rc_user_type}' → Zoom type {zoom_type}")

        return zoom_type

    @staticmethod
    def concat_user_display_name(first_name: str, last_name: str) -> str:
        """
        Concatenate first and last name for user display name.

        Migrated from Users loader transformation for JobType 39.

        Args:
            first_name: User's first name
            last_name: User's last name

        Returns:
            Concatenated display name
        """
        if not first_name and not last_name:
            logger.warning("Both first_name and last_name are empty")
            return ""

        if first_name and last_name:
            display_name = f"{first_name} {last_name}"
        elif first_name:
            display_name = first_name
        elif last_name:
            display_name = last_name
        else:
            display_name = ""

        logger.info(f"Generated display name: '{display_name}' from '{first_name}' + '{last_name}'")
        return display_name

    @staticmethod
    def format_user_phone_numbers(phone_numbers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Format RingCentral phone numbers for Zoom user creation.

        Migrated from Users loader transformation for JobType 39.

        Args:
            phone_numbers: List of RingCentral phone number objects

        Returns:
            List of formatted phone number objects for Zoom
        """
        if not isinstance(phone_numbers, list):
            logger.warning(f"phone_numbers is not a list: {type(phone_numbers)}")
            return []

        formatted_numbers = []

        for phone_obj in phone_numbers:
            if not isinstance(phone_obj, dict):
                logger.warning(f"Skipping invalid phone object: {phone_obj}")
                continue

            phone_type = phone_obj.get('type', '').lower()
            phone_number = phone_obj.get('number', '')

            if not phone_number:
                logger.debug(f"Skipping phone object without number: {phone_obj}")
                continue

            # Map RingCentral phone types to Zoom format
            zoom_type_mapping = {
                'work': 'office',
                'home': 'home',
                'mobile': 'mobile',
                'business': 'office',
                'direct': 'office'
            }

            zoom_type = zoom_type_mapping.get(phone_type, 'office')

            formatted_phone = {
                'number': str(phone_number),
                'type': zoom_type
            }

            formatted_numbers.append(formatted_phone)
            logger.debug(f"Formatted phone: {phone_type} → {zoom_type}, number: {phone_number}")

        logger.info(f"Formatted {len(formatted_numbers)} phone numbers")
        return formatted_numbers

    @staticmethod
    def convert_timezone_to_ringcentral_id(timezone_str: str) -> str:
        """
        Convert timezone string to RingCentral numeric timezone ID.
        
        Migrated from PayloadProcessor._convert_timezone_to_ringcentral_id() for timezone transformation.
        
        Args:
            timezone_str: Timezone string to convert
            
        Returns:
            RingCentral timezone ID string
        """
        try:
            # Basic mapping for common timezones to RingCentral IDs
            timezone_mapping = {
                'America/New_York': '58',  # Eastern
                'America/Chicago': '11',   # Central
                'America/Denver': '50',    # Mountain
                'America/Los_Angeles': '62', # Pacific
                'America/Phoenix': '27',   # Arizona
                'America/Anchorage': '6',  # Alaska
                'Pacific/Honolulu': '30',  # Hawaii
            }
            
            # Try exact match first
            if timezone_str in timezone_mapping:
                return timezone_mapping[timezone_str]
            
            # Fallback to Eastern timezone
            logger.warning(f"Unknown timezone '{timezone_str}', using fallback Eastern timezone")
            return '58'  # Eastern
            
        except Exception as e:
            logger.error(f"Error converting timezone {timezone_str}: {str(e)}")
            return '58'  # Default fallback
    

class ZoomSitesTransformerHelper(ZoomTransformerHelper):
    """Specific helper for Sites transformations (JobType 33)."""
    
    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main transformation entry point for sites data.
        
        Args:
            data: Extracted sites data
            
        Returns:
            Transformed sites data ready for loading
        """
        return self.transform_sites_data(data)


    # === ADDITIONAL PAYLOAD PROCESSOR TRANSFORMATION METHODS ===
    # Migrated from PayloadProcessorService for comprehensive payload transformations
    
    @staticmethod
    def apply_dtmf_cleanup_transformation(record: Dict[str, Any], rule_config: Dict[str, Any]) -> None:
        """
        Apply DTMF cleanup transformations to nested arrays.
        
        Migrated from PayloadProcessor.apply_dtmf_cleanup_transformation() for DTMF processing.
        
        Args:
            record: Source record dictionary (modified in place)
            rule_config: DTMF cleanup rule configuration
        """
        try:
            field_path = rule_config.get('field')
            cleanup_rules = rule_config.get('cleanup_rules', {})
            
            if not field_path:
                return
            
            # Get the array to clean
            source_array = ZoomTransformerHelper.get_nested_field(record, field_path)
            if not isinstance(source_array, list):
                return
            
            cleaned_items = []
            for item in source_array:
                if isinstance(item, dict):
                    cleaned_item = ZoomTransformerHelper._clean_dtmf_item(item, cleanup_rules, record)
                    if cleaned_item is not None:
                        cleaned_items.append(cleaned_item)
            
            # Update the record with cleaned items
            ZoomTransformerHelper._set_nested_value(record, field_path, cleaned_items)
            
        except Exception as e:
            logger.error(f"Error applying DTMF cleanup transformation: {str(e)}")

    @staticmethod
    def _clean_dtmf_item(dtmf_item: Dict[str, Any], rule_config: Dict[str, Any], record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean a single DTMF item based on cleanup rules.
        
        Migrated from PayloadProcessor._clean_dtmf_item() for DTMF processing.
        
        Args:
            dtmf_item: DTMF item to clean
            rule_config: Cleanup rule configuration
            record: Full record for context
            
        Returns:
            Cleaned DTMF item or None if should be filtered out
        """
        try:
            cleaned_item = dtmf_item.copy()
            
            # Apply field transformations
            field_transformations = rule_config.get('field_transformations', {})
            for field_name, transform_rules in field_transformations.items():
                if field_name in cleaned_item:
                    field_value = cleaned_item[field_name]
                    
                    # Apply value mappings
                    value_mapping = transform_rules.get('value_mapping', {})
                    if isinstance(field_value, str) and field_value in value_mapping:
                        cleaned_item[field_name] = value_mapping[field_value]
            
            # Apply filters
            filters = rule_config.get('filters', {})
            for filter_type, filter_config in filters.items():
                if filter_type == 'exclude_if_field_value':
                    field_name = filter_config.get('field')
                    excluded_values = filter_config.get('values', [])
                    
                    if field_name in cleaned_item:
                        field_value = cleaned_item[field_name]
                        if field_value in excluded_values:
                            return None
            
            return cleaned_item
            
        except Exception as e:
            logger.error(f"Error cleaning DTMF item: {str(e)}")
            return dtmf_item

    @staticmethod  
    def _set_nested_value(record: Dict[str, Any], field_path: str, value: Any) -> None:
        """
        Set a nested field value in a record dictionary.
        
        Migrated from PayloadProcessor._set_nested_value() for nested field updates.
        
        Args:
            record: Record dictionary to update
            field_path: Dot-notation field path
            value: Value to set
        """
        try:
            keys = field_path.split('.')
            current = record
            
            # Navigate to the parent of the target field
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set the target field
            current[keys[-1]] = value
            
        except Exception as e:
            logger.error(f"Error setting nested value at {field_path}: {str(e)}")



    @staticmethod
    def generate_incremental_counter(counter_key: str, start_value: int = 1, prefix: str = "", pad_length: int = 0) -> str:
        """
        Generate incremental counter value.
        
        Migrated from PayloadProcessor counter logic for incremental transformations.
        
        Args:
            counter_key: Unique key for the counter
            start_value: Starting value for counter
            prefix: String prefix for counter
            pad_length: Zero-pad the counter to this length
            
        Returns:
            Formatted counter string
        """
        try:
            # For now, return a simple counter format
            # In production, this would need proper counter persistence
            counter_value = start_value
            
            # Apply padding if specified
            if pad_length > 0:
                counter_str = str(counter_value).zfill(pad_length)
            else:
                counter_str = str(counter_value)
            
            # Combine with prefix
            result = f"{prefix}{counter_str}"
            return result
            
        except Exception as e:
            logger.error(f"Error generating counter {counter_key}: {str(e)}")
            return f"{prefix}1"

    @staticmethod
    def apply_address_transformation(record: Dict[str, Any], transform_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply address transformation with fallback logic.
        
        Migrated from PayloadProcessor address transformation logic.
        
        Args:
            record: Source record dictionary
            transform_config: Address transformation configuration
            
        Returns:
            Transformed address dictionary
        """
        try:
            source_fields = transform_config.get('source_fields', {})
            fallback_source = transform_config.get('fallback_source')
            fallback_mapping = transform_config.get('fallback_mapping', {})
            
            # Build address object
            address = {}
            missing_fields = []
            
            # First, try to populate from primary source fields
            for target_field, source_field in source_fields.items():
                # Handle static boolean values
                if isinstance(source_field, bool):
                    address[target_field] = source_field
                elif source_field in record and record[source_field]:
                    # Normalize street and city fields
                    if target_field in ['street', 'street2', 'city']:
                        address[target_field] = ZoomTransformerHelper.normalize_address_field(record[source_field])
                    else:
                        address[target_field] = record[source_field]
                else:
                    missing_fields.append(target_field)
            
            # Then, fill in any missing fields from fallback
            if missing_fields and fallback_source and fallback_mapping:
                for target_field, source_field in fallback_mapping.items():
                    # Only use fallback if the field is missing
                    if target_field in missing_fields:
                        # Handle static boolean values
                        if isinstance(source_field, bool):
                            address[target_field] = source_field
                        elif source_field in record and record[source_field]:
                            # Normalize street and city fields
                            if target_field in ['street', 'street2', 'city']:
                                address[target_field] = ZoomTransformerHelper.normalize_address_field(record[source_field])
                            else:
                                address[target_field] = record[source_field]
            
            return address
            
        except Exception as e:
            logger.error(f"Error applying address transformation: {str(e)}")
            return {}


# Additional helper classes will be added here for other JobTypes
# class ZoomUsersTransformerHelper(ZoomTransformerHelper): # JobType 39
# class ZoomCallQueuesTransformerHelper(ZoomTransformerHelper): # JobType 45  
# class ZoomAutoReceptionistTransformerHelper(ZoomTransformerHelper): # JobType 77
# class ZoomIVRTransformerHelper(ZoomTransformerHelper): # JobType 78