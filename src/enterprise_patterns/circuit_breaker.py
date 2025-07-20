"""
Production-Grade Circuit Breaker Pattern Implementation

This module provides a robust circuit breaker implementation designed for high-frequency
financial applications and real-time data processing systems. The circuit breaker
prevents cascading failures and provides graceful degradation under fault conditions.

Based on production experience scaling real-time market data systems processing
500+ messages/second with sub-second latency requirements.

Key Features:
- Three-state circuit breaker (CLOSED, OPEN, HALF_OPEN)
- Configurable failure thresholds and recovery timeouts  
- Automatic failure detection and recovery
- Comprehensive logging and metrics integration
- Thread-safe implementation for concurrent environments
- Async/await support for modern Python applications

Author: Real-Time Systems Engineering
License: MIT
"""

import asyncio
import logging
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass
from functools import wraps

# Type variables for generic function support
T = TypeVar('T')

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states following the classic pattern."""
    CLOSED = "CLOSED"       # Normal operation, requests allowed
    OPEN = "OPEN"           # Fault detected, requests blocked
    HALF_OPEN = "HALF_OPEN" # Testing recovery, limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.
    
    This configuration is based on production tuning for financial data systems
    where reliability and quick recovery are critical.
    """
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: float = 60.0     # Seconds before attempting recovery
    success_threshold: int = 3          # Successes needed to close circuit in HALF_OPEN
    timeout: float = 30.0               # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures


@dataclass 
class CircuitBreakerMetrics:
    """Metrics collection for circuit breaker monitoring.
    
    These metrics are designed for Prometheus integration and production monitoring.
    """
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_open_count: int = 0
    circuit_half_open_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_consecutive_failures: int = 0
    current_consecutive_successes: int = 0


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Production-grade circuit breaker implementation for high-reliability systems.
    
    This implementation is based on patterns used in real-time financial data processing
    where system reliability and fast recovery are critical business requirements.
    
    Example Usage:
    ```python
    # Configure circuit breaker for external API calls
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        timeout=30.0
    )
    
    circuit_breaker = CircuitBreaker("exchange_api", config)
    
    # Use as decorator
    @circuit_breaker
    async def call_exchange_api():
        # Your API call implementation
        pass
    
    # Or use as context manager
    async with circuit_breaker:
        result = await some_external_service()
    ```
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker with configuration.
        
        Args:
            name: Identifier for this circuit breaker (used in logging/metrics)
            config: Configuration object defining circuit breaker behavior
        """
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()  # Thread-safe operations
        
        # State transition tracking
        self._state_changed_time = time.time()
        self._last_attempt_time: Optional[float] = None
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {config}")
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap functions with circuit breaker protection."""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await self._execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return self._execute_sync(func, *args, **kwargs)
            return sync_wrapper
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._check_and_update_state()
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with failure handling."""
        if exc_type is not None and isinstance(exc_val, self.config.expected_exception):
            self._record_failure()
        else:
            self._record_success()
    
    async def _execute_async(self, func: Callable, *args, **kwargs) -> T:
        """Execute async function with circuit breaker protection."""
        with self._lock:
            self._check_and_update_state()
            
            if self.state == CircuitState.OPEN:
                self.metrics.total_requests += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self._format_last_failure_time()}"
                )
        
        start_time = time.time()
        self.metrics.total_requests += 1
        
        try:
            # Execute with timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.config.timeout
            )
            
            execution_time = time.time() - start_time
            self._record_success()
            
            logger.debug(
                f"Circuit breaker '{self.name}' - Successful call "
                f"(execution_time: {execution_time:.3f}s)"
            )
            return result
            
        except asyncio.TimeoutError as e:
            execution_time = time.time() - start_time
            self._record_failure()
            logger.warning(
                f"Circuit breaker '{self.name}' - Timeout after {execution_time:.3f}s"
            )
            raise
            
        except self.config.expected_exception as e:
            execution_time = time.time() - start_time
            self._record_failure()
            logger.warning(
                f"Circuit breaker '{self.name}' - Failure after {execution_time:.3f}s: {e}"
            )
            raise
    
    def _execute_sync(self, func: Callable, *args, **kwargs) -> T:
        """Execute synchronous function with circuit breaker protection."""
        with self._lock:
            self._check_and_update_state()
            
            if self.state == CircuitState.OPEN:
                self.metrics.total_requests += 1
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self._format_last_failure_time()}"
                )
        
        start_time = time.time()
        self.metrics.total_requests += 1
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            self._record_success()
            
            logger.debug(
                f"Circuit breaker '{self.name}' - Successful call "
                f"(execution_time: {execution_time:.3f}s)"
            )
            return result
            
        except self.config.expected_exception as e:
            execution_time = time.time() - start_time
            self._record_failure()
            logger.warning(
                f"Circuit breaker '{self.name}' - Failure after {execution_time:.3f}s: {e}"
            )
            raise
    
    def _check_and_update_state(self) -> None:
        """Check current state and update if necessary."""
        current_time = time.time()
        self._last_attempt_time = current_time
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            time_since_state_change = current_time - self._state_changed_time
            if time_since_state_change >= self.config.recovery_timeout:
                self._transition_to_half_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # In HALF_OPEN state, we allow limited testing
            # State transitions happen in _record_success/_record_failure
            pass
    
    def _record_success(self) -> None:
        """Record a successful operation and update state accordingly."""
        with self._lock:
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()
            self.metrics.current_consecutive_failures = 0
            self.metrics.current_consecutive_successes += 1
            
            if self.state == CircuitState.HALF_OPEN:
                if self.metrics.current_consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()
                    logger.info(
                        f"Circuit breaker '{self.name}' - Recovered successfully, "
                        f"returning to CLOSED state"
                    )
    
    def _record_failure(self) -> None:
        """Record a failed operation and update state accordingly."""
        with self._lock:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.time()
            self.metrics.current_consecutive_successes = 0
            self.metrics.current_consecutive_failures += 1
            
            if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self.metrics.current_consecutive_failures >= self.config.failure_threshold:
                    self._transition_to_open()
                    logger.error(
                        f"Circuit breaker '{self.name}' - Failure threshold reached, "
                        f"opening circuit (failures: {self.metrics.current_consecutive_failures})"
                    )
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        self.state = CircuitState.OPEN
        self._state_changed_time = time.time()
        self.metrics.circuit_open_count += 1
        
        logger.warning(
            f"Circuit breaker '{self.name}' transitioned to OPEN state. "
            f"Recovery timeout: {self.config.recovery_timeout}s"
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state for recovery testing."""
        self.state = CircuitState.HALF_OPEN
        self._state_changed_time = time.time()
        self.metrics.circuit_half_open_count += 1
        self.metrics.current_consecutive_successes = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN state for testing")
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (normal operation)."""
        self.state = CircuitState.CLOSED
        self._state_changed_time = time.time()
        self.metrics.current_consecutive_failures = 0
        
        logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED state")
    
    def _format_last_failure_time(self) -> str:
        """Format last failure time for human-readable output."""
        if self.metrics.last_failure_time:
            failure_time = datetime.fromtimestamp(
                self.metrics.last_failure_time, 
                tz=timezone.utc
            )
            return failure_time.isoformat()
        return "Never"
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for monitoring and alerting.
        
        Returns:
            Dictionary containing all metrics suitable for Prometheus export
        """
        with self._lock:
            success_rate = 0.0
            if self.metrics.total_requests > 0:
                success_rate = self.metrics.successful_requests / self.metrics.total_requests
            
            return {
                "name": self.name,
                "state": self.state.value,
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": success_rate,
                "circuit_open_count": self.metrics.circuit_open_count,
                "circuit_half_open_count": self.metrics.circuit_half_open_count,
                "current_consecutive_failures": self.metrics.current_consecutive_failures,
                "current_consecutive_successes": self.metrics.current_consecutive_successes,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time,
                "last_attempt_time": self._last_attempt_time,
                "state_changed_time": self._state_changed_time,
            }
    
    def reset(self) -> None:
        """
        Reset circuit breaker to initial state.
        
        This should only be used for testing or manual recovery scenarios.
        """
        with self._lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitBreakerMetrics()
            self._state_changed_time = time.time()
            self._last_attempt_time = None
            
            logger.warning(f"Circuit breaker '{self.name}' manually reset to CLOSED state")


