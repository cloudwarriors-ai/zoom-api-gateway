from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import TransformerConfig, JobTypeConfig


class BaseTransformer(ABC):
    """
    Abstract base class for all data transformers.
    
    This class defines the interface for transformers that convert data
    between different formats and systems. Subclasses must implement
    the transform method.
    """
    
    def __init__(self):
        """Initialize the transformer with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.transformation_config = None
        self.job_type_code = None
        self.source_format = None
        self.target_format = None
    
    def get_transformation_config(self, job_type_code: str) -> Dict[str, Any]:
        """
        Retrieve transformation configuration from the database.
        
        Args:
            job_type_code: Job type code for the transformation configuration
            
        Returns:
            Dictionary containing transformation mapping rules and settings
        """
        self.logger.info(f"Retrieving transformation config for job_type_code: {job_type_code}")
        
        try:
            db = next(get_db())
            
            # First, find the job_type_id from the JobTypeConfig table using the code
            job_type = db.query(JobTypeConfig).filter(
                JobTypeConfig.code == job_type_code
            ).first()
            
            if not job_type:
                self.logger.warning(f"No JobType found for code: {job_type_code}")
                self.transformation_config = {}
                return self.transformation_config
            
            # Now find the transformation config using the job_type_id
            config = db.query(TransformerConfig).filter(
                TransformerConfig.job_type_id == job_type.id
            ).first()
            
            if config:
                # Parse YAML transformation config
                import yaml
                try:
                    parsed_config = yaml.safe_load(config.transformation_config)
                    self.transformation_config = parsed_config or {}
                    self.logger.info(f"Found and parsed transformation config for {job_type_code} (job_type_id: {job_type.id})")
                    return self.transformation_config
                except yaml.YAMLError as ye:
                    self.logger.error(f"Error parsing YAML config for {job_type_code}: {str(ye)}")
                    self.transformation_config = {}
                    return self.transformation_config
            else:
                self.logger.warning(f"No transformation config found for {job_type_code} (job_type_id: {job_type.id})")
                self.transformation_config = {}
                return self.transformation_config
        except Exception as e:
            self.logger.error(f"Error retrieving transformation config: {str(e)}")
            self.transformation_config = {}
            return self.transformation_config
    
    def get_ssot_schema(self, job_type_code: str) -> Dict[str, Any]:
        """
        Retrieve SSOT schema from the database.
        
        Args:
            job_type_code: Job type code for the SSOT schema
            
        Returns:
            Dictionary containing SSOT schema
        """
        self.logger.info(f"Retrieving SSOT schema for job_type_code: {job_type_code}")
        
        try:
            db = next(get_db())
            schema = db.query(TransformerConfig).filter(
                TransformerConfig.job_type_id == job_type_code,
                # Note: TransformerConfig may not have is_active field, adjust as needed
            ).first()
            
            if schema:
                # TransformerConfig doesn't have get_schema_dict() method like SSOTSchema did
                # For raw transformations, we don't need database schemas anyway
                self.logger.info(f"Found transformer config for {job_type_code}: {schema.name}")
                return {"name": schema.name, "transformation_config": schema.transformation_config}
            else:
                self.logger.warning(f"No transformer config found for job_type_code: {job_type_code}")
                return {}
        except Exception as e:
            self.logger.error(f"Error retrieving SSOT schema: {str(e)}")
            return {}
    
    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        Transform the input data to the target format.
        
        Args:
            data: Input data to be transformed
            
        Returns:
            Transformed data in the target format
        """
        pass
    
    def validate_input(self, data: Any) -> bool:
        """
        Validate the input data before transformation.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Default implementation - subclasses should override with specific validation
        return True
    
    def validate_output(self, data: Any) -> bool:
        """
        Validate the output data after transformation.
        
        Args:
            data: Output data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Default implementation - subclasses should override with specific validation
        return True