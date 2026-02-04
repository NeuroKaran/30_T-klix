"""
Klix Core - Hooks System
Event-driven lifecycle hooks for extensibility.
Allows plugins and skills to respond to agent events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable
from uuid import uuid4

from logging_config import get_logger

logger = get_logger(__name__)


class HookEvent(Enum):
    """Lifecycle events that can be hooked into."""
    
    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    
    # Message events
    USER_INPUT = "user_input"
    ASSISTANT_RESPONSE = "assistant_response"
    
    # Tool events
    TOOL_CALL_BEFORE = "tool_call_before"
    TOOL_CALL_AFTER = "tool_call_after"
    TOOL_CALL_ERROR = "tool_call_error"
    
    # Planning events
    PLAN_CREATED = "plan_created"
    PLAN_STEP_START = "plan_step_start"
    PLAN_STEP_COMPLETE = "plan_step_complete"
    PLAN_COMPLETE = "plan_complete"
    
    # Memory events
    MEMORY_SEARCH = "memory_search"
    MEMORY_STORE = "memory_store"
    
    # Error events
    ERROR = "error"


# Type alias for hook callbacks
HookCallback = Callable[[HookEvent, dict[str, Any]], Awaitable[dict[str, Any] | None]]


@dataclass
class Hook:
    """Represents a registered hook."""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    event: HookEvent = HookEvent.ERROR
    callback: HookCallback | None = None
    name: str = ""
    priority: int = 100  # Lower = earlier execution
    enabled: bool = True
    
    def __post_init__(self) -> None:
        if not self.name:
            self.name = f"hook_{self.event.value}_{self.id}"


@dataclass
class HookManager:
    """
    Manages lifecycle hooks for the agent.
    
    Hooks can:
    - Observe events (logging, analytics)
    - Modify event data (transform inputs/outputs)
    - Block actions (approval, validation)
    """
    
    hooks: dict[HookEvent, list[Hook]] = field(default_factory=dict)
    
    def register(
        self,
        event: HookEvent,
        callback: HookCallback,
        name: str = "",
        priority: int = 100,
    ) -> Hook:
        """Register a hook for an event."""
        hook = Hook(
            event=event,
            callback=callback,
            name=name,
            priority=priority,
        )
        
        if event not in self.hooks:
            self.hooks[event] = []
        
        self.hooks[event].append(hook)
        # Sort by priority
        self.hooks[event].sort(key=lambda h: h.priority)
        
        logger.debug(f"Registered hook: {hook.name} for {event.value}")
        return hook
    
    def unregister(self, hook_id: str) -> bool:
        """Unregister a hook by ID."""
        for event, hooks in self.hooks.items():
            for i, hook in enumerate(hooks):
                if hook.id == hook_id:
                    del hooks[i]
                    logger.debug(f"Unregistered hook: {hook.name}")
                    return True
        return False
    
    def unregister_by_name(self, name: str) -> int:
        """Unregister all hooks with a given name."""
        count = 0
        for event in self.hooks:
            original_len = len(self.hooks[event])
            self.hooks[event] = [h for h in self.hooks[event] if h.name != name]
            count += original_len - len(self.hooks[event])
        return count
    
    async def trigger(
        self,
        event: HookEvent,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger an event and run all registered hooks.
        
        Hooks are executed in priority order. Each hook can:
        - Return None to pass through unchanged
        - Return modified data dict
        - Raise an exception to block the action
        
        Returns the (potentially modified) data.
        """
        data = data or {}
        
        if event not in self.hooks:
            return data
        
        for hook in self.hooks[event]:
            if not hook.enabled or not hook.callback:
                continue
            
            try:
                result = await hook.callback(event, data.copy())
                if result is not None:
                    data = result
            except Exception as e:
                logger.error(f"Hook {hook.name} failed: {e}")
                # Re-raise if it's a blocking exception
                if isinstance(e, HookBlockError):
                    raise
        
        return data
    
    def get_hooks(self, event: HookEvent | None = None) -> list[Hook]:
        """Get all registered hooks, optionally filtered by event."""
        if event:
            return self.hooks.get(event, [])
        
        all_hooks = []
        for hooks in self.hooks.values():
            all_hooks.extend(hooks)
        return all_hooks
    
    def clear(self) -> None:
        """Clear all registered hooks."""
        self.hooks.clear()


class HookBlockError(Exception):
    """Raised by a hook to block an action."""
    pass


# Global hook manager instance
_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """Get or create the global HookManager instance."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def on(event: HookEvent, name: str = "", priority: int = 100):
    """
    Decorator to register a hook function.
    
    Usage:
        @on(HookEvent.USER_INPUT)
        async def my_hook(event, data):
            print(f"User said: {data.get('input')}")
            return data
    """
    def decorator(func: HookCallback) -> HookCallback:
        get_hook_manager().register(event, func, name or func.__name__, priority)
        return func
    return decorator


async def trigger(event: HookEvent, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Trigger an event (convenience function)."""
    return await get_hook_manager().trigger(event, data)


# Common hook helpers
def create_logging_hook(event: HookEvent, message_template: str = "") -> Hook:
    """Create a simple logging hook."""
    async def log_hook(ev: HookEvent, data: dict[str, Any]) -> None:
        msg = message_template.format(**data) if message_template else f"{ev.value}: {data}"
        logger.info(msg)
        return None
    
    return get_hook_manager().register(event, log_hook, f"logger_{event.value}")
