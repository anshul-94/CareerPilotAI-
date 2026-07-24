"""
CareerPilot AI — Cache Manager
Simple file-based cache for API responses with TTL support.
"""

import os
import json
import time
import hashlib
from typing import Any, Optional


class CacheManager:
    """File-based cache with TTL (Time-To-Live) support."""

    def __init__(self, cache_dir: str = None, default_ttl: int = 3600):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        if cache_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cache_dir = os.path.join(base, "backend", "cache", "data")
        
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_key_hash(self, key: str) -> str:
        """Generate a hash for the cache key."""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_filepath(self, key: str) -> str:
        """Get the file path for a cache key."""
        return os.path.join(self.cache_dir, f"{self._get_key_hash(key)}.json")

    def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value by key.
        
        Returns:
            Cached value or None if not found/expired
        """
        filepath = self._get_filepath(key)
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check TTL
            if time.time() > data.get('expires_at', 0):
                os.remove(filepath)
                return None
            
            return data.get('value')
            
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        filepath = self._get_filepath(key)
        
        data = {
            'key': key,
            'value': value,
            'created_at': time.time(),
            'expires_at': time.time() + ttl
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, default=str)
        except IOError as e:
            print(f"[WARN] Cache write failed: {str(e)}")

    def delete(self, key: str) -> bool:
        """Delete a cached value."""
        filepath = self._get_filepath(key)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    def clear(self) -> int:
        """Clear all cached values. Returns count of removed files."""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count of removed files."""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    if time.time() > data.get('expires_at', 0):
                        os.remove(filepath)
                        count += 1
                except (json.JSONDecodeError, IOError):
                    os.remove(filepath)
                    count += 1
        return count


# Global cache instance
cache = CacheManager()
