import asyncio
import time
from typing import Any, Callable, Optional, Dict
from datetime import datetime


class RetryManager:
    """Centralized retry manager for all Family Guy bot services."""
    
    # Global retry configuration - single source of truth
    DEFAULT_MAX_ATTEMPTS = 2  # Reduced to prevent thread explosion
    DEFAULT_BASE_DELAY = 0.5  # 500ms base delay
    DEFAULT_MAX_DELAY = 10.0  # Maximum delay cap
    DEFAULT_EXPONENTIAL_BASE = 2  # Exponential backoff multiplier
    
    @staticmethod
    def calculate_delay(attempt: int, base_delay: float = DEFAULT_BASE_DELAY, 
                       exponential_base: float = DEFAULT_EXPONENTIAL_BASE,
                       max_delay: float = DEFAULT_MAX_DELAY) -> float:
        """Calculate delay for exponential backoff."""
        if attempt <= 0:
            return 0
        delay = base_delay * (exponential_base ** (attempt - 1))
        return min(delay, max_delay)
    
    @staticmethod
    async def retry_async(
        operation: Callable,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        base_delay: float = DEFAULT_BASE_DELAY,
        operation_name: str = "operation",
        service_name: str = "service",
        validation_func: Optional[Callable[[Any], bool]] = None,
        **operation_kwargs
    ) -> Optional[Any]:
        """
        Centralized async retry mechanism.
        
        Args:
            operation: Async function to retry
            max_attempts: Maximum number of attempts (default: 2)
            base_delay: Base delay between retries (default: 0.5s)
            operation_name: Name of operation for logging
            service_name: Name of service for logging
            validation_func: Optional function to validate result
            **operation_kwargs: Arguments to pass to operation
            
        Returns:
            Result of successful operation or None if all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                # Add delay before retry (not before first attempt)
                if attempt > 0:
                    delay = RetryManager.calculate_delay(attempt, base_delay)
                    print(f"⏳ {service_name}: Waiting {delay:.1f}s before retry {attempt + 1}/{max_attempts} for {operation_name}")
                    await asyncio.sleep(delay)
                
                print(f"🔄 {service_name}: Attempting {operation_name} (attempt {attempt + 1}/{max_attempts})")
                
                # Execute the operation
                result = await operation(**operation_kwargs)
                
                # Validate result if validation function provided
                if validation_func and not validation_func(result):
                    print(f"❌ {service_name}: {operation_name} validation failed (attempt {attempt + 1}/{max_attempts})")
                    if attempt < max_attempts - 1:
                        continue  # Try again
                    else:
                        print(f"💀 {service_name}: All {max_attempts} attempts failed validation for {operation_name}")
                        return None
                
                print(f"✅ {service_name}: {operation_name} succeeded after {attempt + 1} attempts")
                return result
                
            except Exception as e:
                last_exception = e
                print(f"❌ {service_name}: {operation_name} failed (attempt {attempt + 1}/{max_attempts}): {e}")
                
                if attempt < max_attempts - 1:
                    continue  # Try again
                else:
                    print(f"💀 {service_name}: All {max_attempts} attempts failed for {operation_name}. Last error: {e}")
                    break
        
        return None
    
    @staticmethod
    def retry_sync(
        operation: Callable,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        base_delay: float = DEFAULT_BASE_DELAY,
        operation_name: str = "operation",
        service_name: str = "service",
        validation_func: Optional[Callable[[Any], bool]] = None,
        **operation_kwargs
    ) -> Optional[Any]:
        """
        Centralized synchronous retry mechanism.
        
        Args:
            operation: Sync function to retry
            max_attempts: Maximum number of attempts (default: 2)
            base_delay: Base delay between retries (default: 0.5s)
            operation_name: Name of operation for logging
            service_name: Name of service for logging
            validation_func: Optional function to validate result
            **operation_kwargs: Arguments to pass to operation
            
        Returns:
            Result of successful operation or None if all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                # Add delay before retry (not before first attempt)
                if attempt > 0:
                    delay = RetryManager.calculate_delay(attempt, base_delay)
                    print(f"⏳ {service_name}: Waiting {delay:.1f}s before retry {attempt + 1}/{max_attempts} for {operation_name}")
                    time.sleep(delay)
                
                print(f"🔄 {service_name}: Attempting {operation_name} (attempt {attempt + 1}/{max_attempts})")
                
                # Execute the operation
                result = operation(**operation_kwargs)
                
                # Validate result if validation function provided
                if validation_func and not validation_func(result):
                    print(f"❌ {service_name}: {operation_name} validation failed (attempt {attempt + 1}/{max_attempts})")
                    if attempt < max_attempts - 1:
                        continue  # Try again
                    else:
                        print(f"💀 {service_name}: All {max_attempts} attempts failed validation for {operation_name}")
                        return None
                
                print(f"✅ {service_name}: {operation_name} succeeded after {attempt + 1} attempts")
                return result
                
            except Exception as e:
                last_exception = e
                print(f"❌ {service_name}: {operation_name} failed (attempt {attempt + 1}/{max_attempts}): {e}")
                
                if attempt < max_attempts - 1:
                    continue  # Try again
                else:
                    print(f"💀 {service_name}: All {max_attempts} attempts failed for {operation_name}. Last error: {e}")
                    break
        
        return None


class RetryConfig:
    """Predefined retry configurations for different operation types."""
    
    # Discord message sending - critical, deserves 2 attempts
    DISCORD_MESSAGE = {
        "max_attempts": 2,
        "base_delay": 0.5,
        "operation_name": "discord_message"
    }
    
    # Fallback generation - less critical, 1 attempt only 
    FALLBACK_GENERATION = {
        "max_attempts": 1,  # No retries for fallbacks to prevent cascading
        "base_delay": 0.3,
        "operation_name": "fallback_generation"
    }
    
    # Quality control check - fast operation, 2 attempts
    QUALITY_CHECK = {
        "max_attempts": 2,
        "base_delay": 0.2,
        "operation_name": "quality_check"
    }
    
    # Message router orchestration - core operation, 2 attempts
    MESSAGE_ROUTER = {
        "max_attempts": 2,
        "base_delay": 0.5,
        "operation_name": "message_router"
    }
    
    # Organic conversation analysis - background operation, 1 attempt only
    ORGANIC_ANALYSIS = {
        "max_attempts": 1,  # No retries to prevent exponential explosion
        "base_delay": 0.3,
        "operation_name": "organic_analysis"
    }


# Export convenience functions
async def retry_async(*args, **kwargs):
    """Convenience function for async retries."""
    return await RetryManager.retry_async(*args, **kwargs)

def retry_sync(*args, **kwargs):
    """Convenience function for sync retries."""
    return RetryManager.retry_sync(*args, **kwargs) 