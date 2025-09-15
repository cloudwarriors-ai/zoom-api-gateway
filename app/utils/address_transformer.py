"""
Address Transformation Utilities for Zoom Platform Microservice

This module contains address transformation utilities extracted from the original
ZoomTransformerHelper class. It provides standardized methods for formatting and
validating addresses across different platforms.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Country name to ISO code mapping
COUNTRY_MAPPING = {
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

# Address field replacements for normalization
ADDRESS_REPLACEMENTS = {
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

# Address field end replacements for normalization
ADDRESS_END_REPLACEMENTS = {
    ' Ct': ' CT',
    ' St': ' ST',
    ' Ave': ' AVE',
    ' Blvd': ' BLVD',
    ' Dr': ' DR',
    ' Ln': ' LN',
    ' Rd': ' RD',
}


def convert_country_to_iso(country_name: str) -> str:
    """
    Convert country name to ISO 3166-1 alpha-2 code.
    
    Args:
        country_name: Country name to convert
        
    Returns:
        ISO country code
    """
    return COUNTRY_MAPPING.get(country_name, country_name)


def normalize_address_field(value: str) -> str:
    """
    Normalize address field casing for API compatibility.
    
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
    for old, new in ADDRESS_REPLACEMENTS.items():
        normalized = normalized.replace(old, new)
    
    # Handle cases at the end of string
    for old, new in ADDRESS_END_REPLACEMENTS.items():
        if normalized.endswith(old):
            normalized = normalized[:-len(old)] + new
    
    return normalized


def transform_emergency_address(business_address: Dict[str, Any]) -> Dict[str, Any]:
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
        country_iso = convert_country_to_iso(country_name) if country_name else ''
        
        transformed_address = {
            'address_line1': business_address.get('street', ''),
            'city': business_address.get('city', ''),
            'state_code': business_address.get('state', ''),
            'zip': business_address.get('zip', ''),
            'country': country_iso
        }
        
        logger.debug(f"Transformed emergency address: {transformed_address}")
        return transformed_address
        
    except Exception as e:
        logger.error(f"Error transforming emergency address: {str(e)}")
        return {}


def apply_address_transformation(record: Dict[str, Any], transform_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply address transformation with fallback logic.
    
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
                    address[target_field] = normalize_address_field(record[source_field])
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
                            address[target_field] = normalize_address_field(record[source_field])
                        else:
                            address[target_field] = record[source_field]
        
        return address
        
    except Exception as e:
        logger.error(f"Error applying address transformation: {str(e)}")
        return {}


def validate_address(address: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
    """
    Validate address dictionary for required fields and proper formatting.
    
    Args:
        address: Address dictionary to validate
        required_fields: List of required field names (default: address_line1, city, state_code, country)
        
    Returns:
        Validation result with status and errors
    """
    if required_fields is None:
        required_fields = ['address_line1', 'city', 'state_code', 'country']
    
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check for required fields
    for field in required_fields:
        if field not in address or not address[field]:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Missing required field: {field}")
    
    # Validate country code format (2-letter ISO)
    if 'country' in address and address['country']:
        country = address['country']
        if len(country) != 2 or not country.isalpha():
            validation_result['warnings'].append(f"Country code '{country}' is not in ISO 3166-1 alpha-2 format")
    
    # Validate ZIP/postal code
    if 'zip' in address and address['zip']:
        zip_code = address['zip']
        country = address.get('country', '')
        
        # US ZIP code validation
        if country == 'US' and (not zip_code.isdigit() or (len(zip_code) != 5 and len(zip_code) != 9)):
            validation_result['warnings'].append(f"ZIP code '{zip_code}' does not match US format (5 or 9 digits)")
    
    return validation_result