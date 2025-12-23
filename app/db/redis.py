import redis.asyncio as redis
from app.core.config import settings

# Redis client
redis_client: redis.Redis = None


async def connect_redis():
    """Create Redis connection"""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            ssl=settings.REDIS_SSL,
            decode_responses=True,
            socket_connect_timeout=5
        )
        # Test connection immediately
        await redis_client.ping()
        print("Redis connection established successfully")
    except Exception as e:
        # Connection failed, but don't raise - let health checks handle it
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

