"""Decorators for the parking management system.

This module provides various decorators for common cross-cutting concerns
such as logging, caching, rate limiting, retry logic, authentication,
authorization, and performance monitoring.
"""

import functools
import time
import logging
import asyncio
import hashlib
import json
import pickle
import inspect
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Union, Type, Tuple, List
from functools import wraps
from contextlib import ContextDecorator
import traceback

# ============================================================================
# Logging Decorators
# ============================================================================

def log_call(logger: Optional[logging.Logger] = None, level: str = "DEBUG"):
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        logger: Logger instance to use
        level: Logging level (DEBUG, INFO, etc.)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        log_level = getattr(logging, level.upper())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Format arguments for logging
            args_str = ", ".join(
                f"{name}={repr(value)}" 
                for name, value in bound_args.arguments.items()
            )
            
            logger.log(log_level, f"Calling {func.__qualname__}({args_str})")
            
            try:
                result = func(*args, **kwargs)
                logger.log(log_level, f"{func.__qualname__} returned: {repr(result)}")
                return result
            except Exception as e:
                logger.log(log_level, f"{func.__qualname__} raised: {repr(e)}")
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            args_str = ", ".join(
                f"{name}={repr(value)}" 
                for name, value in bound_args.arguments.items()
            )
            
            logger.log(log_level, f"Calling {func.__qualname__}({args_str})")
            
            try:
                result = await func(*args, **kwargs)
                logger.log(log_level, f"{func.__qualname__} returned: {repr(result)}")
                return result
            except Exception as e:
                logger.log(log_level, f"{func.__qualname__} raised: {repr(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def log_execution_time(logger: Optional[logging.Logger] = None, level: str = "DEBUG"):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance to use
        level: Logging level
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        log_level = getattr(logging, level.upper())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end = time.perf_counter()
                duration = (end - start) * 1000  # Convert to milliseconds
                logger.log(
                    log_level,
                    f"{func.__qualname__} took {duration:.2f}ms"
                )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                end = time.perf_counter()
                duration = (end - start) * 1000
                logger.log(
                    log_level,
                    f"{func.__qualname__} took {duration:.2f}ms"
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def log_exceptions(logger: Optional[logging.Logger] = None, 
                   reraise: bool = True,
                   include_traceback: bool = True):
    """
    Decorator to log exceptions raised by functions.
    
    Args:
        logger: Logger instance to use
        reraise: Whether to reraise the exception after logging
        include_traceback: Whether to include traceback in log
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__qualname__}: {repr(e)}",
                    exc_info=include_traceback
                )
                if reraise:
                    raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__qualname__}: {repr(e)}",
                    exc_info=include_traceback
                )
                if reraise:
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


# ============================================================================
# Performance Monitoring Decorators
# ============================================================================

def profile(sort_by: str = 'cumulative', limit: int = 20):
    """
    Decorator to profile function execution using cProfile.
    
    Args:
        sort_by: How to sort the profile stats
        limit: Number of lines to show
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import cProfile
            import pstats
            import io
            
            profiler = cProfile.Profile()
            try:
                profiler.enable()
                result = func(*args, **kwargs)
                profiler.disable()
                return result
            finally:
                s = io.StringIO()
                stats = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
                stats.print_stats(limit)
                print(f"Profile for {func.__qualname__}:")
                print(s.getvalue())
        
        return wrapper
    return decorator


def monitor_memory():
    """Decorator to monitor memory usage of function."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import tracemalloc
            
            tracemalloc.start()
            start_snapshot = tracemalloc.take_snapshot()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_snapshot = tracemalloc.take_snapshot()
                tracemalloc.stop()
                
                stats = end_snapshot.compare_to(start_snapshot, 'lineno')
                print(f"Memory usage for {func.__qualname__}:")
                for stat in stats[:10]:
                    print(stat)
        
        return wrapper
    return decorator


# ============================================================================
# Caching Decorators
# ============================================================================

def cached(ttl: Optional[int] = None, 
           key_func: Optional[Callable] = None,
           cache_backend: Optional[Any] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds (None for no expiration)
        key_func: Function to generate cache key
        cache_backend: Cache backend to use (defaults to memory cache)
    """
    # Simple memory cache backend
    class MemoryCache:
        def __init__(self):
            self._cache = {}
            self._timestamps = {}
        
        def get(self, key):
            if key in self._cache:
                if key in self._timestamps:
                    if time.time() - self._timestamps[key] > ttl:
                        del self._cache[key]
                        del self._timestamps[key]
                        return None
                return self._cache[key]
            return None
        
        def set(self, key, value):
            self._cache[key] = value
            if ttl:
                self._timestamps[key] = time.time()
    
    cache = cache_backend or MemoryCache()
    
    def default_key_func(func, args, kwargs):
        """Default key generation function."""
        key_parts = [func.__module__, func.__qualname__]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    key_generator = key_func or default_key_func
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_generator(func, args, kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = key_generator(func, args, kwargs)
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        # Add cache management methods
        wrapper.cache_clear = lambda: cache._cache.clear() if hasattr(cache, '_cache') else None
        wrapper.cache_info = lambda: {
            'size': len(cache._cache) if hasattr(cache, '_cache') else 0,
            'ttl': ttl
        }
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def memoize(func: Callable) -> Callable:
    """
    Simple memoization decorator for functions with hashable arguments.
    """
    cache = {}
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Create a key from args and kwargs
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key = tuple(key_parts)
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    
    wrapper.cache = cache
    wrapper.cache_clear = lambda: cache.clear()
    wrapper.cache_info = lambda: {'size': len(cache)}
    
    return wrapper


# ============================================================================
# Retry Decorators
# ============================================================================

def retry(max_attempts: int = 3,
          delay: float = 1.0,
          backoff: float = 2.0,
          exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
          logger: Optional[logging.Logger] = None):
    """
    Decorator to retry function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        exceptions: Exception types to retry on
        logger: Logger instance
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__qualname__} failed after "
                            f"{max_attempts} attempts"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} for "
                        f"{func.__qualname__} failed: {e}. Retrying in "
                        f"{current_delay:.2f}s"
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__qualname__} failed after "
                            f"{max_attempts} attempts"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} for "
                        f"{func.__qualname__} failed: {e}. Retrying in "
                        f"{current_delay:.2f}s"
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def retry_with_circuit_breaker(failure_threshold: int = 5,
                                recovery_timeout: int = 60,
                                exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception):
    """
    Decorator implementing circuit breaker pattern with retry.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying again
        exceptions: Exception types to count as failures
    """
    circuit_state = {
        'failures': 0,
        'last_failure_time': None,
        'is_open': False
    }
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal circuit_state
            
            # Check if circuit is open
            if circuit_state['is_open']:
                if circuit_state['last_failure_time']:
                    elapsed = time.time() - circuit_state['last_failure_time']
                    if elapsed >= recovery_timeout:
                        circuit_state['is_open'] = False
                        circuit_state['failures'] = 0
                    else:
                        raise Exception(
                            f"Circuit breaker is open. "
                            f"Try again in {recovery_timeout - elapsed:.0f}s"
                        )
            
            try:
                result = func(*args, **kwargs)
                # Success - reset failure count
                circuit_state['failures'] = 0
                return result
            except exceptions as e:
                circuit_state['failures'] += 1
                circuit_state['last_failure_time'] = time.time()
                
                if circuit_state['failures'] >= failure_threshold:
                    circuit_state['is_open'] = True
                
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Authentication/Authorization Decorators
# ============================================================================

def require_auth():
    """Decorator to require authentication."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get request object from args (assuming first arg is self for methods)
            # This is a simplified example - adapt to your auth system
            request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
            
            if not request or not hasattr(request, 'user'):
                raise PermissionError("Authentication required")
            
            if not request.user:
                raise PermissionError("Authentication required")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permissions(*permissions: str):
    """Decorator to require specific permissions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
            
            if not request or not hasattr(request, 'user'):
                raise PermissionError("Authentication required")
            
            user = request.user
            user_permissions = getattr(user, 'permissions', [])
            
            missing = [p for p in permissions if p not in user_permissions]
            if missing:
                raise PermissionError(
                    f"Missing required permissions: {', '.join(missing)}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_roles(*roles: str):
    """Decorator to require specific roles."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
            
            if not request or not hasattr(request, 'user'):
                raise PermissionError("Authentication required")
            
            user = request.user
            user_roles = getattr(user, 'roles', [])
            
            if not any(role in user_roles for role in roles):
                raise PermissionError(
                    f"Required one of roles: {', '.join(roles)}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_ownership(resource_id_arg: str = 'resource_id'):
    """
    Decorator to require ownership of a resource.
    
    Args:
        resource_id_arg: Name of the argument containing resource ID
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get request and resource ID
            request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
            resource_id = kwargs.get(resource_id_arg)
            
            if not request or not hasattr(request, 'user'):
                raise PermissionError("Authentication required")
            
            # This is a simplified example - adapt to your ownership model
            user = request.user
            if not hasattr(user, 'owns_resource') or not user.owns_resource(resource_id):
                raise PermissionError("You don't own this resource")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Rate Limiting Decorators
# ============================================================================

def rate_limit(max_calls: int, period: int = 60, key_func: Optional[Callable] = None):
    """
    Decorator to rate limit function calls.
    
    Args:
        max_calls: Maximum number of calls allowed in the period
        period: Time period in seconds
        key_func: Function to generate rate limit key (e.g., by user ID)
    """
    # Simple in-memory rate limiter
    calls = {}
    
    def default_key_func(*args, **kwargs):
        return 'default'
    
    key_generator = key_func or default_key_func
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = key_generator(*args, **kwargs)
            now = time.time()
            
            # Clean up old calls
            if key in calls:
                calls[key] = [t for t in calls[key] if now - t < period]
            else:
                calls[key] = []
            
            # Check rate limit
            if len(calls.get(key, [])) >= max_calls:
                oldest = calls[key][0]
                reset_time = oldest + period
                raise Exception(
                    f"Rate limit exceeded. Max {max_calls} calls per {period}s. "
                    f"Reset at {datetime.fromtimestamp(reset_time)}"
                )
            
            # Record call
            calls.setdefault(key, []).append(now)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit_per_user(max_calls: int, period: int = 60):
    """Rate limit decorator keyed by user ID."""
    def key_func(*args, **kwargs):
        # Extract user ID from request
        request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
        if request and hasattr(request, 'user') and request.user:
            return str(request.user.id)
        return 'anonymous'
    
    return rate_limit(max_calls, period, key_func)


def rate_limit_per_ip(max_calls: int, period: int = 60):
    """Rate limit decorator keyed by IP address."""
    def key_func(*args, **kwargs):
        request = kwargs.get('request') or (args[1] if len(args) > 1 else None)
        if request and hasattr(request, 'client'):
            return request.client.host
        return 'unknown'
    
    return rate_limit(max_calls, period, key_func)


# ============================================================================
# Input Validation Decorators
# ============================================================================

def validate_args(**validators):
    """
    Decorator to validate function arguments.
    
    Args:
        **validators: Mapping of argument names to validator functions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Bind arguments to function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each argument
            for arg_name, validator in validators.items():
                if arg_name in bound_args.arguments:
                    value = bound_args.arguments[arg_name]
                    if not validator(value):
                        raise ValueError(
                            f"Invalid value for argument '{arg_name}': {value}"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_return(validator: Callable):
    """
    Decorator to validate function return value.
    
    Args:
        validator: Function that validates the return value
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if not validator(result):
                raise ValueError(f"Invalid return value: {result}")
            
            return result
        
        return wrapper
    return decorator


def sanitize_input(*args_to_sanitize: str, sanitizer: Optional[Callable] = None):
    """
    Decorator to sanitize function inputs.
    
    Args:
        *args_to_sanitize: Names of arguments to sanitize
        sanitizer: Sanitizer function (default: strip whitespace)
    """
    if sanitizer is None:
        sanitizer = lambda x: x.strip() if isinstance(x, str) else x
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Sanitize kwargs
            for arg in args_to_sanitize:
                if arg in kwargs:
                    kwargs[arg] = sanitizer(kwargs[arg])
            
            # Sanitize args (more complex - need to know positions)
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for i, (arg_name, value) in enumerate(bound_args.arguments.items()):
                if arg_name in args_to_sanitize:
                    bound_args.arguments[arg_name] = sanitizer(value)
            
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Transaction Decorators
# ============================================================================

def transactional(session_arg: str = 'session'):
    """
    Decorator to wrap function in a database transaction.
    
    Args:
        session_arg: Name of the session argument
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get session from args or kwargs
            session = kwargs.get(session_arg)
            if not session and len(args) > 1:
                # Try to find session by parameter name
                sig = inspect.signature(func)
                params = list(sig.parameters.values())
                for i, param in enumerate(params):
                    if param.name == session_arg and i < len(args):
                        session = args[i]
                        break
            
            if not session:
                raise ValueError(f"Could not find session argument '{session_arg}'")
            
            try:
                result = func(*args, **kwargs)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Synchronization Decorators
# ============================================================================

def synchronized(lock=None):
    """
    Decorator to synchronize function execution with a lock.
    
    Args:
        lock: Lock object to use (creates new RLock if None)
    """
    if lock is None:
        import threading
        lock = threading.RLock()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_lock(lock_name: str, timeout: Optional[int] = None):
    """
    Decorator to acquire a distributed lock before function execution.
    
    Args:
        lock_name: Name of the lock
        timeout: Lock timeout in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This is a simplified example - adapt to your lock system
            lock_acquired = False
            try:
                # Acquire lock (pseudo-code)
                # lock = acquire_lock(lock_name, timeout)
                lock_acquired = True
                return func(*args, **kwargs)
            finally:
                if lock_acquired:
                    # Release lock
                    # release_lock(lock_name)
                    pass
        
        return wrapper
    return decorator


# ============================================================================
# Deprecation Decorators
# ============================================================================

def deprecated(message: Optional[str] = None, removal_version: Optional[str] = None):
    """
    Decorator to mark functions as deprecated.
    
    Args:
        message: Deprecation message
        removal_version: Version when function will be removed
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            warning = f"Function '{func.__qualname__}' is deprecated"
            if message:
                warning += f": {message}"
            if removal_version:
                warning += f" (will be removed in version {removal_version})"
            
            import warnings
            warnings.warn(warning, DeprecationWarning, stacklevel=2)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Feature Flag Decorators
# ============================================================================

def feature_flag(flag_name: str, default: bool = False):
    """
    Decorator to conditionally enable function based on feature flag.
    
    Args:
        flag_name: Name of the feature flag
        default: Default value if flag not found
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check feature flag (simplified - adapt to your feature flag system)
            enabled = default
            
            # Example: check from config or environment
            # enabled = config.get_feature_flag(flag_name, default)
            
            if not enabled:
                raise Exception(f"Feature '{flag_name}' is not enabled")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Timing Decorators
# ============================================================================

def timeout(seconds: int, error_message: str = "Function call timed out"):
    """
    Decorator to timeout function execution.
    
    Args:
        seconds: Maximum execution time in seconds
        error_message: Error message on timeout
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def handler(signum, frame):
                raise TimeoutError(error_message)
            
            # Set timeout handler
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)
                return result
            finally:
                signal.alarm(0)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(error_message)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    
    return decorator


def timer(func: Callable) -> Callable:
    """
    Simple decorator to time function execution and print result.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            end = time.perf_counter()
            print(f"{func.__qualname__} took {end - start:.4f}s")
    
    return wrapper


# ============================================================================
# Singleton Decorators
# ============================================================================

def singleton(cls):
    """
    Decorator to implement singleton pattern for classes.
    """
    instances = {}
    
    @wraps(cls, updated=())  # updated=() prevents copying __dict__
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


def thread_safe_singleton(cls):
    """
    Thread-safe singleton decorator.
    """
    import threading
    
    instances = {}
    lock = threading.Lock()
    
    @wraps(cls, updated=())
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


# ============================================================================
# Class Decorators
# ============================================================================

def add_repr(cls):
    """
    Class decorator to add __repr__ method.
    """
    def __repr__(self):
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({attrs})"
    
    cls.__repr__ = __repr__
    return cls


def add_str(cls):
    """
    Class decorator to add __str__ method.
    """
    def __str__(self):
        attrs = ', '.join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({attrs})"
    
    cls.__str__ = __str__
    return cls


def auto_repr(*attrs):
    """
    Class decorator to auto-generate __repr__ from specified attributes.
    """
    def decorator(cls):
        def __repr__(self):
            values = ', '.join(f"{attr}={getattr(self, attr)!r}" for attr in attrs)
            return f"{cls.__name__}({values})"
        
        cls.__repr__ = __repr__
        return cls
    
    return decorator


def auto_str(*attrs):
    """
    Class decorator to auto-generate __str__ from specified attributes.
    """
    def decorator(cls):
        def __str__(self):
            values = ', '.join(f"{attr}={getattr(self, attr)}" for attr in attrs)
            return f"{cls.__name__}({values})"
        
        cls.__str__ = __str__
        return cls
    
    return decorator


# ============================================================================
# Context Managers as Decorators
# ============================================================================

class timeout_context(ContextDecorator):
    """Context manager/decorator for timeout."""
    
    def __init__(self, seconds: int, error_message: str = "Operation timed out"):
        self.seconds = seconds
        self.error_message = error_message
    
    def __enter__(self):
        import signal
        
        def handler(signum, frame):
            raise TimeoutError(self.error_message)
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(self.seconds)
        return self
    
    def __exit__(self, *exc):
        import signal
        signal.alarm(0)
        return False


class suppress_exceptions(ContextDecorator):
    """Context manager/decorator to suppress specified exceptions."""
    
    def __init__(self, *exceptions):
        self.exceptions = exceptions or (Exception,)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return isinstance(exc_val, self.exceptions)


# ============================================================================
# Utility Decorators
# ============================================================================

def once(func: Callable) -> Callable:
    """
    Decorator to ensure function is only called once.
    """
    has_run = False
    result = None
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal has_run, result
        if not has_run:
            result = func(*args, **kwargs)
            has_run = True
        return result
    
    return wrapper


def memoized_property(func: Callable):
    """
    Decorator for memoized properties (cached property).
    """
    @property
    @functools.wraps(func)
    def wrapper(self):
        cache_attr = f"_cached_{func.__name__}"
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, func(self))
        return getattr(self, cache_attr)
    
    return wrapper


def async_to_sync(func: Callable) -> Callable:
    """
    Decorator to convert async function to sync.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            loop.close()
    
    return wrapper


def sync_to_async(func: Callable) -> Callable:
    """
    Decorator to convert sync function to async.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    
    return wrapper


def notify_on_error(notification_func: Callable):
    """
    Decorator to send notification on function error.
    
    Args:
        notification_func: Function to call with error details
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                notification_func({
                    'function': func.__qualname__,
                    'args': args,
                    'kwargs': kwargs,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
                raise
        
        return wrapper
    return decorator


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Logging
    'log_call',
    'log_execution_time',
    'log_exceptions',
    
    # Performance
    'profile',
    'monitor_memory',
    
    # Caching
    'cached',
    'memoize',
    
    # Retry
    'retry',
    'retry_with_circuit_breaker',
    
    # Auth
    'require_auth',
    'require_permissions',
    'require_roles',
    'require_ownership',
    
    # Rate limiting
    'rate_limit',
    'rate_limit_per_user',
    'rate_limit_per_ip',
    
    # Validation
    'validate_args',
    'validate_return',
    'sanitize_input',
    
    # Transactions
    'transactional',
    
    # Synchronization
    'synchronized',
    'with_lock',
    
    # Deprecation
    'deprecated',
    
    # Feature flags
    'feature_flag',
    
    # Timing
    'timeout',
    'timer',
    
    # Singleton
    'singleton',
    'thread_safe_singleton',
    
    # Class decorators
    'add_repr',
    'add_str',
    'auto_repr',
    'auto_str',
    
    # Context managers
    'timeout_context',
    'suppress_exceptions',
    
    # Utilities
    'once',
    'memoized_property',
    'async_to_sync',
    'sync_to_async',
    'notify_on_error',
]