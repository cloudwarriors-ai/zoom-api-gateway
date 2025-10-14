"""
Zoom API Endpoint Discovery Module

This module discovers and manages Zoom API endpoints by fetching
from Zoom's official OpenAPI specification and providing a queryable interface.
"""

import requests
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Zoom OpenAPI specification URL
ZOOM_OPENAPI_URL = "https://raw.githubusercontent.com/zoom/api/master/openapi.v2.json"
CACHE_FILE = Path("/tmp/zoom_endpoints.json")

# Global cache
_endpoints_cache = None


def fetch_zoom_openapi_spec() -> Optional[Dict]:
    """
    Fetch Zoom's OpenAPI specification from their official GitHub URL.

    Returns:
        Dict containing the OpenAPI spec, or None if fetch fails
    """
    try:
        logger.info(f"Fetching Zoom OpenAPI spec from {ZOOM_OPENAPI_URL}")
        response = requests.get(ZOOM_OPENAPI_URL, timeout=10)
        response.raise_for_status()
        spec = response.json()
        logger.info(f"✅ Successfully fetched Zoom OpenAPI spec")
        return spec
    except Exception as e:
        logger.error(f"❌ Failed to fetch Zoom OpenAPI spec: {e}")
        return None


def parse_openapi_endpoints(spec: Dict) -> Dict:
    """
    Parse endpoints from Zoom's OpenAPI specification.

    Args:
        spec: The OpenAPI specification dictionary

    Returns:
        Dict containing parsed endpoint metadata
    """
    endpoints = []
    tags_set = set()

    paths = spec.get('paths', {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                # Extract tags
                tags = details.get('tags', [])
                for tag in tags:
                    tags_set.add(tag)

                # Build endpoint object
                endpoint = {
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', ''),
                    'description': details.get('description', '').split('\n')[0],  # First line only
                    'operationId': details.get('operationId', ''),
                    'tags': tags,
                    'parameters': [
                        {
                            'name': param.get('name'),
                            'in': param.get('in'),
                            'required': param.get('required', False),
                            'description': param.get('description', ''),
                            'type': param.get('schema', {}).get('type', 'string')
                        }
                        for param in details.get('parameters', [])
                    ],
                    'deprecated': details.get('deprecated', False),
                    'authenticated': True  # Zoom API requires authentication
                }

                # Assign category from first tag or path-based categorization
                if tags:
                    endpoint['category'] = tags[0].replace('_', ' ').title()
                else:
                    # Fallback: derive category from path
                    path_parts = path.strip('/').split('/')
                    if len(path_parts) >= 1:
                        endpoint['category'] = path_parts[0].replace('_', ' ').title()
                    else:
                        endpoint['category'] = 'General'

                endpoints.append(endpoint)

    # Sort tags for categories
    categories = sorted(list(tags_set))

    return {
        'source': ZOOM_OPENAPI_URL,
        'last_updated': datetime.now().isoformat(),
        'total_endpoints': len(endpoints),
        'categories': categories,
        'endpoints': endpoints
    }


def load_cached_endpoints() -> Optional[Dict]:
    """
    Load endpoints from cache file.

    Returns:
        Dict containing cached endpoint data, or None if not available
    """
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"✅ Loaded {data.get('total_endpoints', 0)} endpoints from cache")
                return data
    except Exception as e:
        logger.warning(f"Failed to load cache file: {e}")
    return None


def save_endpoints_to_cache(data: Dict):
    """
    Save endpoints to cache file.

    Args:
        data: Endpoint data to cache
    """
    try:
        # Create parent directory if it doesn't exist
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"✅ Cached {data.get('total_endpoints', 0)} endpoints to {CACHE_FILE}")
    except Exception as e:
        logger.warning(f"Failed to write cache file: {e}")


def fetch_zoom_endpoints() -> Dict:
    """
    Fetch Zoom API endpoints from OpenAPI spec or cache.

    Tries to fetch from Zoom's official OpenAPI specification.
    Falls back to cached version if fetch fails.

    Returns:
        Dict containing endpoint metadata and list of endpoints
    """
    global _endpoints_cache

    # Return cached data if already loaded
    if _endpoints_cache:
        return _endpoints_cache

    # Try to fetch from Zoom's OpenAPI spec
    spec = fetch_zoom_openapi_spec()

    if spec:
        # Parse endpoints from spec
        endpoints_data = parse_openapi_endpoints(spec)

        # Save to cache
        save_endpoints_to_cache(endpoints_data)

        # Store in memory cache
        _endpoints_cache = endpoints_data

        logger.info(f"✅ Discovered {endpoints_data['total_endpoints']} Zoom endpoints")
        return endpoints_data

    # Fallback to cached version
    logger.warning("Falling back to cached endpoints")
    cached_data = load_cached_endpoints()

    if cached_data:
        _endpoints_cache = cached_data
        return cached_data

    # No cache available, return empty structure
    logger.error("❌ No endpoints available (fetch failed and no cache)")
    return {
        'source': ZOOM_OPENAPI_URL,
        'last_updated': datetime.now().isoformat(),
        'total_endpoints': 0,
        'categories': [],
        'endpoints': []
    }


def get_endpoint_categories() -> List[str]:
    """
    Get list of available endpoint categories.

    Returns:
        List of category names
    """
    data = fetch_zoom_endpoints()
    return data.get("categories", [])


def get_endpoints_by_category(category: Optional[str] = None, limit: Optional[int] = None) -> Dict:
    """
    Get endpoints filtered by category.

    Args:
        category: Optional category filter
        limit: Optional limit on number of results

    Returns:
        Dict containing filtered endpoints and metadata
    """
    data = fetch_zoom_endpoints()
    endpoints = data.get("endpoints", [])

    if category:
        endpoints = [ep for ep in endpoints if ep.get("category") == category or category in ep.get("tags", [])]

    if limit:
        endpoints = endpoints[:limit]

    return {
        "success": True,
        "source": data.get("source"),
        "total_endpoints": data.get("total_endpoints"),
        "filtered_endpoints": len(endpoints) if category or limit else None,
        "categories": data.get("categories", []),
        "endpoints": endpoints
    }


def initialize_discovery():
    """
    Initialize the discovery module on startup.
    """
    logger.info("Initializing Zoom endpoint discovery...")
    try:
        endpoints = fetch_zoom_endpoints()
        logger.info(f"✅ Zoom discovery initialized: {endpoints['total_endpoints']} endpoints across {len(endpoints['categories'])} categories")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Zoom discovery: {e}")
        return False
