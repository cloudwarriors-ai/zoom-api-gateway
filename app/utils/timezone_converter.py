"""
Timezone Converter Utilities for Zoom Platform Microservice

This module contains timezone conversion utilities extracted from the original
ZoomTransformerHelper class. It provides standardized methods for converting
between different timezone formats used across platforms.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# RingCentral to IANA timezone mappings
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

# RingCentral timezone ID to IANA mapping
RC_ID_TO_IANA_MAPPING = {
    '58': 'America/New_York',    # Eastern
    '59': 'America/Chicago',     # Central
    '60': 'America/Denver',      # Mountain
    '61': 'America/Los_Angeles', # Pacific
    '62': 'America/Phoenix',     # Arizona
    '63': 'America/Anchorage',   # Alaska
    '64': 'Pacific/Honolulu'     # Hawaii
}

# Common name to IANA mapping
COMMON_NAME_TO_IANA_MAPPING = {
    'Eastern Time': 'America/New_York',
    'Central Time': 'America/Chicago',
    'Mountain Time': 'America/Denver', 
    'Pacific Time': 'America/Los_Angeles',
    'Alaska Time': 'America/Anchorage',
    'Hawaii Time': 'Pacific/Honolulu'
}

# IANA to RingCentral timezone ID mapping (reverse of RC_ID_TO_IANA_MAPPING)
IANA_TO_RC_ID_MAPPING = {
    'America/New_York': '58',    # Eastern
    'America/Chicago': '59',     # Central
    'America/Denver': '60',      # Mountain
    'America/Los_Angeles': '61', # Pacific
    'America/Phoenix': '62',     # Arizona
    'America/Anchorage': '63',   # Alaska
    'Pacific/Honolulu': '64'     # Hawaii
}


def convert_to_iana_timezone(rc_timezone: str) -> str:
    """
    Convert RingCentral timezone format to IANA timezone format.
    
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
    if rc_timezone in RC_TO_IANA_MAPPING:
        iana_timezone = RC_TO_IANA_MAPPING[rc_timezone]
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


def transform_timezone_to_iana(timezone_data: Dict[str, Any]) -> Optional[str]:
    """
    Transform timezone data object to IANA format.
    
    This handles complex timezone data objects from various platforms.
    
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
                return RC_ID_TO_IANA_MAPPING.get(str(timezone_data['id']))
                
            if 'name' in timezone_data:
                # Handle timezone name to IANA conversion
                return COMMON_NAME_TO_IANA_MAPPING.get(timezone_data['name'])
        
        elif isinstance(timezone_data, str):
            # Handle direct string timezone values
            return timezone_data if timezone_data.startswith('America/') or timezone_data.startswith('Pacific/') else None
            
        return None
        
    except Exception as e:
        logger.error(f"Error converting timezone to IANA: {str(e)}")
        return None


def transform_regional_settings(regional_settings: Dict[str, Any]) -> Dict[str, Any]:
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
        iana_timezone = transform_timezone_to_iana(timezone)
        
        return {
            'timezone': iana_timezone
        }
        
    except Exception as e:
        logger.error(f"Error transforming regional settings: {str(e)}")
        return {}


def convert_timezone_to_ringcentral_id(timezone_str: str) -> str:
    """
    Convert IANA timezone string to RingCentral numeric timezone ID.
    
    Args:
        timezone_str: IANA timezone string to convert
        
    Returns:
        RingCentral timezone ID string
    """
    try:
        # Try exact match first
        if timezone_str in IANA_TO_RC_ID_MAPPING:
            return IANA_TO_RC_ID_MAPPING[timezone_str]
        
        # Fallback to Eastern timezone
        logger.warning(f"Unknown timezone '{timezone_str}', using fallback Eastern timezone")
        return '58'  # Eastern
        
    except Exception as e:
        logger.error(f"Error converting timezone {timezone_str} to RingCentral ID: {str(e)}")
        return '58'  # Default fallback


def apply_timezone_conversion(record: Dict[str, Any], field_name: str) -> str:
    """
    Apply timezone conversion transformation to a field in a record.
    
    Args:
        record: The record containing source data
        field_name: The field name to extract and convert
        
    Returns:
        Converted timezone string
    """
    from .zoom_transformer_ported import ZoomTransformerHelper
    
    timezone_value = ZoomTransformerHelper.get_nested_field(record, field_name)
    if timezone_value:
        return convert_to_iana_timezone(timezone_value)
    return timezone_value