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
