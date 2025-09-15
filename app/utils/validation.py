"""
Data Validation Utilities for Zoom Platform Microservice

This module contains data validation utilities extracted from the original
ZoomTransformerHelper class. It provides standardized methods for validating
and sanitizing data across different platform transformations.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Callable

logger = logging.getLogger(__name__)


def extract_nested_field(record: Dict[str, Any], field_path: str) -> Any:
    """
    Extract nested field value using dot notation (e.g., 'extension.id').
    
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


def get_nested_field(record: Dict[str, Any], field_path: str) -> Any:
    """
    Get a nested field value using dot notation with array support.
    
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


def get_nested_field_with_multi_lookup(record: Dict[str, Any], field_path: str) -> List[Any]:
    """
    Get nested field values supporting multi-lookup for array patterns.
    
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
            array_value = get_nested_field(record, base_path)
            
            if isinstance(array_value, list):
                results = []
                for item in array_value:
                    if remaining_path:
                        # Navigate further into each array item
                        item_value = get_nested_field(item, remaining_path)
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
            value = get_nested_field(record, field_path)
            return [value] if value is not None else []
            
    except Exception as e:
        logger.error(f"Error in multi-lookup for field path '{field_path}': {str(e)}")
        return []


def set_nested_value(record: Dict[str, Any], field_path: str, value: Any) -> None:
    """
    Set a nested field value in a record dictionary.
    
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


def apply_minimum_length_transformation(value: Any, config: Dict[str, Any]) -> str:
    """
    Apply minimum length transformation with padding.
    
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


def apply_custom_extension_format(value: Any, config: Dict[str, Any]) -> str:
    """
    Apply custom extension format transformation for Zoom compatibility.
    
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


def validate_ar_name_length(ar_name: str, max_length: int = 30) -> Dict[str, Any]:
    """
    Validate that an AR name meets Zoom's length requirements.
    
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


def map_user_type_to_zoom(rc_user_type: str) -> int:
    """
    Map RingCentral user type to Zoom user type integer.
    
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


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Validate that a dictionary contains all required fields.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Validation result with status and missing fields
    """
    validation_result = {
        'valid': True,
        'missing_fields': []
    }
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            validation_result['valid'] = False
            validation_result['missing_fields'].append(field)
    
    return validation_result


def apply_validation_transformation(data: Dict[str, Any], 
                                   rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a set of validation rules to a data dictionary.
    
    Args:
        data: Dictionary to validate and transform
        rules: Validation and transformation rules
        
    Returns:
        Transformed data dictionary
    """
    result = data.copy()
    
    # Apply transformations
    transformations = rules.get('transformations', {})
    for field, transform_rule in transformations.items():
        if field in result:
            transform_type = transform_rule.get('type')
            
            if transform_type == 'minimum_length':
                result[field] = apply_minimum_length_transformation(result[field], transform_rule)
            
            elif transform_type == 'custom_extension_format':
                result[field] = apply_custom_extension_format(result[field], transform_rule)
    
    # Apply validations
    validations = rules.get('validations', {})
    validation_results = {}
    
    for field, validation_rule in validations.items():
        if field in result:
            validation_type = validation_rule.get('type')
            
            if validation_type == 'max_length':
                max_length = validation_rule.get('max_length', 255)
                value = str(result[field])
                
                if len(value) > max_length:
                    # Truncate if configured to do so
                    if validation_rule.get('truncate', False):
                        result[field] = value[:max_length]
                        validation_results[field] = {
                            'valid': True,
                            'truncated': True,
                            'original_length': len(value),
                            'truncated_to': max_length
                        }
                    else:
                        validation_results[field] = {
                            'valid': False,
                            'reason': f'Value exceeds maximum length of {max_length} characters',
                            'length': len(value),
                            'max_length': max_length
                        }
    
    return {
        'data': result,
        'validation_results': validation_results
    }


def replace_template_placeholders(template: str, record: Dict[str, Any]) -> str:
    """
    Replace template placeholders with values from record.
    
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
            value = get_nested_field(record, field_path)

            if value is not None:
                result = result.replace(f"{{{field_path}}}", str(value))
            else:
                result = result.replace(f"{{{field_path}}}", "")

        return result

    except Exception as e:
        logger.error(f"Error replacing template placeholders: {str(e)}")
        return template