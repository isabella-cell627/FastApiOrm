"""
Model Hooks and Signals System

Provides extensible hooks for model lifecycle events:
- pre_save: Before creating or updating a record
- post_save: After creating or updating a record
- pre_delete: Before deleting a record
- post_delete: After deleting a record

Example:
    class User(Model):
        __tablename__ = "users"
        
        username: str = StringField(max_length=100)
        
        @classmethod
        async def pre_save_hook(cls, instance, **kwargs):
            # Called before save
            print(f"About to save user: {instance.username}")
        
        @classmethod
        async def post_save_hook(cls, instance, created, **kwargs):
            # Called after save
            if created:
                print(f"Created new user: {instance.username}")
            else:
                print(f"Updated user: {instance.username}")
"""

from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import asyncio
from functools import wraps

if TYPE_CHECKING:
    from fastapi_orm.model import Model
    from sqlalchemy.ext.asyncio import AsyncSession


class Signal:
    """
    A signal that can have multiple handlers attached.
    Handlers are called in order when the signal is sent.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._handlers: List[Callable] = []
    
    def connect(self, handler: Callable) -> None:
        """Connect a handler to this signal."""
        if handler not in self._handlers:
            self._handlers.append(handler)
    
    def disconnect(self, handler: Callable) -> None:
        """Disconnect a handler from this signal."""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    async def send(self, sender: type, instance: Any, **kwargs) -> None:
        """Send the signal to all connected handlers."""
        for handler in self._handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(sender, instance, **kwargs)
            else:
                handler(sender, instance, **kwargs)


class ModelSignals:
    """Container for all model lifecycle signals."""
    
    def __init__(self):
        self.pre_save = Signal("pre_save")
        self.post_save = Signal("post_save")
        self.pre_delete = Signal("pre_delete")
        self.post_delete = Signal("post_delete")
        self.pre_update = Signal("pre_update")
        self.post_update = Signal("post_update")


# Global signal manager
_signals = ModelSignals()


def get_signals() -> ModelSignals:
    """Get the global signals instance."""
    return _signals


class HooksMixin:
    """
    Mixin that provides hook methods for model lifecycle events.
    Models can override these methods to add custom behavior.
    """
    
    @classmethod
    async def pre_save_hook(cls, instance: "Model", **kwargs) -> None:
        """
        Called before an instance is saved (created or updated).
        
        Args:
            instance: The model instance being saved
            **kwargs: Additional context (e.g., 'created' boolean)
        """
        pass
    
    @classmethod
    async def post_save_hook(cls, instance: "Model", created: bool = False, **kwargs) -> None:
        """
        Called after an instance is saved.
        
        Args:
            instance: The model instance that was saved
            created: True if this was a create operation, False if update
            **kwargs: Additional context
        """
        pass
    
    @classmethod
    async def pre_update_hook(cls, instance: "Model", **kwargs) -> None:
        """
        Called before an instance is updated.
        
        Args:
            instance: The model instance being updated
            **kwargs: Additional context (e.g., update fields)
        """
        pass
    
    @classmethod
    async def post_update_hook(cls, instance: "Model", **kwargs) -> None:
        """
        Called after an instance is updated.
        
        Args:
            instance: The model instance that was updated
            **kwargs: Additional context
        """
        pass
    
    @classmethod
    async def pre_delete_hook(cls, instance: "Model", **kwargs) -> None:
        """
        Called before an instance is deleted.
        
        Args:
            instance: The model instance being deleted
            **kwargs: Additional context
        """
        pass
    
    @classmethod
    async def post_delete_hook(cls, instance: "Model", **kwargs) -> None:
        """
        Called after an instance is deleted.
        
        Args:
            instance: The model instance that was deleted
            **kwargs: Additional context
        """
        pass


async def trigger_pre_save(sender: type, instance: "Model", **kwargs) -> None:
    """Trigger pre_save hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'pre_save') and callable(getattr(instance, 'pre_save')):
        method = getattr(instance, 'pre_save')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'))
    
    # Call class hook method
    if hasattr(sender, 'pre_save_hook'):
        await sender.pre_save_hook(instance, **kwargs)
    
    # Send global signal
    await _signals.pre_save.send(sender, instance, **kwargs)


async def trigger_post_save(sender: type, instance: "Model", created: bool = False, **kwargs) -> None:
    """Trigger post_save hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'post_save') and callable(getattr(instance, 'post_save')):
        method = getattr(instance, 'post_save')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'), created)
    
    # Call class hook method
    if hasattr(sender, 'post_save_hook'):
        await sender.post_save_hook(instance, created=created, **kwargs)
    
    # Send global signal
    await _signals.post_save.send(sender, instance, created=created, **kwargs)


async def trigger_pre_update(sender: type, instance: "Model", **kwargs) -> None:
    """Trigger pre_update hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'pre_update') and callable(getattr(instance, 'pre_update')):
        method = getattr(instance, 'pre_update')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'))
    
    # Call class hook method
    if hasattr(sender, 'pre_update_hook'):
        await sender.pre_update_hook(instance, **kwargs)
    
    # Send global signal
    await _signals.pre_update.send(sender, instance, **kwargs)


async def trigger_post_update(sender: type, instance: "Model", **kwargs) -> None:
    """Trigger post_update hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'post_update') and callable(getattr(instance, 'post_update')):
        method = getattr(instance, 'post_update')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'))
    
    # Call class hook method
    if hasattr(sender, 'post_update_hook'):
        await sender.post_update_hook(instance, **kwargs)
    
    # Send global signal
    await _signals.post_update.send(sender, instance, **kwargs)


async def trigger_pre_delete(sender: type, instance: "Model", **kwargs) -> None:
    """Trigger pre_delete hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'pre_delete') and callable(getattr(instance, 'pre_delete')):
        method = getattr(instance, 'pre_delete')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'))
    
    # Call class hook method
    if hasattr(sender, 'pre_delete_hook'):
        await sender.pre_delete_hook(instance, **kwargs)
    
    # Send global signal
    await _signals.pre_delete.send(sender, instance, **kwargs)


async def trigger_post_delete(sender: type, instance: "Model", **kwargs) -> None:
    """Trigger post_delete hooks and signals."""
    # Call instance hook method if exists
    if hasattr(instance, 'post_delete') and callable(getattr(instance, 'post_delete')):
        method = getattr(instance, 'post_delete')
        if asyncio.iscoroutinefunction(method):
            await method(kwargs.get('session'))
    
    # Call class hook method
    if hasattr(sender, 'post_delete_hook'):
        await sender.post_delete_hook(instance, **kwargs)
    
    # Send global signal
    await _signals.post_delete.send(sender, instance, **kwargs)


def receiver(signal: Signal, sender: Optional[type] = None):
    """
    Decorator to connect a function to a signal.
    
    Args:
        signal: The signal to connect to
        sender: Optional model class to filter signals from
    
    Example:
        @receiver(signals.post_save, sender=User)
        async def user_saved_handler(sender, instance, created, **kwargs):
            if created:
                print(f"New user created: {instance.username}")
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(signal_sender: type, instance: Any, **kwargs):
            if sender is None or signal_sender is sender:
                if asyncio.iscoroutinefunction(func):
                    await func(signal_sender, instance, **kwargs)
                else:
                    func(signal_sender, instance, **kwargs)
        
        signal.connect(wrapper)
        return func
    
    return decorator
