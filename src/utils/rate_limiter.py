"""
Rate limiting utilities for API calls and web scraping.

This module provides rate limiting functionality to ensure respectful usage
of external APIs and websites while avoiding being blocked.
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 30
    requests_per_hour: int = 1000
    burst_limit: int = 5
    cooldown_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0

class RateLimiter:
    """Token bucket rate limiter with burst support and backoff."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_limit
        self.last_refill = time.time()
        self.request_times: deque = deque()
        self.consecutive_failures = 0
        self.last_failure_time = 0
        
        # Calculate refill rate (tokens per second)
        self.refill_rate = config.requests_per_minute / 60.0
    
    async def acquire(self) -> bool:
        """
        Acquire a token for making a request.
        
        Returns:
            True if token acquired, False if rate limited
        """
        current_time = time.time()
        
        # Check if we're in backoff period
        if self._is_in_backoff(current_time):
            backoff_time = self._get_backoff_time()
            logger.warning(f"Rate limiter in backoff for {backoff_time:.1f}s")
            await asyncio.sleep(backoff_time)
            return False
        
        # Refill tokens based on time elapsed
        self._refill_tokens(current_time)
        
        # Check hourly limit
        if not self._check_hourly_limit(current_time):
            logger.warning("Hourly rate limit exceeded")
            return False
        
        # Check if we have tokens available
        if self.tokens >= 1:
            self.tokens -= 1
            self.request_times.append(current_time)
            
            # Apply cooldown
            if self.config.cooldown_seconds > 0:
                await asyncio.sleep(self.config.cooldown_seconds)
            
            return True
        
        # No tokens available
        wait_time = 1.0 / self.refill_rate
        logger.debug(f"Rate limited, waiting {wait_time:.1f}s for next token")
        await asyncio.sleep(wait_time)
        return False
    
    def _refill_tokens(self, current_time: float) -> None:
        """Refill tokens based on elapsed time."""
        time_elapsed = current_time - self.last_refill
        tokens_to_add = time_elapsed * self.refill_rate
        
        self.tokens = min(self.config.burst_limit, self.tokens + tokens_to_add)
        self.last_refill = current_time
    
    def _check_hourly_limit(self, current_time: float) -> bool:
        """Check if we're within hourly request limit."""
        # Remove requests older than 1 hour
        cutoff_time = current_time - 3600
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
        
        return len(self.request_times) < self.config.requests_per_hour
    
    def _is_in_backoff(self, current_time: float) -> bool:
        """Check if we're currently in a backoff period."""
        if self.consecutive_failures == 0:
            return False
        
        backoff_time = self._get_backoff_time()
        return (current_time - self.last_failure_time) < backoff_time
    
    def _get_backoff_time(self) -> float:
        """Calculate current backoff time based on consecutive failures."""
        backoff = min(
            self.config.cooldown_seconds * (self.config.backoff_multiplier ** self.consecutive_failures),
            self.config.max_backoff_seconds
        )
        return backoff
    
    def record_success(self) -> None:
        """Record a successful request (resets backoff)."""
        self.consecutive_failures = 0
    
    def record_failure(self) -> None:
        """Record a failed request (increases backoff)."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        logger.warning(f"Request failed, consecutive failures: {self.consecutive_failures}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        current_time = time.time()
        self._refill_tokens(current_time)
        
        return {
            "available_tokens": int(self.tokens),
            "max_tokens": self.config.burst_limit,
            "requests_last_hour": len(self.request_times),
            "hourly_limit": self.config.requests_per_hour,
            "consecutive_failures": self.consecutive_failures,
            "in_backoff": self._is_in_backoff(current_time),
            "backoff_time_remaining": max(0, self._get_backoff_time() - (current_time - self.last_failure_time)) if self.consecutive_failures > 0 else 0
        }

class GlobalRateLimiter:
    """Global rate limiter manager for different services."""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self.default_configs = {
            "linkedin": RateLimitConfig(requests_per_minute=10, requests_per_hour=200, cooldown_seconds=2.0),
            "openrouter": RateLimitConfig(requests_per_minute=60, requests_per_hour=3000, cooldown_seconds=0.5),
            "hunter_io": RateLimitConfig(requests_per_minute=30, requests_per_hour=1000, cooldown_seconds=1.0),
            "apollo_io": RateLimitConfig(requests_per_minute=20, requests_per_hour=500, cooldown_seconds=1.5),
            "ollama": RateLimitConfig(requests_per_minute=120, requests_per_hour=5000, cooldown_seconds=0.1),
            "default": RateLimitConfig()
        }
    
    def get_limiter(self, service: str) -> RateLimiter:
        """Get or create rate limiter for a service."""
        if service not in self.limiters:
            config = self.default_configs.get(service, self.default_configs["default"])
            self.limiters[service] = RateLimiter(config)
            logger.info(f"Created rate limiter for service: {service}")
        
        return self.limiters[service]
    
    async def acquire(self, service: str) -> bool:
        """Acquire token for a specific service."""
        limiter = self.get_limiter(service)
        return await limiter.acquire()
    
    def record_success(self, service: str) -> None:
        """Record successful request for a service."""
        if service in self.limiters:
            self.limiters[service].record_success()
    
    def record_failure(self, service: str) -> None:
        """Record failed request for a service."""
        if service in self.limiters:
            self.limiters[service].record_failure()
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all rate limiters."""
        return {service: limiter.get_status() for service, limiter in self.limiters.items()}
    
    def configure_service(self, service: str, config: RateLimitConfig) -> None:
        """Configure rate limiting for a specific service."""
        self.default_configs[service] = config
        if service in self.limiters:
            # Replace existing limiter with new config
            self.limiters[service] = RateLimiter(config)
        logger.info(f"Configured rate limiter for service: {service}")

# Global rate limiter instance
global_rate_limiter = GlobalRateLimiter()

def rate_limited(service: str):
    """Decorator for rate-limited functions."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Acquire rate limit token
            if not await global_rate_limiter.acquire(service):
                logger.warning(f"Rate limit exceeded for {service}")
                return None
            
            try:
                result = await func(*args, **kwargs)
                global_rate_limiter.record_success(service)
                return result
            except Exception as e:
                global_rate_limiter.record_failure(service)
                logger.error(f"Rate limited function {func.__name__} failed: {e}")
                raise
        
        return wrapper
    return decorator

async def with_rate_limit(service: str, func: Callable, *args, **kwargs) -> Any:
    """Execute function with rate limiting."""
    if not await global_rate_limiter.acquire(service):
        logger.warning(f"Rate limit exceeded for {service}")
        return None
    
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        global_rate_limiter.record_success(service)
        return result
    except Exception as e:
        global_rate_limiter.record_failure(service)
        logger.error(f"Rate limited function failed: {e}")
        raise

def get_rate_limiter(service: str) -> RateLimiter:
    """Get rate limiter for a specific service."""
    return global_rate_limiter.get_limiter(service)

def configure_rate_limiting(service: str, **kwargs) -> None:
    """Configure rate limiting for a service."""
    config = RateLimitConfig(**kwargs)
    global_rate_limiter.configure_service(service, config)

def get_rate_limit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all rate limiters."""
    return global_rate_limiter.get_all_status()