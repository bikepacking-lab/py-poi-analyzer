#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import logging
from typing import Callable, Any, Type, Tuple
from functools import wraps
import random

logger = logging.getLogger(__name__)

class RetryManager:
    """Gestionnaire de retry intelligent"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction avec retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if not any(isinstance(e, exc_type) for exc_type in self.retry_on_exceptions):
                    logger.debug(f"Exception non retryable: {type(e).__name__}")
                    raise
                
                if attempt >= self.max_retries:
                    logger.error(f"Échec après {self.max_retries} tentatives: {e}")
                    raise
                
                delay = self.base_delay * (self.backoff_factor ** attempt)
                if self.jitter:
                    jitter_factor = 0.7 + (0.6 * random.random())
                    delay = delay * jitter_factor
                delay = min(delay, self.max_delay)
                
                logger.warning(
                    f"Tentative {attempt + 1}/{self.max_retries} échouée: {e}. "
                    f"Nouvelle tentative dans {delay:.2f}s"
                )
                time.sleep(delay)
        
        raise last_exception if last_exception else RuntimeError("Échec inattendu")
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper


class CircuitBreaker:
    """Circuit Breaker"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def can_execute(self) -> bool:
        current_time = time.time()
        
        if self.state == "CLOSED":
            return True
        
        elif self.state == "OPEN":
            if self.last_failure_time and (current_time - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit Breaker: passage en HALF_OPEN")
                return True
            return False
        
        elif self.state == "HALF_OPEN":
            return True
        
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.last_failure_time = None
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit Breaker: retour en CLOSED")
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit Breaker: passage en OPEN ({self.failure_count} échecs)")
        
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.logger.warning("Circuit Breaker: retour en OPEN")
    
    def reset(self):
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None


def retry(max_retries: int = 3, base_delay: float = 1.0, 
          retry_on_exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """Décorateur de retry simplifié"""
    retry_manager = RetryManager(
        max_retries=max_retries,
        base_delay=base_delay,
        retry_on_exceptions=retry_on_exceptions
    )
    return retry_manager