#!/usr/bin/env python3

import redis
import os
from dotenv import load_dotenv

load_dotenv()


def get_redis_client():
    """Get Redis client connection."""
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'tesseract-redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )

def get_session_data(session_id: str):
    """
    Get session data from Redis.
    
    Args:
        session_id: Session UUID
    
    Returns:
        Dictionary containing session data or None if not found
    """
    import json
    
    client = get_redis_client()
    session_key = f"session:{session_id}"
    
    try:
        session_data = client.hgetall(session_key)
        if not session_data:
            return None
        
        # Parse JSON fields
        if "provider_tokens" in session_data:
            session_data["provider_tokens"] = json.loads(session_data["provider_tokens"])
        if "system_creds" in session_data:
            session_data["system_creds"] = json.loads(session_data["system_creds"])
        
        return session_data
    except Exception as e:
        print(f"Error getting session data: {e}")
        return None
