"""
Dependency injection container for service management.
"""
from typing import Dict, Any, TypeVar, Type, Optional, Callable
from abc import ABC, abstractmethod
import inspect
from functools import wraps


T = TypeVar('T')


class ServiceLifetime:
    """Service lifetime constants."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """Describes a service registration."""
    
    def __init__(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[..., T]] = None,
        instance: Optional[T] = None,
        lifetime: str = ServiceLifetime.TRANSIENT
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        if not any([implementation, factory, instance]):
            raise ValueError("Must provide implementation, factory, or instance")


class ServiceContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
    
    def register_singleton(self, service_type: Type[T], implementation: Type[T] = None) -> 'ServiceContainer':
        """Register a service as singleton."""
        impl = implementation or service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        return self
    
    def register_transient(self, service_type: Type[T], implementation: Type[T] = None) -> 'ServiceContainer':
        """Register a service as transient."""
        impl = implementation or service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._services[service_type] = descriptor
        return self
    
    def register_scoped(self, service_type: Type[T], implementation: Type[T] = None) -> 'ServiceContainer':
        """Register a service as scoped."""
        impl = implementation or service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=impl,
            lifetime=ServiceLifetime.SCOPED
        )
        self._services[service_type] = descriptor
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """Register a service instance."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        return self
    
    def register_factory(
        self, 
        service_type: Type[T], 
        factory: Callable[..., T], 
        lifetime: str = ServiceLifetime.TRANSIENT
    ) -> 'ServiceContainer':
        """Register a service factory."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        return self
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        
        # Handle singleton lifetime
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = self._create_instance(descriptor)
            self._singletons[service_type] = instance
            return instance
        
        # Handle scoped lifetime
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if service_type in self._scoped_instances:
                return self._scoped_instances[service_type]
            
            instance = self._create_instance(descriptor)
            self._scoped_instances[service_type] = instance
            return instance
        
        # Handle transient lifetime
        else:
            return self._create_instance(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance."""
        # Use existing instance
        if descriptor.instance is not None:
            return descriptor.instance
        
        # Use factory
        if descriptor.factory is not None:
            return self._invoke_with_dependencies(descriptor.factory)
        
        # Use implementation
        if descriptor.implementation is not None:
            return self._invoke_with_dependencies(descriptor.implementation)
        
        raise ValueError("Cannot create instance: no implementation, factory, or instance provided")
    
    def _invoke_with_dependencies(self, callable_obj: Callable) -> Any:
        """Invoke a callable with dependency injection."""
        if inspect.isclass(callable_obj):
            # Get constructor signature
            signature = inspect.signature(callable_obj.__init__)
            parameters = list(signature.parameters.values())[1:]  # Skip 'self'
        else:
            # Get function signature
            signature = inspect.signature(callable_obj)
            parameters = list(signature.parameters.values())
        
        # Resolve dependencies
        kwargs = {}
        for param in parameters:
            if param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param.name] = self.resolve(param.annotation)
                except ValueError:
                    # If dependency cannot be resolved and has default value, skip it
                    if param.default == inspect.Parameter.empty:
                        raise ValueError(f"Cannot resolve dependency {param.annotation.__name__} for parameter {param.name}")
        
        return callable_obj(**kwargs)
    
    def clear_scoped(self):
        """Clear scoped instances."""
        self._scoped_instances.clear()
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service is registered."""
        return service_type in self._services


# Global container instance
container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the global service container."""
    return container


def inject(service_type: Type[T]) -> T:
    """Dependency injection decorator for FastAPI dependencies."""
    def dependency():
        return container.resolve(service_type)
    return dependency


def service(lifetime: str = ServiceLifetime.TRANSIENT):
    """Decorator to automatically register a service."""
    def decorator(cls):
        if lifetime == ServiceLifetime.SINGLETON:
            container.register_singleton(cls)
        elif lifetime == ServiceLifetime.SCOPED:
            container.register_scoped(cls)
        else:
            container.register_transient(cls)
        return cls
    return decorator