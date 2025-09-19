"""
Field Mapping Service

This service handles field mappings from SSOT to platform-specific formats.
It provides methods to retrieve, apply, and manage field mappings.
"""
import logging
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import SSOTFieldMapping
from app.core.exceptions import TransformationError

logger = logging.getLogger(__name__)


class FieldMappingService:
    """Service for handling field mappings between SSOT and platform-specific formats."""
    
    @staticmethod
    def get_field_mappings(job_type_id: int, source_platform: str, target_entity: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        Retrieve field mappings for a specific job type, source platform, and target entity.
        
        Args:
            job_type_id: ID of the job type
            source_platform: Source platform (e.g., 'ssot')
            target_entity: Target entity (e.g., 'user', 'site', 'call_queue')
            db: Optional database session
            
        Returns:
            List of field mapping dictionaries
        """
        try:
            if db is None:
                db = next(get_db())
                
            mappings = db.query(SSOTFieldMapping).filter(
                SSOTFieldMapping.job_type_id == job_type_id,
                SSOTFieldMapping.source_platform == source_platform,
                SSOTFieldMapping.target_entity == target_entity
            ).all()
            
            return [
                {
                    "id": mapping.id,
                    "job_type_id": mapping.job_type_id,
                    "source_platform": mapping.source_platform,
                    "target_entity": mapping.target_entity,
                    "ssot_field": mapping.ssot_field,
                    "target_field": mapping.target_field,
                    "transformation_rule": mapping.transformation_rule,
                    "is_required": mapping.is_required,
                    "description": mapping.description
                }
                for mapping in mappings
            ]
        except Exception as e:
            logger.error(f"Error retrieving field mappings: {str(e)}")
            return []
    
    @staticmethod
    def apply_field_mappings(data: Dict[str, Any], mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply field mappings to transform data from SSOT format to target format.
        
        Args:
            data: Source data dictionary (SSOT format)
            mappings: List of field mapping dictionaries
            
        Returns:
            Transformed data dictionary
        """
        if not data or not mappings:
            return data
            
        transformed_data = {}
        missing_required_fields = []
        
        for mapping in mappings:
            ssot_field = mapping["ssot_field"]
            target_field = mapping["target_field"]
            transformation_rule = mapping.get("transformation_rule")
            is_required = mapping.get("is_required", False)
            
            # Check if the SSOT field exists in the data
            if ssot_field in data:
                value = data[ssot_field]
                
                # Apply transformation rule if specified
                if transformation_rule and value is not None:
                    try:
                        # Simple transformation rules
                        if transformation_rule == "uppercase":
                            value = str(value).upper()
                        elif transformation_rule == "lowercase":
                            value = str(value).lower()
                        elif transformation_rule == "capitalize":
                            value = str(value).capitalize()
                        elif transformation_rule == "boolean":
                            value = bool(value)
                        elif transformation_rule == "integer":
                            value = int(value) if value else 0
                        elif transformation_rule == "string":
                            value = str(value) if value is not None else ""
                        # More complex rules can be added here
                    except Exception as e:
                        logger.warning(f"Error applying transformation rule '{transformation_rule}' to field '{ssot_field}': {str(e)}")
                
                # Add the field to the transformed data with the target field name
                transformed_data[target_field] = value
                
            elif is_required:
                missing_required_fields.append(ssot_field)
        
        if missing_required_fields:
            logger.warning(f"Missing required fields in data: {', '.join(missing_required_fields)}")
        
        return transformed_data
    
    @staticmethod
    def apply_nested_field_mappings(data: Dict[str, Any], mappings: List[Dict[str, Any]], 
                                   target_parent: str) -> Dict[str, Any]:
        """
        Apply field mappings to create a nested object in the target data.
        
        Args:
            data: Source data dictionary (SSOT format)
            mappings: List of field mapping dictionaries
            target_parent: Name of the parent object in target format (e.g., 'user_info')
            
        Returns:
            Transformed data dictionary with nested structure
        """
        transformed_data = {}
        nested_data = {}
        
        for mapping in mappings:
            ssot_field = mapping["ssot_field"]
            target_field = mapping["target_field"]
            
            # If the target field is part of the nested structure (contains a dot)
            if "." in target_field:
                parent, child = target_field.split(".", 1)
                
                # Only process if this is the parent we're looking for
                if parent == target_parent and ssot_field in data:
                    value = data[ssot_field]
                    nested_data[child] = value
            elif ssot_field in data:
                # Keep non-nested fields in the root
                transformed_data[target_field] = data[ssot_field]
        
        # Add the nested object to the transformed data
        if nested_data:
            transformed_data[target_parent] = nested_data
            
        return transformed_data
    
    @staticmethod
    def create_or_update_field_mapping(mapping_data: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Create or update a field mapping.
        
        Args:
            mapping_data: Field mapping data
            db: Optional database session
            
        Returns:
            Created or updated field mapping
        """
        try:
            if db is None:
                db = next(get_db())
            
            # Check if mapping exists
            existing = None
            if "id" in mapping_data:
                existing = db.query(SSOTFieldMapping).filter(SSOTFieldMapping.id == mapping_data["id"]).first()
                
            if existing:
                # Update existing mapping
                for key, value in mapping_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                db.commit()
                logger.info(f"Updated field mapping {existing.id}")
                result = {
                    "id": existing.id,
                    "action": "updated"
                }
            else:
                # Create new mapping
                new_mapping = SSOTFieldMapping(**mapping_data)
                db.add(new_mapping)
                db.commit()
                db.refresh(new_mapping)
                logger.info(f"Created new field mapping {new_mapping.id}")
                result = {
                    "id": new_mapping.id,
                    "action": "created"
                }
                
            return result
        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Error creating/updating field mapping: {str(e)}")
            raise TransformationError(f"Failed to create/update field mapping: {str(e)}")
    
    @staticmethod
    def delete_field_mapping(mapping_id: int, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Delete a field mapping.
        
        Args:
            mapping_id: ID of the field mapping to delete
            db: Optional database session
            
        Returns:
            Result of the deletion operation
        """
        try:
            if db is None:
                db = next(get_db())
                
            mapping = db.query(SSOTFieldMapping).filter(SSOTFieldMapping.id == mapping_id).first()
            if mapping:
                db.delete(mapping)
                db.commit()
                logger.info(f"Deleted field mapping {mapping_id}")
                return {"id": mapping_id, "action": "deleted"}
            else:
                logger.warning(f"Field mapping {mapping_id} not found for deletion")
                return {"id": mapping_id, "action": "not_found"}
        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Error deleting field mapping: {str(e)}")
            raise TransformationError(f"Failed to delete field mapping: {str(e)}")
    
    @staticmethod
    def bulk_create_field_mappings(mappings_data: List[Dict[str, Any]], db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Create multiple field mappings in bulk.
        
        Args:
            mappings_data: List of field mapping data dictionaries
            db: Optional database session
            
        Returns:
            Result of the bulk operation
        """
        if db is None:
            db = next(get_db())
            
        created = 0
        updated = 0
        failed = 0
        
        try:
            for mapping_data in mappings_data:
                try:
                    result = FieldMappingService.create_or_update_field_mapping(mapping_data, db)
                    if result["action"] == "created":
                        created += 1
                    elif result["action"] == "updated":
                        updated += 1
                except Exception:
                    failed += 1
                    # Continue with next mapping
            
            return {
                "created": created,
                "updated": updated,
                "failed": failed,
                "total": len(mappings_data)
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error in bulk field mapping creation: {str(e)}")
            raise TransformationError(f"Failed to create field mappings in bulk: {str(e)}")