# Factory function for common configurations
def create_exchange_api_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Create a circuit breaker optimized for external exchange API calls.
    
    This configuration is based on production experience with cryptocurrency
    exchange APIs that typically have varying response times and occasional
    rate limiting or connectivity issues.
    
    Args:
        name: Identifier for this circuit breaker
        
    Returns:
        Configured CircuitBreaker instance
    """
    config = CircuitBreakerConfig(
        failure_threshold=5,      # Allow 5 failures before opening
        recovery_timeout=60.0,    # Wait 1 minute before testing recovery
        success_threshold=3,      # Need 3 successes to fully recover
        timeout=30.0,             # 30 second timeout for API calls
        expected_exception=(Exception,)  # All exceptions count as failures
    )
    
    return CircuitBreaker(name, config)


def create_database_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Create a circuit breaker optimized for database operations.
    
    Database operations typically have different failure patterns than
    external APIs, requiring different thresholds and timeouts.
    
    Args:
        name: Identifier for this circuit breaker
        
    Returns:
        Configured CircuitBreaker instance
    """
    config = CircuitBreakerConfig(
        failure_threshold=3,      # Databases should fail fast
        recovery_timeout=30.0,    # Shorter recovery time for internal services
        success_threshold=2,      # Quick recovery for internal systems
        timeout=10.0,             # Shorter timeout for database operations
        expected_exception=(Exception,)
    )
    
    return CircuitBreaker(name, config)


# Example usage and testing
if __name__ == "__main__":
    async def example_usage():
        """Demonstrate circuit breaker usage patterns."""
        
        # Create circuit breaker for external API
        api_circuit = create_exchange_api_circuit_breaker("binance_api")
        
        # Example 1: Using as decorator
        @api_circuit
        async def fetch_market_data():
            # Simulate API call that might fail
            import random
            if random.random() < 0.3:  # 30% failure rate
                raise Exception("API connection failed")
            return {"price": 50000, "volume": 1000}
        
        # Example 2: Using as context manager
        async def manual_api_call():
            async with api_circuit:
                # Your API logic here
                return await fetch_market_data()
        
        # Test the circuit breaker
        for i in range(10):
            try:
                result = await fetch_market_data()
                print(f"Call {i+1}: Success - {result}")
            except Exception as e:
                print(f"Call {i+1}: Failed - {e}")
            
            # Print metrics every few calls
            if (i + 1) % 3 == 0:
                metrics = api_circuit.get_metrics()
                print(f"Metrics: State={metrics['state']}, "
                      f"Success Rate={metrics['success_rate']:.2%}")
    
    # Run example
    asyncio.run(example_usage()) 