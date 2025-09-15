from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional


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
    
    def get_transformation_config(self, config_id: str) -> Dict[str, Any]:
        """
        Retrieve transformation configuration from the database.
        
        Args:
            config_id: Identifier for the transformation configuration
            
        Returns:
            Dictionary containing transformation mapping rules and settings
        """
        # In a real implementation, this would query a database
        # For now, we'll just log the request and return an empty dict
        self.logger.info(f"Retrieving transformation config: {config_id}")
        
        # TODO: Implement actual database query to fetch transformation config
        # Example: from app.models import TransformationConfig
        #          config = TransformationConfig.objects.get(id=config_id)
        #          return config.settings
        
        self.transformation_config = {}
        return self.transformation_config
    
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