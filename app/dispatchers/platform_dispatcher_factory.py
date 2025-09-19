"""
Platform Dispatcher Factory

This factory creates appropriate dispatchers based on source and target platforms.
It provides a centralized way to route transformation requests to platform-specific
dispatchers while keeping the main MCP router platform-agnostic.
"""
import logging
from typing import Dict, Any, Optional, Type
from app.core.exceptions import TransformationError
from app.dispatchers.ringcentral_to_zoom_dispatcher import RingCentralToZoomDispatcher
from app.dispatchers.ssot_to_zoom_dispatcher import SSOTToZoomDispatcher
from app.dispatchers.dialpad_to_zoom_dispatcher import DialpadToZoomDispatcher

logger = logging.getLogger(__name__)


class PlatformDispatcherFactory:
    """Factory for creating platform-specific transformation dispatchers."""
    
    # Registry of available dispatchers
    _dispatcher_registry = {
        ("ringcentral", "zoom"): RingCentralToZoomDispatcher,
        ("ssot", "zoom"): SSOTToZoomDispatcher,
        ("dialpad", "zoom"): DialpadToZoomDispatcher,
        # Future dispatchers can be added here:
        # ("zoom", "ringcentral"): ZoomToRingCentralDispatcher,
    }
    
    # Cache for dispatcher instances
    _dispatcher_cache = {}
    
    @classmethod
    def get_dispatcher(cls, source_platform: str, target_platform: str):
        """
        Get a dispatcher instance for the given source and target platforms.
        
        Args:
            source_platform: Source platform name (e.g., 'ringcentral')
            target_platform: Target platform name (e.g., 'zoom')
            
        Returns:
            Dispatcher instance
            
        Raises:
            TransformationError: If no dispatcher is available for the platform combination
        """
        platform_key = (source_platform.lower(), target_platform.lower())
        
        # Check if we have a cached instance
        if platform_key in cls._dispatcher_cache:
            logger.debug(f"Using cached dispatcher for {source_platform} -> {target_platform}")
            return cls._dispatcher_cache[platform_key]
        
        # Check if we have a dispatcher for this platform combination
        if platform_key not in cls._dispatcher_registry:
            available_combinations = [
                f"{src} -> {tgt}" for src, tgt in cls._dispatcher_registry.keys()
            ]
            raise TransformationError(
                f"No dispatcher available for {source_platform} -> {target_platform}. "
                f"Available combinations: {', '.join(available_combinations)}"
            )
        
        # Create and cache the dispatcher instance
        dispatcher_class = cls._dispatcher_registry[platform_key]
        try:
            dispatcher_instance = dispatcher_class()
            cls._dispatcher_cache[platform_key] = dispatcher_instance
            logger.info(f"Created and cached dispatcher for {source_platform} -> {target_platform}")
            return dispatcher_instance
            
        except Exception as e:
            logger.error(f"Failed to create dispatcher for {source_platform} -> {target_platform}: {str(e)}")
            raise TransformationError(f"Dispatcher creation failed: {str(e)}")
    
    @classmethod
    def get_supported_platforms(cls) -> Dict[str, list]:
        """
        Get all supported platform combinations.
        
        Returns:
            Dictionary with source platforms as keys and lists of target platforms as values
        """
        supported = {}
        for source, target in cls._dispatcher_registry.keys():
            if source not in supported:
                supported[source] = []
            supported[source].append(target)
        return supported
    
    @classmethod
    def supports_platform_combination(cls, source_platform: str, target_platform: str) -> bool:
        """
        Check if a platform combination is supported.
        
        Args:
            source_platform: Source platform name
            target_platform: Target platform name
            
        Returns:
            True if combination is supported, False otherwise
        """
        platform_key = (source_platform.lower(), target_platform.lower())
        return platform_key in cls._dispatcher_registry
    
    @classmethod
    def register_dispatcher(cls, source_platform: str, target_platform: str, dispatcher_class: Type):
        """
        Register a new dispatcher for a platform combination.
        
        Args:
            source_platform: Source platform name
            target_platform: Target platform name
            dispatcher_class: Dispatcher class to register
        """
        platform_key = (source_platform.lower(), target_platform.lower())
        cls._dispatcher_registry[platform_key] = dispatcher_class
        
        # Clear cache for this platform combination if it exists
        if platform_key in cls._dispatcher_cache:
            del cls._dispatcher_cache[platform_key]
        
        logger.info(f"Registered dispatcher {dispatcher_class.__name__} for {source_platform} -> {target_platform}")
    
    @classmethod
    def clear_cache(cls):
        """Clear the dispatcher cache."""
        cls._dispatcher_cache.clear()
        logger.info("Cleared dispatcher cache")
    
    @classmethod
    def transform_data(cls, source_platform: str, target_platform: str, job_type_code: str, 
                      raw_data: Dict[str, Any], job: Optional[Any] = None) -> Dict[str, Any]:
        """
        Convenience method to transform data using the appropriate dispatcher.
        
        Args:
            source_platform: Source platform name
            target_platform: Target platform name
            job_type_code: Job type code for the transformation
            raw_data: Raw data to transform
            job: Optional job instance for context
            
        Returns:
            Transformed data
        """
        dispatcher = cls.get_dispatcher(source_platform, target_platform)
        return dispatcher.transform(job_type_code, raw_data, job)