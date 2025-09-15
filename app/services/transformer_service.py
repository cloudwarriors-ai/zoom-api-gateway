"""
Transformer Service for the Zoom Platform Microservice.

This module provides a factory service for creating and managing data transformers
that convert data between different platforms and formats.
"""

import logging
from typing import Dict, Any, Type, Optional, List, Union
import importlib
import inspect

from app.transformers.base_transformer import BaseTransformer
from app.core.exceptions import NotFoundException, ValidationException


class TransformerService:
    """
    Service for managing data transformers.
    
    This service implements a factory pattern to create the appropriate transformer
    based on entity type and source/target platforms. It handles discovery, creation,
    and management of transformer instances.
    """
    
    def __init__(self):
        """Initialize the transformer service with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._transformer_registry: Dict[str, Type[BaseTransformer]] = {}
        self._discover_transformers()
    
    def _discover_transformers(self) -> None:
        """
        Discover and register all available transformers.
        
        This method scans the transformer modules and registers all classes
        that inherit from BaseTransformer.
        """
        try:
            # Dynamically discover transformers in the transformers directory
            self.logger.info("Discovering available transformers")
            
            # Raw to Zoom transformers
            self._register_transformers_from_module("app.transformers.raw_to_zoom.ringcentral_to_zoom")
            
            # SSOT to Zoom transformers
            self._register_transformers_from_module("app.transformers.ssot_to_zoom")
            
            # Add other transformer modules as needed
            
            self.logger.info(f"Discovered {len(self._transformer_registry)} transformers")
        except Exception as e:
            self.logger.error(f"Error discovering transformers: {str(e)}")
            # Re-raise as this is a critical initialization step
            raise
    
    def _register_transformers_from_module(self, module_path: str) -> None:
        """
        Register all transformers from a specific module.
        
        Args:
            module_path: The Python path to the module containing transformers
        """
        try:
            module = importlib.import_module(module_path)
            
            for name, obj in inspect.getmembers(module):
                # Check if it's a class that inherits from BaseTransformer
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseTransformer) and 
                    obj != BaseTransformer):
                    
                    # Use the class name as the key in the registry
                    self._transformer_registry[name] = obj
                    self.logger.debug(f"Registered transformer: {name}")
        except ImportError as e:
            self.logger.warning(f"Could not import module {module_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error registering transformers from {module_path}: {str(e)}")
    
    def get_transformer(self, 
                       entity_type: str, 
                       source_platform: str, 
                       target_platform: str) -> BaseTransformer:
        """
        Get the appropriate transformer based on entity type and platforms.
        
        Args:
            entity_type: The type of entity to transform (e.g., 'sites', 'users')
            source_platform: The source platform (e.g., 'ringcentral', 'ssot')
            target_platform: The target platform (e.g., 'zoom')
            
        Returns:
            An instance of the appropriate transformer
            
        Raises:
            NotFoundException: If no suitable transformer is found
            ValidationException: If the parameters are invalid
        """
        if not entity_type or not source_platform or not target_platform:
            self.logger.error("Invalid parameters for get_transformer")
            raise ValidationException(detail="Entity type, source platform, and target platform are required")
        
        # Normalize parameters to lowercase
        entity_type = entity_type.lower()
        source_platform = source_platform.lower()
        target_platform = target_platform.lower()
        
        # Generate expected transformer name based on convention
        # Example: RingcentralToZoomSitesTransformer
        transformer_name = f"{source_platform.capitalize()}To{target_platform.capitalize()}{entity_type.capitalize()}Transformer"
        
        self.logger.debug(f"Looking for transformer: {transformer_name}")
        
        # Look for the transformer in the registry
        transformer_class = self._transformer_registry.get(transformer_name)
        
        if not transformer_class:
            self.logger.error(f"No transformer found for entity_type={entity_type}, "
                              f"source_platform={source_platform}, target_platform={target_platform}")
            raise NotFoundException(
                detail=f"No transformer found for {entity_type} from {source_platform} to {target_platform}"
            )
        
        # Create and return a new instance of the transformer
        transformer = transformer_class()
        self.logger.info(f"Created transformer: {transformer_name}")
        return transformer
    
    def list_available_transformers(self) -> List[Dict[str, str]]:
        """
        List all available transformers.
        
        Returns:
            A list of dictionaries with transformer information
        """
        result = []
        
        for name, transformer_class in self._transformer_registry.items():
            # Extract entity type and platforms from the transformer name
            # This assumes a naming convention like SourceToTargetEntityTransformer
            info = {
                "name": name,
                "class": transformer_class.__name__
            }
            result.append(info)
            
        return result
    
    def transform_data(self, 
                      entity_type: str, 
                      source_platform: str, 
                      target_platform: str, 
                      data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Any:
        """
        Transform data using the appropriate transformer.
        
        Args:
            entity_type: The type of entity to transform
            source_platform: The source platform
            target_platform: The target platform
            data: The data to transform
            
        Returns:
            The transformed data
            
        Raises:
            NotFoundException: If no suitable transformer is found
            ValidationException: If the data validation fails
        """
        try:
            # Get the appropriate transformer
            transformer = self.get_transformer(
                entity_type=entity_type, 
                source_platform=source_platform, 
                target_platform=target_platform
            )
            
            # Validate input data
            if not transformer.validate_input(data):
                self.logger.error(f"Input data validation failed for {entity_type}")
                raise ValidationException(detail=f"Input data validation failed for {entity_type}")
            
            # Transform the data
            self.logger.info(f"Transforming {entity_type} data from {source_platform} to {target_platform}")
            transformed_data = transformer.transform(data)
            
            # Validate output data
            if not transformer.validate_output(transformed_data):
                self.logger.error(f"Output data validation failed for {entity_type}")
                raise ValidationException(detail=f"Output data validation failed for {entity_type}")
            
            return transformed_data
            
        except NotFoundException as e:
            # Re-raise NotFoundException
            raise
        except ValidationException as e:
            # Re-raise ValidationException
            raise
        except Exception as e:
            # Log and convert other exceptions
            self.logger.error(f"Error transforming data: {str(e)}")
            raise ValidationException(detail=f"Error transforming data: {str(e)}")