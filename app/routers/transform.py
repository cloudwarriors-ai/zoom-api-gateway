"""
Transform Router - Core transformation logic for the microservice

This router handles transformation requests from the main ETL system.
It provides the actual transformation functionality that will be called
when the main system has integration_mode='microservice'.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.database.session import get_db

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class TransformRequest(BaseModel):
    """Request model for transformation."""
    job_id: int
    job_type: int  # Job type ID (33, 39, 45, 77, 78)
    source_platform_id: int
    ssot_schema_id: int
    data: List[Dict[str, Any]]  # Raw extracted data to transform


class TransformResponse(BaseModel):
    """Response model for transformation."""
    success: bool
    transformed_data: List[Dict[str, Any]]
    record_count: int
    job_type: int
    transformation_type: str
    error_message: Optional[str] = None


class ZoomTransformerService:
    """
    Core transformation service that replicates the logic from zoom_transformer_helper.py
    
    This service handles the actual transformation logic for converting data
    from various source formats to Zoom-compatible formats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def transform_data(self, job_type: int, data: List[Dict[str, Any]], 
                      ssot_schema_id: int) -> List[Dict[str, Any]]:
        """
        Main transformation method that routes to specific transformers based on job type.
        
        Args:
            job_type: The job type ID (33=Sites, 39=Users, 45=Call Queues, 77=ARs, 78=IVR)
            data: List of extracted records to transform
            ssot_schema_id: Schema ID for transformation rules
            
        Returns:
            List of transformed records in Zoom format
        """
        self.logger.info(f"Transforming {len(data)} records for job type {job_type}")
        
        # Route to specific transformer based on job type
        if job_type == 33:  # Sites
            return self._transform_sites(data, ssot_schema_id)
        elif job_type == 39:  # Users
            return self._transform_users(data, ssot_schema_id)
        elif job_type == 45:  # Call Queues
            return self._transform_call_queues(data, ssot_schema_id)
        elif job_type == 77:  # Auto Receptionists
            return self._transform_auto_receptionists(data, ssot_schema_id)
        elif job_type == 78:  # IVR
            return self._transform_ivr(data, ssot_schema_id)
        else:
            raise ValueError(f"Unsupported job type: {job_type}")
    
    def _transform_sites(self, data: List[Dict[str, Any]], ssot_schema_id: int) -> List[Dict[str, Any]]:
        """Transform site data (Job Type 33)."""
        self.logger.info(f"Transforming {len(data)} sites")
        transformed = []
        
        for site_record in data:
            # Extract the site data from the record
            site_data = site_record.get('data', {})
            
            # Transform emergency address (port logic from zoom_transformer_helper.py)
            transformed_site = self._transform_emergency_address(site_data)
            
            # Add any additional site-specific transformations
            transformed_site = self._apply_site_transformations(transformed_site, site_record)
            
            transformed.append({
                'id': site_record.get('id'),
                'source_id': site_record.get('source_id'),
                'data': transformed_site
            })
        
        self.logger.info(f"Successfully transformed {len(transformed)} sites")
        return transformed
    
    def _transform_users(self, data: List[Dict[str, Any]], ssot_schema_id: int) -> List[Dict[str, Any]]:
        """Transform user data (Job Type 39)."""
        self.logger.info(f"Transforming {len(data)} users")
        transformed = []
        
        for user_record in data:
            # Extract the user data from the record
            user_data = user_record.get('data', {})
            
            # Transform user data (port logic from zoom_transformer_helper.py)
            transformed_user = self._transform_user_data(user_data)
            
            transformed.append({
                'id': user_record.get('id'),
                'source_id': user_record.get('source_id'),
                'data': transformed_user
            })
        
        self.logger.info(f"Successfully transformed {len(transformed)} users")
        return transformed
    
    def _transform_call_queues(self, data: List[Dict[str, Any]], ssot_schema_id: int) -> List[Dict[str, Any]]:
        """Transform call queue data (Job Type 45)."""
        self.logger.info(f"Transforming {len(data)} call queues")
        transformed = []
        
        for queue_record in data:
            queue_data = queue_record.get('data', {})
            
            # Transform business hours (port logic from zoom_transformer_helper.py)
            transformed_queue = self._transform_business_hours_data(queue_data)
            
            transformed.append({
                'id': queue_record.get('id'),
                'source_id': queue_record.get('source_id'),
                'data': transformed_queue
            })
        
        self.logger.info(f"Successfully transformed {len(transformed)} call queues")
        return transformed
    
    def _transform_auto_receptionists(self, data: List[Dict[str, Any]], ssot_schema_id: int) -> List[Dict[str, Any]]:
        """Transform auto receptionist data (Job Type 77)."""
        self.logger.info(f"Transforming {len(data)} auto receptionists")
        transformed = []
        
        for ar_record in data:
            ar_data = ar_record.get('data', {})
            
            # Apply basic transformations (expand as needed)
            transformed_ar = self._transform_ar_data(ar_data)
            
            transformed.append({
                'id': ar_record.get('id'),
                'source_id': ar_record.get('source_id'),
                'data': transformed_ar
            })
        
        self.logger.info(f"Successfully transformed {len(transformed)} auto receptionists")
        return transformed
    
    def _transform_ivr(self, data: List[Dict[str, Any]], ssot_schema_id: int) -> List[Dict[str, Any]]:
        """Transform IVR data (Job Type 78)."""
        self.logger.info(f"Transforming {len(data)} IVR records")
        transformed = []
        
        for ivr_record in data:
            ivr_data = ivr_record.get('data', {})
            
            # Transform IVR actions (port logic from zoom_transformer_helper.py)
            transformed_ivr = self._transform_ivr_action(ivr_data)
            
            transformed.append({
                'id': ivr_record.get('id'),
                'source_id': ivr_record.get('source_id'),
                'data': transformed_ivr
            })
        
        self.logger.info(f"Successfully transformed {len(transformed)} IVR records")
        return transformed

    # Core transformation methods (ported from zoom_transformer_helper.py)
    
    def _transform_emergency_address(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform emergency address format (port from zoom_transformer_helper.py).
        
        Converts businessAddress format to default_emergency_address format.
        """
        transformed = dict(site_data)  # Start with copy of original
        
        if 'businessAddress' in site_data:
            business_addr = site_data['businessAddress']
            
            # Transform to Zoom emergency address format
            emergency_address = {
                'address_line1': business_addr.get('street', ''),
                'city': business_addr.get('city', ''),
                'state': business_addr.get('state', ''),
                'zip': business_addr.get('zip', ''),
                'country': self._convert_country_code(business_addr.get('country', ''))
            }
            
            # Add address_line2 if available
            if business_addr.get('street2'):
                emergency_address['address_line2'] = business_addr.get('street2')
            
            transformed['default_emergency_address'] = emergency_address
            
            # Remove original businessAddress
            del transformed['businessAddress']
            
        # Generate site code if name is available
        if 'name' in site_data:
            transformed['site_code'] = self._generate_site_code(site_data['name'])
        
        return transformed
    
    def _transform_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform user data format (port from zoom_transformer_helper.py).
        
        Converts contact.* fields to user_info.* format and maps user types.
        """
        transformed = dict(user_data)  # Start with copy
        
        # Transform contact fields to user_info
        if 'contact' in user_data:
            contact = user_data['contact']
            
            user_info = {
                'first_name': contact.get('firstName', ''),
                'last_name': contact.get('lastName', ''),
                'email': contact.get('email', ''),
                'phone_number': contact.get('businessPhone', '')
            }
            
            transformed['user_info'] = user_info
            
            # Remove original contact
            del transformed['contact']
        
        # Map user type (String to Integer)
        if 'type' in user_data:
            user_type_str = user_data['type']
            transformed['user_type'] = self._map_user_type(user_type_str)
        
        # Convert timezone format
        if 'timezone' in user_data:
            transformed['timezone'] = self._convert_timezone(user_data['timezone'])
        
        return transformed
    
    def _transform_business_hours_data(self, queue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform business hours format (port from zoom_transformer_helper.py).
        
        Converts weeklyRanges to custom_hours_settings format.
        """
        transformed = dict(queue_data)
        
        # Transform business hours if present
        if 'business_hours' in queue_data and 'schedule' in queue_data['business_hours']:
            schedule = queue_data['business_hours']['schedule']
            
            if 'weeklyRanges' in schedule:
                weekly_ranges = schedule['weeklyRanges']
                
                # Convert to custom_hours_settings format
                custom_hours = {
                    'type': 'business_hours',
                    'settings': self._convert_weekly_ranges(weekly_ranges)
                }
                
                transformed['custom_hours_settings'] = custom_hours
                
                # Optionally remove original format
                # del transformed['business_hours']
        
        return transformed
    
    def _transform_ar_data(self, ar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform auto receptionist data."""
        transformed = dict(ar_data)
        
        # Add any AR-specific transformations here
        # For now, just pass through with basic cleaning
        
        return transformed
    
    def _transform_ivr_action(self, ivr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform IVR action data (port from zoom_transformer_helper.py).
        
        Converts key mappings and action codes.
        """
        transformed = dict(ivr_data)
        
        # Transform IVR actions if present
        if 'ivr_details' in ivr_data:
            ivr_details = ivr_data['ivr_details']
            
            if isinstance(ivr_details, list) and len(ivr_details) > 0:
                actions = ivr_details[0].get('actions', [])
                
                # Transform each action
                transformed_actions = []
                for action in actions:
                    transformed_action = self._transform_single_ivr_action(action)
                    transformed_actions.append(transformed_action)
                
                # Update the transformed data
                transformed['ivr_details'][0]['actions'] = transformed_actions
        
        return transformed
    
    def _transform_single_ivr_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single IVR action."""
        transformed_action = dict(action)
        
        # Map key inputs (Star->*, Hash->#, NoInput->timeout)
        if 'input' in action:
            key_input = action['input']
            transformed_action['input'] = self._map_ivr_key(key_input)
        
        # Map action strings to Zoom integer codes
        if 'action' in action:
            action_str = action['action']
            transformed_action['action_code'] = self._map_ivr_action_code(action_str)
        
        # Handle target type mapping
        if 'target' in action and action['target']:
            target = action['target']
            transformed_action['target'] = self._map_ivr_target(target)
        
        return transformed_action

    # Utility methods for transformations
    
    def _convert_country_code(self, country: str) -> str:
        """Convert country name to ISO 2-letter code."""
        country_mapping = {
            'United States': 'US',
            'Canada': 'CA',
            'United Kingdom': 'GB',
            'Australia': 'AU',
            # Add more mappings as needed
        }
        return country_mapping.get(country, country)
    
    def _generate_site_code(self, site_name: str) -> str:
        """Generate site code from site name."""
        # Simple transformation: uppercase, replace spaces with underscores, limit length
        code = site_name.upper().replace(' ', '_').replace('-', '_')
        # Remove special characters and limit length
        code = ''.join(c for c in code if c.isalnum() or c == '_')
        return code[:20]  # Limit to 20 characters
    
    def _map_user_type(self, user_type_str: str) -> int:
        """Map user type string to Zoom integer code."""
        type_mapping = {
            'User': 1,
            'Admin': 2,
            'BasicUser': 1,
            'LimitedUser': 3
        }
        return type_mapping.get(user_type_str, 1)  # Default to basic user
    
    def _convert_timezone(self, timezone: str) -> str:
        """Convert timezone to IANA format."""
        # Simple conversion - in real implementation, use proper timezone mapping
        if not timezone:
            return 'UTC'
        
        # Basic conversions
        tz_mapping = {
            'Eastern Standard Time': 'America/New_York',
            'Pacific Standard Time': 'America/Los_Angeles',
            'Central Standard Time': 'America/Chicago',
            'Mountain Standard Time': 'America/Denver'
        }
        
        return tz_mapping.get(timezone, timezone)
    
    def _convert_weekly_ranges(self, weekly_ranges: Dict[str, Any]) -> Dict[str, Any]:
        """Convert weeklyRanges to custom hours settings format."""
        # Simplified conversion - expand as needed
        settings = {}
        
        for day, ranges in weekly_ranges.items():
            if ranges:
                day_settings = []
                for range_info in ranges:
                    day_settings.append({
                        'from': range_info.get('from', '09:00'),
                        'to': range_info.get('to', '17:00')
                    })
                settings[day.lower()] = day_settings
        
        return settings
    
    def _map_ivr_key(self, key_input: str) -> str:
        """Map IVR key inputs."""
        key_mapping = {
            'Star': '*',
            'Hash': '#', 
            'NoInput': 'timeout'
        }
        return key_mapping.get(key_input, key_input)
    
    def _map_ivr_action_code(self, action_str: str) -> int:
        """Map action strings to Zoom action codes."""
        action_mapping = {
            'Connect': 2,
            'Voicemail': 3,
            'Disconnect': 1,
            'Repeat': 4,
            'Transfer': 2
        }
        return action_mapping.get(action_str, 0)
    
    def _map_ivr_target(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """Map IVR target information."""
        mapped_target = dict(target)
        
        # Add target type based on target data
        if 'extension' in target:
            mapped_target['type'] = 'user'
        elif 'queue_id' in target:
            mapped_target['type'] = 'call_queue'
        elif 'voicemail' in target:
            mapped_target['type'] = 'voicemail'
        
        return mapped_target
    
    def _apply_site_transformations(self, site_data: Dict[str, Any], 
                                  original_record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply any additional site-specific transformations."""
        # Add timezone normalization, additional field mapping, etc.
        transformed = dict(site_data)
        
        # Add any site-specific logic here
        if 'timezone' in site_data:
            transformed['timezone'] = self._convert_timezone(site_data['timezone'])
        
        return transformed


# Create service instance
transformer_service = ZoomTransformerService()


@router.post("/transform", response_model=TransformResponse)
async def transform_data(request: TransformRequest, db: Session = Depends(get_db)):
    """
    Main transformation endpoint.
    
    This endpoint receives transformation requests from the main ETL system
    when integration_mode is set to 'microservice'.
    """
    logger.info(f"Received transform request for job {request.job_id}, type {request.job_type}")
    
    try:
        # Perform the transformation
        transformed_data = transformer_service.transform_data(
            job_type=request.job_type,
            data=request.data,
            ssot_schema_id=request.ssot_schema_id
        )
        
        # Determine transformation type for logging
        job_type_names = {33: 'sites', 39: 'users', 45: 'call_queues', 77: 'auto_receptionists', 78: 'ivr'}
        transformation_type = f"ringcentral_to_zoom_{job_type_names.get(request.job_type, 'unknown')}"
        
        logger.info(f"✅ Successfully transformed {len(transformed_data)} records for job {request.job_id}")
        
        return TransformResponse(
            success=True,
            transformed_data=transformed_data,
            record_count=len(transformed_data),
            job_type=request.job_type,
            transformation_type=transformation_type
        )
        
    except Exception as e:
        logger.error(f"❌ Transformation failed for job {request.job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transformation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for the transform service."""
    return {"status": "healthy", "service": "zoom-transformer"}


@router.get("/supported-job-types")
async def get_supported_job_types():
    """Get list of supported job types."""
    return {
        "supported_job_types": [
            {"id": 33, "name": "Sites", "description": "RingCentral to Zoom Sites"},
            {"id": 39, "name": "Users", "description": "RingCentral to Zoom Users"}, 
            {"id": 45, "name": "Call Queues", "description": "RingCentral to Zoom Call Queues"},
            {"id": 77, "name": "Auto Receptionists", "description": "RingCentral to Zoom Auto Receptionists"},
            {"id": 78, "name": "IVR", "description": "RingCentral to Zoom IVR"}
        ]
    }