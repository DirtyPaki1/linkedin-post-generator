from cachetools import TTLCache
from functools import wraps
import hashlib
import json
from typing import Any, Callable
from config import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# In-memory cache
_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_seconds)

def cached(ttl: int = None):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not settings.enable_caching:
                return func(*args, **kwargs)
            
            # Create cache key
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(json.dumps(key_parts).encode()).hexdigest()
            
            # Check cache
            if cache_key in _cache:
                logger.debug(f"Cache hit for {func.__name__}")
                return _cache[cache_key]
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_ttl = ttl or settings.cache_ttl_seconds
            _cache[cache_key] = result
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator

def clear_cache():
    """Clear all cached data."""
    _cache.clear()
    logger.info("Cache cleared")

def get_cache_stats():
    """Get cache statistics."""
    return {
        'size': len(_cache),
        'maxsize': _cache.maxsize,
        'ttl': _cache.ttl
    }

class RedisCache:
    """Redis cache implementation (optional)."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        
        try:
            import redis
            if settings.redis_url:
                self.redis_client = redis.from_url(settings.redis_url)
                self.enabled = True
                logger.info("Redis cache enabled")
        except ImportError:
            logger.warning("Redis not available, using in-memory cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str):
        if not self.enabled:
            return None
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        if not self.enabled:
            return
        try:
            ttl = ttl or settings.cache_ttl_seconds
            self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete(self, key: str):
        if not self.enabled:
            return
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

# Global cache instance
redis_cache = RedisCache()