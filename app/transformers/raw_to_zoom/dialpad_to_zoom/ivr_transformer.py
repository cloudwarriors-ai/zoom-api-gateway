from typing import Any, Dict, List, Optional
from datetime import datetime

from app.transformers.base_transformer import BaseTransformer


class DialpadIvrToZoomTransformer(BaseTransformer):
    """
    Transformer for converting Dialpad IVR/DTMF routing data to RingCentral-equivalent format.
    
    This transformer takes Dialpad raw office routing options and converts them to match the exact
    format that RingCentral IVR produces after transformation, so that the same
    RingCentral→Zoom IVR loader can be reused without modification.
    
    Maps Dialpad routing_options.dtmf to RingCentral ivr_actions format.
    """
    
    def __init__(self, job_type_code: Optional[str] = None, config_id: Optional[str] = None):
        """
        Initialize the DialpadIvrToZoomTransformer.
        
        Args:
            job_type_code: The job type code for this transformation
            config_id: Optional identifier for a specific transformation configuration
        """
        super().__init__()
        self.job_type_code = job_type_code
        
        # Dialpad to Zoom action mapping - reusing logic from zoom_transformer_helper.py
        self.action_mapping = {
            # Target-specific mappings (will be refined based on target type)
            'operator': 2,        # Forward to user (operator)
            'department': 7,      # Forward to call queue/department  
            'voicemail': 200,     # Leave voicemail to user
            'directory': 4,       # Forward to common area / directory
            'disabled': -1,       # Disabled action
            # Universal mappings  
            'repeat': 21,         # Repeat menu greeting
            'disconnect': -1,     # Disabled/disconnect
        }
        
        self.logger.info("DialpadIvrToZoomTransformer initialized")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Dialpad office routing data to RingCentral IVR format.
        
        This converts Dialpad routing_options structure to match what RingCentral IVR looks like
        after transformation, so the same loader can handle both sources.
        
        Args:
            data: Dialpad office data dictionary containing routing_options
            
        Returns:
            Transformed IVR record matching RingCentral transformed format
        """
        try:
            # Create the RingCentral-equivalent structure  
            # Based on RingCentral jobtype 78 transformed format
            transformed_record = {
                # Core fields that match RingCentral structure
                "id": str(data.get('id', data.get('office_id', ''))),
                "name": data.get('name', ''),
                "extensionNumber": str(data.get('office_id', data.get('id', ''))),
                "site.id": self._determine_site_id(data),
                
                # Transform the routing options to ivr_actions
                "ivr_actions": self._transform_routing_options_to_ivr_actions(data),
                
                # Add record tracking
                "record_id": data.get('record_id', f"dialpad_ivr_{data.get('id', 'unknown')}")
            }
            
            self.logger.info(f"Transformed Dialpad IVR {data.get('id', 'unknown')} with {len(transformed_record.get('ivr_actions', []))} actions")
            return transformed_record
            
        except Exception as e:
            self.logger.error(f"Error transforming Dialpad IVR data: {str(e)}")
            self.logger.error(f"Input data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            # Return a minimal valid structure to avoid breaking the pipeline
            return {
                "id": str(data.get('id', data.get('office_id', 'unknown'))),
                "name": data.get('name', 'Unknown Office'),
                "extensionNumber": str(data.get('office_id', data.get('id', '0'))),
                "site.id": "main-site", 
                "ivr_actions": [],
                "record_id": data.get('record_id', f"dialpad_ivr_{data.get('id', 'unknown')}")
            }
    
    def _transform_routing_options_to_ivr_actions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform Dialpad routing_options.dtmf to RingCentral ivr_actions format.
        
        Args:
            data: Dialpad office data with routing_options
            
        Returns:
            List of IVR action objects matching RingCentral format
        """
        ivr_actions = []
        
        try:
            routing_options = data.get('routing_options', {})
            if not routing_options:
                self.logger.warning(f"No routing_options found in data for office {data.get('id', 'unknown')}")
                return []
            
            # Process both 'open' and 'closed' routing options
            for state in ['open', 'closed']:
                state_options = routing_options.get(state, {})
                if not state_options:
                    continue
                
                dtmf_options = state_options.get('dtmf', [])
                if not isinstance(dtmf_options, list):
                    continue
                
                # Transform each DTMF option
                for dtmf_item in dtmf_options:
                    if not isinstance(dtmf_item, dict):
                        continue
                    
                    action = self._transform_single_dtmf_action(dtmf_item, data)
                    if action:
                        ivr_actions.append(action)
            
            # Add timeout action if no operators are available or based on no_operators_action
            timeout_action = self._create_timeout_action(data)
            if timeout_action:
                ivr_actions.append(timeout_action)
            
            self.logger.info(f"Created {len(ivr_actions)} IVR actions from routing options")
            return ivr_actions
            
        except Exception as e:
            self.logger.error(f"Error transforming routing options: {str(e)}")
            return []
    
    def _transform_single_dtmf_action(self, dtmf_item: Dict[str, Any], full_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Transform a single DTMF item to RingCentral IVR action format.
        
        Args:
            dtmf_item: Single DTMF configuration item
            full_data: Full office data for context
            
        Returns:
            Transformed IVR action or None if invalid
        """
        try:
            input_key = dtmf_item.get('input', '')
            options = dtmf_item.get('options', {})
            
            if not input_key or not options:
                return None
            
            # Map input key (Dialpad uses strings like "0", "1" directly)  
            zoom_key = self._map_input_key(input_key)
            
            # Get the action from options
            dialpad_action = options.get('action', '')
            
            # Map action to Zoom action code
            zoom_action_code = self._map_dialpad_action_to_zoom(dialpad_action, options)
            
            # Build the action object
            action = {
                "key": zoom_key,
                "action": zoom_action_code
            }
            
            # Add target information if needed
            target_info = self._build_target_info(options, dialpad_action)
            if target_info:
                action["target"] = target_info
            
            self.logger.debug(f"Transformed DTMF: {input_key}→{dialpad_action} to {zoom_key}→{zoom_action_code}")
            return action
            
        except Exception as e:
            self.logger.error(f"Error transforming single DTMF action: {str(e)}")
            return None
    
    def _map_input_key(self, dialpad_input: str) -> str:
        """
        Map Dialpad input key to Zoom format.
        
        Args:
            dialpad_input: Dialpad input key
            
        Returns:
            Zoom-compatible input key
        """
        # Dialpad uses direct strings, Zoom also uses strings
        # Most mappings are direct, but handle any special cases
        key_mapping = {
            'star': '*',
            'hash': '#',
            'pound': '#',
            '*': '*',
            '#': '#'
        }
        
        return key_mapping.get(dialpad_input.lower(), dialpad_input)
    
    def _map_dialpad_action_to_zoom(self, dialpad_action: str, options: Dict[str, Any]) -> int:
        """
        Map Dialpad action to appropriate Zoom action integer.
        
        Args:
            dialpad_action: Dialpad action string
            options: Full options dict for context
            
        Returns:
            Zoom action integer code
        """
        # Determine target type to get the right action code
        target_type = self._determine_target_type(options)
        
        # Base mapping - can be refined based on target type
        if dialpad_action == 'operator':
            return 2  # Forward to user (operator)
        elif dialpad_action == 'department':
            return 7  # Forward to call queue/department
        elif dialpad_action == 'voicemail':
            # Different voicemail codes based on target type
            if target_type == 'call_queue':
                return 400  # Voicemail to call queue
            elif target_type == 'auto_receptionist': 
                return 300  # Voicemail to auto receptionist
            else:
                return 200  # Voicemail to user
        elif dialpad_action == 'directory':
            return 4   # Forward to common area
        elif dialpad_action == 'disabled':
            return -1  # Disabled
        else:
            self.logger.warning(f"Unknown Dialpad action '{dialpad_action}', using -1 (disabled)")
            return -1
    
    def _determine_target_type(self, options: Dict[str, Any]) -> str:
        """
        Determine the target type from Dialpad options.
        
        Args:
            options: DTMF options dictionary
            
        Returns:
            Target type string
        """
        # Analyze the options to determine what type of target this is
        action_target_type = options.get('action_target_type', '')
        action_target_id = options.get('action_target_id', '')
        action = options.get('action', '')
        
        if action == 'department' or action_target_type == 'department':
            return 'call_queue'  # Departments are typically call queues
        elif action == 'operator':
            return 'user'  # Operators are users
        elif action_target_type == 'office':
            return 'auto_receptionist'  # Office targets are auto receptionists
        else:
            return 'user'  # Default to user
    
    def _build_target_info(self, options: Dict[str, Any], action: str) -> Optional[Dict[str, Any]]:
        """
        Build target information for actions that need targets.
        
        Args:
            options: DTMF options dictionary
            action: Dialpad action string
            
        Returns:
            Target information dictionary or None
        """
        # Actions that don't need targets
        no_target_actions = ['disabled', 'directory', 'repeat']
        if action in no_target_actions:
            return None
        
        # Get target ID and type
        target_id = options.get('action_target_id', '')
        target_type = self._determine_target_type(options)
        
        if not target_id:
            return None
        
        # Map target type to Zoom format
        zoom_target_type_mapping = {
            'user': 'user',
            'call_queue': 'call_queue',
            'auto_receptionist': 'auto_receptionist'
        }
        
        return {
            "type": zoom_target_type_mapping.get(target_type, 'user'),
            "extension_id": str(target_id)  # Keep as string for loader to resolve
        }
    
    def _create_timeout_action(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create timeout action based on no_operators_action or default behavior.
        
        Args:
            data: Full office data
            
        Returns:
            Timeout action or None
        """
        no_operators_action = data.get('no_operators_action', 'voicemail')
        
        # Map the no operators action to timeout action
        if no_operators_action == 'voicemail':
            action_code = 200  # Voicemail to user
        elif no_operators_action == 'disconnect':
            action_code = -1   # Disabled/disconnect
        else:
            action_code = -1   # Default to disabled
        
        return {
            "key": "timeout",
            "action": action_code
        }
    
    def _determine_site_id(self, data: Dict[str, Any]) -> str:
        """
        Determine the site ID for the office.
        
        For Dialpad to Zoom, the site ID should match the office ID since each Dialpad office
        corresponds to a Zoom site. This enables proper dependency resolution between
        the site loader and IVR loader.
        
        Args:
            data: Dialpad office data
            
        Returns:
            Site ID string matching the office ID
        """
        # Use the office ID as the site ID for proper dependency mapping
        # This ensures the IVR can find the corresponding site
        return str(data.get('id', data.get('office_id', '')))
    
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
        required_fields = ["id", "name", "extensionNumber", "ivr_actions"]
        
        for field in required_fields:
            if field not in transformed_data:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["is_valid"] = False
        
        # Check IVR actions structure
        ivr_actions = transformed_data.get("ivr_actions", [])
        if not isinstance(ivr_actions, list):
            validation_result["errors"].append("ivr_actions must be a list")
            validation_result["is_valid"] = False
        else:
            for i, action in enumerate(ivr_actions):
                if not isinstance(action, dict):
                    validation_result["errors"].append(f"ivr_actions[{i}] must be a dictionary")
                elif "key" not in action or "action" not in action:
                    validation_result["errors"].append(f"ivr_actions[{i}] missing required fields (key, action)")
        
        # Check if we actually found routing options to transform
        original_routing = original_data.get('routing_options', {})
        if original_routing and not ivr_actions:
            validation_result["warnings"].append("Found routing options in original data but no IVR actions were generated")
        
        return validation_result