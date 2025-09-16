from typing import Any, Dict, List, Optional
import logging

from app.transformers.base_transformer import BaseTransformer

logger = logging.getLogger(__name__)


class RingCentralToZoomIVRTransformer(BaseTransformer):
    """
    Transformer for converting RingCentral IVR data to Zoom IVR format.
    
    This transformer handles the mapping of IVR (Interactive Voice Response)
    data from RingCentral's format to the format required by Zoom's API.
    """
    
    # Input key mappings from RingCentral to Zoom (from ZoomTransformerHelper)
    INPUT_KEY_MAPPINGS = {
        'Star': '*',
        'Hash': '#',
        'NoInput': 'timeout',
        # Numbers stay the same: '1' -> '1', '2' -> '2', etc.
    }
    
    def __init__(self):
        """
        Initialize the RingCentralToZoomIVRTransformer.
        """
        super().__init__()
        self.job_type_code = "rc_zoom_ivr"
        self.source_format = "ringcentral"
        self.target_format = "zoom"
        
        self.logger.info(f"RingCentralToZoomIVRTransformer initialized for job_type_code: {self.job_type_code}")
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform RingCentral IVR data to Zoom IVR format.
        
        This matches exactly what the working system does in dynamic_transformer.py:
        - Copies ALL original data
        - Processes ivr_details[0].actions → ivr_actions using transform_ivr_action
        - Removes ivr_details field
        
        Args:
            data: RingCentral IVR data dictionary
            
        Returns:
            Transformed IVR record with original data plus ivr_actions
        """
        try:
            # This matches dynamic_transformer.py line 124 exactly
            transformed = dict(data)  # Copy ALL original data
            
            # Process IVR actions like the working system does (lines 125-142)
            if 'ivr_details' in data and isinstance(data['ivr_details'], list) and len(data['ivr_details']) > 0:
                ivr_detail = data['ivr_details'][0]
                if 'actions' in ivr_detail:
                    # Get job group ID for extension type detection (we'll use None for now)
                    job_group_id = None
                    
                    transformed_actions = []
                    self.logger.info(f"IVR_DEBUG: Processing {len(ivr_detail['actions'])} actions from ivr_details")
                    
                    for i, action in enumerate(ivr_detail['actions']):
                        self.logger.info(f"IVR_DEBUG: Processing action {i+1}: {action}")
                        transformed_action = self.transform_ivr_action(action, job_group_id)
                        self.logger.info(f"IVR_DEBUG: Transformed action {i+1} result: {transformed_action}")
                        
                        if transformed_action:
                            transformed_actions.append(transformed_action)
                        else:
                            self.logger.warning(f"IVR_DEBUG: Action {i+1} returned None, skipping")
                    
                    transformed['ivr_actions'] = transformed_actions
                    self.logger.info(f"IVR_DEBUG: Successfully transformed {len(transformed_actions)} out of {len(ivr_detail['actions'])} IVR actions")
                
                # Remove original field after transformation (line 144)
                del transformed['ivr_details']
            else:
                self.logger.info(f"IVR_DEBUG: No IVR details found for IVR transformation. Item keys: {list(data.keys())}")
                if 'ivr_details' in data:
                    self.logger.info(f"IVR_DEBUG: ivr_details exists but is: {data['ivr_details']}")
            
            self.logger.info(f"IVR_DEBUG: Returning transformed IVR item with keys: {list(transformed.keys())}")
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming IVR data: {str(e)}")
            raise ValueError("Invalid input data for RingCentral IVR transformation")
    
    def transform_ivr_action(self, action: Dict[str, Any], job_group_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Transform a single IVR action from RingCentral format to Zoom format.
        
        This matches exactly what ZoomTransformerHelper.transform_ivr_action() does.
        
        Args:
            action: Single IVR action from RingCentral ivr_details[0].actions
            job_group_id: Optional job group ID for extension type detection
            
        Returns:
            Transformed action in Zoom format, or None if transformation fails
        """
        if not isinstance(action, dict):
            self.logger.warning(f"Invalid action format, expected dict: {action}")
            return None
            
        try:
            self.logger.info(f"IVR_DEBUG: transform_ivr_action START")
            transformed = {}
            
            # 1. Handle key field (input mapping)
            if 'input' in action:
                # RingCentral format - transform input to key
                rc_input = action.get('input', '')
                transformed['key'] = self.map_input_key(rc_input)
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
                
            self.logger.info(f"IVR_DEBUG: job_group_id={job_group_id}, extension_id={extension_id}")
            # For now, we'll use the default 'user' type since we don't have job group data
            
            # 3. Map action to Zoom action code
            if 'action' in action:
                rc_action = action.get('action')
                action_code = self.map_action_to_code(rc_action, target_type)
                transformed['action'] = action_code
                
                # 4. Add target information if extension exists and action requires target
                if extension_id and action_code not in [-1, 21, 22, 23]:  # Actions that don't need targets
                    transformed['target'] = {
                        'type': target_type,
                        'extension_id': str(extension_id)
                    }
            
            self.logger.info(f"IVR_DEBUG: transform_ivr_action result: {transformed}")
            return transformed
            
        except Exception as e:
            self.logger.error(f"Error transforming IVR action: {str(e)}")
            return None
    
    def map_input_key(self, rc_input: str) -> str:
        """
        Map RingCentral input key to Zoom format.
        
        Args:
            rc_input: RingCentral input key ('Star', 'Hash', '1', '2', etc.)
            
        Returns:
            Zoom-compatible input key ('*', '#', '1', '2', etc.)
        """
        mapped_key = self.INPUT_KEY_MAPPINGS.get(rc_input, rc_input)
        if mapped_key != rc_input:
            self.logger.info(f"INPUT_MAPPING: Mapped '{rc_input}' → '{mapped_key}'")
        return mapped_key
    
    def map_action_to_code(self, rc_action: str, target_type: str = 'user') -> int:
        """
        Map RingCentral action to Zoom action integer code.
        
        Args:
            rc_action: RingCentral action string ('Connect', 'Voicemail', etc.)
            target_type: Target type ('user', 'call_queue', 'auto_receptionist')
            
        Returns:
            Zoom action integer code
        """
        # Target-specific action mappings (from ZoomTransformerHelper)
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
                'Connect': 8,           # Forward to auto receptionist
                'Voicemail': 300,       # Leave voicemail to auto receptionist
                'Transfer': 10,         # Forward to phone number
                'ConnectToOperator': 8, # Forward to auto receptionist (operator)
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
            self.logger.info(f"ACTION_MAPPING: Universal action '{rc_action}' → {action_code}")
            return action_code
        
        # Check target-specific mappings
        if target_type in type_specific_mappings:
            target_mappings = type_specific_mappings[target_type]
            if rc_action in target_mappings:
                action_code = target_mappings[rc_action]
                self.logger.info(f"ACTION_MAPPING: '{rc_action}' for {target_type} → {action_code}")
                return action_code
        
        # Fallback for unknown actions
        self.logger.warning(f"ACTION_MAPPING: Unknown action '{rc_action}' for target_type '{target_type}', using -1 (disabled)")
        return -1
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate the input RingCentral IVR data.
        
        Args:
            data: RingCentral IVR data to validate
            
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
        Validate the output Zoom IVR data.
        
        Args:
            data: Zoom IVR data to validate
            
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
        
        # If ivr_details was in input, ivr_actions should be in output
        if "ivr_details" in data:
            self.logger.warning("ivr_details still present - should have been removed")
        
        return True