# app/transformers/ssot_to_zoom/call_queues_transformer.py

from typing import Dict, List, Any, Optional
from datetime import time
import logging

from ..base_transformer import BaseTransformer

logger = logging.getLogger(__name__)

class SSOTToZoomCallQueuesTransformer(BaseTransformer):
    """
    Transformer for converting SSOT call queue data to Zoom format.
    Handles job_type_code: 'ssot_to_zoom_call_queues'
    """

    # Mapping for weekdays to Zoom's expected format
    WEEKDAY_MAPPING = {
        'monday': 'monday',
        'tuesday': 'tuesday',
        'wednesday': 'wednesday',
        'thursday': 'thursday',
        'friday': 'friday',
        'saturday': 'saturday',
        'sunday': 'sunday'
    }

    def __init__(self):
        super().__init__()
        self.job_type_code = 'ssot_to_zoom_call_queues'

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform SSOT call queue data to Zoom format.

        Args:
            data: Input data containing call queue information

        Returns:
            Transformed data in Zoom format

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Validate input data
            self._validate_input_data(data)

            # Extract call queue data
            call_queues = data.get('call_queues', [])

            transformed_queues = []
            for queue in call_queues:
                transformed_queue = self._transform_single_queue(queue)
                transformed_queues.append(transformed_queue)

            return {
                'call_queues': transformed_queues,
                'metadata': {
                    'job_type_code': self.job_type_code,
                    'transformed_count': len(transformed_queues)
                }
            }

        except Exception as e:
            logger.error(f"Error transforming SSOT call queue data: {str(e)}")
            raise ValueError(f"Transformation failed: {str(e)}")

    def _validate_input_data(self, data: Dict[str, Any]) -> None:
        """Validate the input data structure."""
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        if 'call_queues' not in data:
            raise ValueError("Input data must contain 'call_queues' key")

        if not isinstance(data['call_queues'], list):
            raise ValueError("'call_queues' must be a list")

    def _transform_single_queue(self, queue: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single call queue."""
        # Required fields
        queue_id = queue.get('id')
        if not queue_id:
            raise ValueError("Call queue must have an 'id'")

        name = queue.get('name')
        if not name:
            raise ValueError("Call queue must have a 'name'")

        # Transform business hours if present
        business_hours = self._transform_business_hours(queue.get('business_hours', {}))

        # Transform other fields as needed
        transformed = {
            'id': queue_id,
            'name': name,
            'description': queue.get('description', ''),
            'extension_number': queue.get('extension_number'),
            'business_hours': business_hours,
            'members': queue.get('members', []),
            'settings': queue.get('settings', {})
        }

        return transformed

    def _transform_business_hours(self, business_hours: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform business hours data to Zoom format.
        Ports logic from ZoomTransformerHelper.transform_business_hours_data
        """
        if not business_hours:
            return {}

        transformed_hours = {}

        # Handle schedule type
        schedule_type = business_hours.get('schedule_type', 'custom')
        transformed_hours['schedule_type'] = schedule_type

        if schedule_type == 'custom':
            # Transform custom hours
            weekly_hours = business_hours.get('weekly_hours', {})
            transformed_weekly = {}

            for day, hours in weekly_hours.items():
                if day.lower() in self.WEEKDAY_MAPPING:
                    zoom_day = self.WEEKDAY_MAPPING[day.lower()]
                    transformed_weekly[zoom_day] = self._transform_day_hours(hours)

            transformed_hours['weekly_hours'] = transformed_weekly

        elif schedule_type == '24_7':
            transformed_hours['is_24_7'] = True

        # Handle holidays if present
        holidays = business_hours.get('holidays', [])
        if holidays:
            transformed_hours['holidays'] = self._transform_holidays(holidays)

        return transformed_hours

    def _transform_day_hours(self, day_hours: Dict[str, Any]) -> Dict[str, Any]:
        """Transform hours for a single day."""
        if not day_hours.get('enabled', True):
            return {'enabled': False}

        start_time = day_hours.get('start_time')
        end_time = day_hours.get('end_time')

        if start_time and end_time:
            # Convert to Zoom's expected time format if needed
            return {
                'enabled': True,
                'start_time': self._format_time(start_time),
                'end_time': self._format_time(end_time)
            }

        return {'enabled': False}

    def _transform_holidays(self, holidays: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform holiday data."""
        transformed_holidays = []
        for holiday in holidays:
            transformed_holiday = {
                'name': holiday.get('name', ''),
                'date': holiday.get('date'),
                'start_time': self._format_time(holiday.get('start_time')),
                'end_time': self._format_time(holiday.get('end_time'))
            }
            transformed_holidays.append(transformed_holiday)
        return transformed_holidays

    def _format_time(self, time_str: Optional[str]) -> Optional[str]:
        """Format time string to Zoom's expected format."""
        if not time_str:
            return None

        try:
            # Assuming time_str is in HH:MM format, convert if needed
            # For now, return as-is, but could add parsing logic
            return time_str
        except Exception:
            logger.warning(f"Invalid time format: {time_str}")
            return None
