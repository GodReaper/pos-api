from typing import Optional, Dict, Any
import json
import redis.asyncio as redis
from app.core.config import settings

# Redis client
redis_client: redis.Redis = None


async def connect_redis():
    """Create Redis connection"""
    global redis_client
    try:
        if settings.REDIS_HOST and settings.REDIS_PORT:
            # ✅ PROD / Redis.io: prefer host/port
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USERNAME,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                ssl=settings.REDIS_SSL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        elif settings.REDIS_URL:
            # ✅ Docker / dev: URL-style
            redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        else:
            print("Warning: No Redis configuration found")
            redis_client = None
            return

        # Test connection
        await redis_client.ping()
        print("Redis connection established successfully")
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")
        redis_client = None

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()


async def ping_redis() -> bool:
    """Ping Redis to check connection"""
    try:
        if redis_client is None:
            return False
        await redis_client.ping()
        return True
    except Exception:
        return False


async def acquire_lock(key: str, ttl: int = 2) -> bool:
    """
    Acquire a distributed lock with TTL (time-to-live) in seconds.
    Returns True if lock was acquired, False if already locked.
    """
    if redis_client is None:
        # If Redis is not available, allow operation (graceful degradation)
        return True
    
    try:
        # Try to set the key with NX (only if not exists) and EX (expiration)
        result = await redis_client.set(f"lock:{key}", "1", nx=True, ex=ttl)
        return result is True
    except Exception:
        # On error, allow operation (graceful degradation)
        return True
    

async def release_lock(key: str):
    """Release a distributed lock"""
    if redis_client is None:
        return
    
    try:
        await redis_client.delete(f"lock:{key}")
    except Exception:
        pass
    

async def get_cache(key: str) -> Optional[str]:
    """Get a value from cache"""
    if redis_client is None:
        return None
    
    try:
        return await redis_client.get(f"cache:{key}")
    except Exception:
        return None
    

async def set_cache(key: str, value: str, ttl: int = 2):
    """Set a value in cache with TTL in seconds"""
    if redis_client is None:
        return
    
    try:
        await redis_client.set(f"cache:{key}", value, ex=ttl)
    except Exception:
        pass
    

async def delete_cache(key: str):
    """Delete a value from cache"""
    if redis_client is None:
        return
    
    try:
        await redis_client.delete(f"cache:{key}")
    except Exception:
        pass


async def publish_event(channel: str, payload: Dict[str, Any]) -> None:
    """Publish a small JSON event to a Redis pub/sub channel."""
    if redis_client is None:
        return

    try:
        message = json.dumps(payload)
        await redis_client.publish(channel, message)
    except Exception:
        # Best-effort: failures should not break business flow
        pass
