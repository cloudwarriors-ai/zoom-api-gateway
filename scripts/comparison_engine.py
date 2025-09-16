#!/usr/bin/env python3
"""
Advanced Output Comparison Engine

This module provides sophisticated comparison capabilities for validating
that the microservice produces identical outputs to the existing internal
transformation logic.

Features:
- Field-by-field deep comparison
- Business logic validation
- Tolerance handling for timestamps/UUIDs  
- Smart diff analysis with fix suggestions
- JSON schema validation
- Performance metrics comparison
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass
from deepdiff import DeepDiff
from jsondiff import diff as json_diff
import difflib
from datetime import datetime, timezone
import re
import uuid

logger = logging.getLogger(__name__)

@dataclass
class FieldDifference:
    """Represents a difference in a specific field."""
    field_path: str
    path_a_value: Any
    path_b_value: Any
    difference_type: str
    severity: str  # 'critical', 'warning', 'info'
    fix_suggestion: Optional[str] = None

@dataclass
class ComparisonMetrics:
    """Performance and accuracy metrics for comparison."""
    total_records: int
    identical_records: int
    different_records: int
    field_differences_count: int
    processing_time_ms: float
    accuracy_percentage: float

@dataclass 
class BusinessLogicValidation:
    """Results of business logic validation."""
    field_name: str
    validation_type: str
    passed: bool
    expected_pattern: str
    actual_value: str
    error_message: Optional[str] = None

class TransformationComparisonEngine:
    """Advanced comparison engine for transformation outputs."""
    
    def __init__(self):
        self.tolerance_config = self._get_tolerance_config()
        self.business_validators = self._get_business_validators()
        self.field_patterns = self._get_field_patterns()
    
    def _get_tolerance_config(self) -> Dict[str, Any]:
        """Configuration for fields that should be ignored in comparisons."""
        return {
            # System generated fields to ignore
            "ignore_fields": [
                "id",
                "uuid", 
                "created_at",
                "updated_at",
                "timestamp",
                "modified_at",
                "processed_at"
            ],
            
            # Fields with regex patterns to ignore
            "ignore_patterns": [
                r".*_id$",  # Any field ending with _id
                r".*_uuid$",  # Any field ending with _uuid
                r".*_timestamp$",  # Any field ending with _timestamp
                r"^temp_.*",  # Any field starting with temp_
            ],
            
            # Numerical tolerance for floating point comparisons
            "numerical_tolerance": 0.001,
            
            # String case sensitivity
            "case_sensitive": True,
            
            # Date/time tolerance in seconds
            "datetime_tolerance_seconds": 5
        }
    
    def _get_business_validators(self) -> Dict[str, callable]:
        """Business logic validators for specific transformation types."""
        return {
            "emergency_address": self._validate_emergency_address,
            "timezone_format": self._validate_timezone_format, 
            "phone_number": self._validate_phone_number,
            "user_type_mapping": self._validate_user_type_mapping,
            "ivr_action_mapping": self._validate_ivr_action_mapping,
            "business_hours": self._validate_business_hours,
            "site_code_generation": self._validate_site_code_generation
        }
    
    def _get_field_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Expected patterns for specific fields by job type."""
        return {
            # Job Type 33: Sites
            "sites": {
                "default_emergency_address": {
                    "required_fields": ["address_line1", "city", "state", "zip", "country"],
                    "country_format": r"^[A-Z]{2}$",  # ISO 2-letter country code
                    "zip_format": r"^\d{5}(-\d{4})?$"  # US ZIP code format
                },
                "site_code": {
                    "pattern": r"^[A-Z0-9_]+$",  # Uppercase alphanumeric with underscores
                    "max_length": 20
                }
            },
            
            # Job Type 39: Users  
            "users": {
                "user_info": {
                    "required_fields": ["first_name", "last_name", "email"],
                    "email_format": r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
                },
                "user_type": {
                    "valid_values": [1, 2, 3],  # Zoom user type codes
                    "mapping": {"User": 1, "Admin": 2, "Basic": 3}
                }
            },
            
            # Job Type 45: Call Queues
            "call_queues": {
                "custom_hours_settings": {
                    "required_fields": ["type", "settings"],
                    "type_values": ["business_hours", "24_7", "custom"]
                },
                "queue_members": {
                    "member_type": ["user", "call_queue", "voicemail"] 
                }
            },
            
            # Job Type 77: Auto Receptionists
            "auto_receptionists": {
                "site_association": {
                    "required": True,
                    "field_name": "site_id"
                },
                "phone_extension": {
                    "pattern": r"^\d{3,6}$",  # 3-6 digit extension
                    "required": False
                }
            },
            
            # Job Type 78: IVR
            "ivr": {
                "key_actions": {
                    "valid_keys": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "#", "timeout"],
                    "valid_actions": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # Zoom action codes
                    "key_mappings": {"Star": "*", "Hash": "#", "NoInput": "timeout"}
                },
                "target_types": {
                    "valid_types": ["user", "call_queue", "voicemail", "announcement", "disconnect"]
                }
            }
        }
    
    def should_ignore_field(self, field_path: str, value: Any) -> bool:
        """Determine if a field should be ignored in comparison."""
        # Check exact field names
        field_name = field_path.split('.')[-1]
        if field_name in self.tolerance_config["ignore_fields"]:
            return True
        
        # Check regex patterns
        for pattern in self.tolerance_config["ignore_patterns"]:
            if re.match(pattern, field_name):
                return True
        
        # Check for UUID values
        if isinstance(value, str) and self._is_uuid(value):
            return True
        
        # Check for timestamp values
        if isinstance(value, str) and self._is_timestamp(value):
            return True
        
        return False
    
    def _is_uuid(self, value: str) -> bool:
        """Check if string is a UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    def _is_timestamp(self, value: str) -> bool:
        """Check if string is a timestamp."""
        timestamp_patterns = [
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO timestamp
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",  # SQL timestamp  
            r"^\d{10}$",  # Unix timestamp
            r"^\d{13}$"   # Unix timestamp in milliseconds
        ]
        
        for pattern in timestamp_patterns:
            if re.match(pattern, str(value)):
                return True
        return False
    
    def compare_records(self, path_a_data: List[Dict], path_b_data: List[Dict], job_type: str) -> Tuple[bool, List[FieldDifference], ComparisonMetrics]:
        """Compare two sets of transformation output records."""
        start_time = datetime.now()
        
        logger.info(f"Comparing {len(path_a_data)} vs {len(path_b_data)} records for job type: {job_type}")
        
        # Normalize data for comparison
        normalized_a = self._normalize_data(path_a_data)
        normalized_b = self._normalize_data(path_b_data)
        
        # Perform deep diff comparison
        diff = DeepDiff(
            normalized_a,
            normalized_b,
            ignore_order=True,
            exclude_paths=self._get_exclude_paths(),
            view='tree'
        )
        
        # Analyze differences
        field_differences = self._analyze_differences(diff, job_type)
        
        # Calculate metrics
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        identical_count = len(path_a_data) - len([d for d in field_differences if d.severity == 'critical'])
        
        metrics = ComparisonMetrics(
            total_records=len(path_a_data),
            identical_records=identical_count,
            different_records=len(path_a_data) - identical_count,
            field_differences_count=len(field_differences),
            processing_time_ms=processing_time,
            accuracy_percentage=(identical_count / len(path_a_data) * 100) if path_a_data else 100.0
        )
        
        # Overall comparison result
        is_identical = len(field_differences) == 0
        
        return is_identical, field_differences, metrics
    
    def _normalize_data(self, data: List[Dict]) -> List[Dict]:
        """Normalize data by sorting and removing ignored fields."""
        normalized = []
        
        for record in data:
            normalized_record = {}
            
            for key, value in record.items():
                if not self.should_ignore_field(key, value):
                    if isinstance(value, dict):
                        # Recursively normalize nested objects
                        normalized_value = self._normalize_dict(value, key)
                        if normalized_value:  # Only add if not empty after normalization
                            normalized_record[key] = normalized_value
                    elif isinstance(value, list):
                        # Handle lists (sort if all elements are comparable)
                        try:
                            normalized_record[key] = sorted(value) if value else value
                        except TypeError:
                            normalized_record[key] = value
                    else:
                        normalized_record[key] = value
            
            normalized.append(normalized_record)
        
        # Sort records by JSON representation for consistent ordering
        return sorted(normalized, key=lambda x: json.dumps(x, sort_keys=True))
    
    def _normalize_dict(self, obj: Dict, parent_key: str = "") -> Dict:
        """Recursively normalize dictionary objects."""
        normalized = {}
        
        for key, value in obj.items():
            field_path = f"{parent_key}.{key}" if parent_key else key
            
            if not self.should_ignore_field(field_path, value):
                if isinstance(value, dict):
                    normalized_value = self._normalize_dict(value, field_path)
                    if normalized_value:
                        normalized[key] = normalized_value
                else:
                    normalized[key] = value
        
        return normalized
    
    def _get_exclude_paths(self) -> List[str]:
        """Get paths to exclude from DeepDiff comparison."""
        exclude_paths = []
        
        # Generate exclude paths for ignored fields
        for field in self.tolerance_config["ignore_fields"]:
            exclude_paths.extend([
                f"root[*]['{field}']",  # Top level field
                f"root[*].{field}",     # Nested field
            ])
        
        return exclude_paths
    
    def _analyze_differences(self, diff: DeepDiff, job_type: str) -> List[FieldDifference]:
        """Analyze DeepDiff results and categorize differences."""
        field_differences = []
        
        # Handle different types of differences
        for diff_type, changes in diff.items():
            if diff_type == 'values_changed':
                for path, change in changes.items():
                    field_diff = FieldDifference(
                        field_path=str(path),
                        path_a_value=change['old_value'],
                        path_b_value=change['new_value'],
                        difference_type='value_changed',
                        severity=self._assess_severity(str(path), change['old_value'], change['new_value'], job_type),
                        fix_suggestion=self._generate_fix_suggestion(str(path), change['old_value'], change['new_value'], job_type)
                    )
                    field_differences.append(field_diff)
            
            elif diff_type == 'dictionary_item_added':
                for path, value in changes.items():
                    field_diff = FieldDifference(
                        field_path=str(path),
                        path_a_value=None,
                        path_b_value=value,
                        difference_type='field_added',
                        severity='warning',
                        fix_suggestion=f"Field '{path}' was added in Path B. Verify if this is expected."
                    )
                    field_differences.append(field_diff)
            
            elif diff_type == 'dictionary_item_removed':
                for path, value in changes.items():
                    field_diff = FieldDifference(
                        field_path=str(path),
                        path_a_value=value,
                        path_b_value=None,
                        difference_type='field_removed', 
                        severity='critical',
                        fix_suggestion=f"Field '{path}' was removed in Path B. This may indicate missing transformation logic."
                    )
                    field_differences.append(field_diff)
        
        return field_differences
    
    def _assess_severity(self, field_path: str, old_value: Any, new_value: Any, job_type: str) -> str:
        """Assess the severity of a field difference."""
        # Critical differences that would break functionality
        critical_patterns = [
            r".*email.*",
            r".*phone.*",
            r".*address.*",
            r".*user_type.*",
            r".*action_code.*",
            r".*site_id.*"
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, field_path, re.IGNORECASE):
                return 'critical'
        
        # Warning level differences (formatting, case, etc.)
        if isinstance(old_value, str) and isinstance(new_value, str):
            if old_value.lower() == new_value.lower():
                return 'info'  # Just case difference
        
        # Numerical differences within tolerance
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            if abs(old_value - new_value) <= self.tolerance_config["numerical_tolerance"]:
                return 'info'
        
        return 'warning'
    
    def _generate_fix_suggestion(self, field_path: str, old_value: Any, new_value: Any, job_type: str) -> str:
        """Generate helpful fix suggestions for differences."""
        suggestions = []
        
        # Address field differences
        if 'address' in field_path.lower():
            suggestions.append("Check address normalization logic in microservice transformer")
            suggestions.append("Verify country code conversion (full name vs ISO code)")
        
        # Timezone differences  
        elif 'timezone' in field_path.lower():
            suggestions.append("Verify timezone conversion logic matches zoom_transformer_helper.py")
            suggestions.append("Check for IANA timezone format consistency")
        
        # User type mapping
        elif 'user_type' in field_path.lower():
            suggestions.append("Check user type mapping in microservice matches helper logic")
            suggestions.append(f"Expected: {old_value}, Got: {new_value}")
        
        # IVR action mapping
        elif 'action' in field_path.lower() and job_type == 'ivr':
            suggestions.append("Verify IVR action code mapping in microservice")
            suggestions.append("Check if key mapping (Star->*, Hash->#) is correct")
        
        # Generic suggestions based on value types
        else:
            if isinstance(old_value, str) and isinstance(new_value, str):
                if old_value.lower() == new_value.lower():
                    suggestions.append("Case sensitivity difference - check string handling")
                else:
                    suggestions.append("String value difference - check field mapping logic")
            elif isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                suggestions.append("Numerical difference - check calculation or conversion logic")
            else:
                suggestions.append(f"Data type or value mismatch - check transformation logic for {field_path}")
        
        return " | ".join(suggestions) if suggestions else "Review transformation logic for this field"
    
    def validate_business_logic(self, data: List[Dict], job_type: str) -> List[BusinessLogicValidation]:
        """Validate business logic rules for specific job types."""
        validations = []
        patterns = self.field_patterns.get(job_type.lower(), {})
        
        for record in data:
            for field_group, rules in patterns.items():
                validation = self._validate_field_group(record, field_group, rules, job_type)
                if validation:
                    validations.extend(validation)
        
        return validations
    
    def _validate_field_group(self, record: Dict, field_group: str, rules: Dict, job_type: str) -> List[BusinessLogicValidation]:
        """Validate a group of related fields."""
        validations = []
        
        # Check if the field group exists in the record
        if field_group not in record:
            return validations
        
        field_data = record[field_group]
        
        # Validate required fields
        if 'required_fields' in rules:
            for required_field in rules['required_fields']:
                if required_field not in field_data:
                    validations.append(BusinessLogicValidation(
                        field_name=f"{field_group}.{required_field}",
                        validation_type="required_field",
                        passed=False,
                        expected_pattern="field should be present",
                        actual_value="missing",
                        error_message=f"Required field {required_field} missing from {field_group}"
                    ))
        
        # Validate patterns
        for field_name, pattern in rules.items():
            if field_name.endswith('_format') or field_name.endswith('_pattern'):
                actual_field = field_name.replace('_format', '').replace('_pattern', '')
                if actual_field in field_data:
                    value = str(field_data[actual_field])
                    matches = re.match(pattern, value) if isinstance(pattern, str) else True
                    
                    validations.append(BusinessLogicValidation(
                        field_name=f"{field_group}.{actual_field}",
                        validation_type="pattern_match",
                        passed=bool(matches),
                        expected_pattern=str(pattern),
                        actual_value=value,
                        error_message=None if matches else f"Value '{value}' does not match expected pattern '{pattern}'"
                    ))
        
        return validations
    
    # Business logic validators
    def _validate_emergency_address(self, data: Dict) -> bool:
        """Validate emergency address transformation."""
        if 'default_emergency_address' not in data:
            return False
        
        address = data['default_emergency_address']
        required_fields = ['address_line1', 'city', 'state', 'zip', 'country']
        
        return all(field in address and address[field] for field in required_fields)
    
    def _validate_timezone_format(self, data: Dict) -> bool:
        """Validate timezone is in IANA format."""
        timezone_fields = ['timezone', 'time_zone', 'tz']
        
        for field in timezone_fields:
            if field in data:
                tz_value = data[field]
                # Basic IANA timezone pattern check
                return bool(re.match(r'^[A-Za-z_]+/[A-Za-z_]+$', str(tz_value)))
        
        return True  # No timezone field found, assume valid
    
    def _validate_phone_number(self, data: Dict) -> bool:
        """Validate phone number format."""
        phone_fields = ['phone_number', 'extension', 'direct_number']
        
        for field in phone_fields:
            if field in data and data[field]:
                phone = str(data[field])
                # Basic phone number validation
                return bool(re.match(r'^\+?[\d\s\-\(\)\.]+$', phone))
        
        return True
    
    def _validate_user_type_mapping(self, data: Dict) -> bool:
        """Validate user type mapping is correct."""
        if 'user_type' in data:
            return data['user_type'] in [1, 2, 3]  # Valid Zoom user types
        return True
    
    def _validate_ivr_action_mapping(self, data: Dict) -> bool:
        """Validate IVR action codes are correct."""
        if 'actions' in data:
            for action in data['actions']:
                if 'action_code' in action:
                    # Valid Zoom IVR action codes (0-12)
                    if not (0 <= action['action_code'] <= 12):
                        return False
        return True
    
    def _validate_business_hours(self, data: Dict) -> bool:
        """Validate business hours format."""
        if 'custom_hours_settings' in data:
            hours = data['custom_hours_settings']
            return isinstance(hours, dict) and 'type' in hours
        return True
    
    def _validate_site_code_generation(self, data: Dict) -> bool:
        """Validate site code generation."""
        if 'site_code' in data:
            site_code = str(data['site_code'])
            return bool(re.match(r'^[A-Z0-9_]+$', site_code)) and len(site_code) <= 20
        return True
    
    def generate_comparison_report(self, is_identical: bool, differences: List[FieldDifference], 
                                 metrics: ComparisonMetrics, validations: List[BusinessLogicValidation] = None) -> Dict[str, Any]:
        """Generate comprehensive comparison report."""
        report = {
            "summary": {
                "identical": is_identical,
                "total_records": metrics.total_records,
                "accuracy_percentage": metrics.accuracy_percentage,
                "processing_time_ms": metrics.processing_time_ms,
                "timestamp": datetime.now().isoformat()
            },
            "metrics": {
                "identical_records": metrics.identical_records,
                "different_records": metrics.different_records,
                "field_differences_count": metrics.field_differences_count
            },
            "differences": [
                {
                    "field_path": diff.field_path,
                    "difference_type": diff.difference_type,
                    "severity": diff.severity,
                    "path_a_value": diff.path_a_value,
                    "path_b_value": diff.path_b_value,
                    "fix_suggestion": diff.fix_suggestion
                }
                for diff in differences
            ],
            "severity_breakdown": {
                "critical": len([d for d in differences if d.severity == 'critical']),
                "warning": len([d for d in differences if d.severity == 'warning']), 
                "info": len([d for d in differences if d.severity == 'info'])
            }
        }
        
        if validations:
            report["business_logic_validation"] = [
                {
                    "field_name": v.field_name,
                    "validation_type": v.validation_type,
                    "passed": v.passed,
                    "expected_pattern": v.expected_pattern,
                    "actual_value": v.actual_value,
                    "error_message": v.error_message
                }
                for v in validations
            ]
        
        return report