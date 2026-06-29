#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import redis
import json
import hashlib
from typing import Optional, Any
import logging
from datetime import datetime
from functools import wraps
from config import CACHE_REDIS_URL, CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestionnaire de cache avec Redis"""
    
    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 86400):
        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self.redis_client = None
        self._memory_cache = {}
        
        if redis_url:
            self._connect()
        else:
            logger.info("Cache Redis desactive, utilisation du cache memoire")
    
    def _connect(self):
        """Connexion Redis simple et compatible"""
        if not self.redis_url:
            return
        
        try:
            # Connexion simple, sans options complexes
            self.redis_client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Test de connexion
            self.redis_client.ping()
            logger.info(f"Redis connecte: {self.redis_url}")
            
        except Exception as e:
            logger.warning(f"Redis indisponible: {e}")
            self.redis_client = None
    
    def _key(self, prefix: str, *args, **kwargs) -> str:
        """Génère une clé unique"""
        parts = [prefix]
        parts.extend(str(a) for a in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key = "|".join(parts)
        return f"gps:{hashlib.md5(key.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur"""
        # Cache mémoire
        if key in self._memory_cache:
            data, ts = self._memory_cache[key]
            if (datetime.now() - ts).seconds < self.ttl:
                return data
            del self._memory_cache[key]
        
        # Cache Redis
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Stocke une valeur"""
        ttl = ttl or self.ttl
        
        # Mémoire
        self._memory_cache[key] = (value, datetime.now())
        
        # Redis
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
            except Exception:
                pass
    
    def delete(self, key: str):
        """Supprime une clé"""
        if key in self._memory_cache:
            del self._memory_cache[key]
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
    
    def clear(self):
        """Vide le cache"""
        self._memory_cache.clear()
        if self.redis_client:
            try:
                keys = self.redis_client.keys("gps:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass
    
    def cached(self, prefix: str = "", ttl: Optional[int] = None):
        """Décorateur de cache"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                key = self._key(prefix or func.__name__, *args, **kwargs)
                result = self.get(key)
                if result is not None:
                    return result
                result = func(*args, **kwargs)
                if result is not None:
                    self.set(key, result, ttl)
                return result
            return wrapper
        return decorator


# Singleton
_cache = None

def get_cache_manager() -> CacheManager:
    global _cache
    if _cache is None:
        _cache = CacheManager(CACHE_REDIS_URL, CACHE_TTL_SECONDS)
    return _cache