# src/utils/di_container.py

from typing import Callable, Dict, Any, Type
import threading
import logging
from .config_loader import ConfigLoader
from .exceptions import (
    ConfigurationErrorFactory,
    ValidationError,
)
logger = logging.getLogger("DIContainer")
logger.setLevel(logging.DEBUG)


class DIContainer:
    def __init__(self):
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._lock = threading.Lock()

    def register_singleton(self, cls: Type, instance: Any = None) -> None:
        """Registers a class as a singleton."""
        try:
            with self._lock:
                self._singletons[cls] = instance
            logger.debug(f"Singleton registered for class: {cls.__name__}")
        finally:
            logger.debug(f"Released lock for singleton registration: {cls.__name__}")

    def register_factory(self, cls: Type, factory: Callable) -> None:
        """Registers a factory method for a class."""
        try:
            with self._lock:
                self._factories[cls] = factory
            logger.debug(f"Factory registered for class: {cls.__name__}")
        finally:
            logger.debug(f"Released lock for factory registration: {cls.__name__}")

    def resolve(self, cls: Type) -> Any:
        """Resolves an instance of the requested class."""
        logger.debug(f"Attempting to resolve class: {cls.__name__}")
        try:
            with self._lock:
                if cls in self._singletons:
                    if self._singletons[cls] is None:
                        logger.debug(f"Creating singleton instance for class: {cls.__name__}")
                        self._singletons[cls] = cls()
                        logger.debug(f"Singleton instance created for class: {cls.__name__}")
                    else:
                        logger.debug(f"Returning existing singleton instance for class: {cls.__name__}")
                    return self._singletons[cls]
                elif cls in self._factories:
                    logger.debug(f"Creating instance via factory for class: {cls.__name__}")
                    instance = self._factories[cls]()
                    logger.debug(f"Factory instance created for class: {cls.__name__}")
                    return instance
                else:
                    logger.error(f"Class {cls.__name__} not registered in DI container.")
                    raise ValueError(f"Class {cls.__name__} not registered in DI container.")
        finally:
            logger.debug(f"Released lock after resolving class: {cls.__name__}")

    def register_conditional(
        self, cls: Type, condition: Callable[[], bool], factory: Callable = None
    ) -> None:
        """Registers a factory conditionally based on a provided condition."""
        if condition():
            self.register_factory(cls, factory)
            logger.debug(f"Conditional factory registered for class: {cls.__name__}")
        else:
            logger.debug(
                f"Condition not met. Factory not registered for class: {cls.__name__}"
            )

    def detect_circular_dependencies(self, cls: Type, resolving: set) -> None:
        """Detects circular dependencies during resolution."""
        if cls in resolving:
            raise RuntimeError(f"Circular dependency detected for class: {cls.__name__}")
        resolving.add(cls)
        try:
            if cls in self._factories:
                factory_cls = self._factories[cls]
                # Example: If the factory creates another class instance, detect circular dependencies in that process
                if isinstance(factory_cls, Type):
                    self.detect_circular_dependencies(factory_cls, resolving)
        finally:
            resolving.remove(cls)

    def scope_management(self, scope: str):
        """Manages different scopes for instances."""
        if scope not in ["request", "session", "singleton"]:
            raise ValueError(f"Invalid scope: {scope}")
        # Implement logic based on the scope
        if scope == "request":
            # Manage request-scoped instances
            pass
        elif scope == "session":
            # Manage session-scoped instances
            pass
        logger.debug(f"Scope management for {scope} not implemented yet.")
        
    def instance_tracking(self) -> Dict[str, int]:
        """Tracks the number of instances created for each class."""
        instance_count = {cls.__name__: 0 for cls in self._singletons}
        for cls, instance in self._singletons.items():
            if instance is not None:
                instance_count[cls.__name__] += 1
        logger.debug(f"Instance tracking: {instance_count}")
        return instance_count
    
    def cleanup_instances(self):
        """Cleans up instances, invoking any cleanup strategies."""
        logger.debug("Starting instance cleanup.")
        
        for cls, instance in list(self._singletons.items()):
            if instance is not None:
                try:
                    # Check if the instance has a cleanup method and call it
                    if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                        logger.debug(f"Invoking cleanup for class: {cls.__name__}")
                        instance.cleanup()
                    elif hasattr(instance, 'close') and callable(getattr(instance, 'close')):
                        logger.debug(f"Invoking close for class: {cls.__name__}")
                        instance.close()
                    # Optionally, implement any custom cleanup logic here
                except Exception as e:
                    logger.error(f"Error during cleanup for {cls.__name__}: {e}")
                finally:
                    # Remove the instance from the container after cleanup
                    logger.debug(f"Removing instance of {cls.__name__} from DI container.")
                    del self._singletons[cls]
        
        logger.debug("Completed instance cleanup.")
