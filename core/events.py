"""
Event System - Decouples game logic from UI.

The game emits events, the UI subscribes to them.
This allows swapping UI frameworks without touching game logic.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any
from enum import Enum, auto


class EventType(Enum):
    """All game event types"""
    # Player events
    PLAYER_MOVED = auto()
    PLAYER_ATTACKED = auto()
    PLAYER_DAMAGED = auto()
    PLAYER_HEALED = auto()
    PLAYER_DIED = auto()
    PLAYER_LEVELED_UP = auto()

    # Combat events
    ATTACK_HIT = auto()
    ATTACK_MISSED = auto()
    MONSTER_DIED = auto()
    SPELL_CAST = auto()
    SPELL_FAILED = auto()

    # Alchemy events
    MEDITATION_COMPLETE = auto()
    MEDITATION_FAILED = auto()
    DISSOLUTION_COMPLETE = auto()
    DISSOLUTION_FAILED = auto()
    TRANSMUTATION_SUCCESS = auto()
    TRANSMUTATION_FAILED = auto()

    # Inventory events
    ITEM_PICKED_UP = auto()
    ITEM_DROPPED = auto()
    ITEM_USED = auto()
    ESSENCE_GAINED = auto()
    ESSENCE_SPENT = auto()

    # World events
    MONSTER_SPAWNED = auto()
    ITEM_SPAWNED = auto()
    LEVEL_CHANGED = auto()

    # UI events (game -> UI)
    MESSAGE = auto()
    MODE_CHANGED = auto()


@dataclass
class GameEvent:
    """A single game event with associated data"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class EventBus:
    """
    Central event bus for game-UI communication.

    Usage:
        bus = EventBus()

        # Subscribe to events
        bus.subscribe(EventType.PLAYER_DAMAGED, my_handler)

        # Emit events
        bus.emit(EventType.PLAYER_DAMAGED, {'amount': 10, 'source': 'Goblin'})

        # Or emit with a message
        bus.emit_message("You took 10 damage from Goblin!")
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._global_subscribers: List[Callable] = []
        self._message_log: List[str] = []
        self._max_messages = 100

    def subscribe(self, event_type: EventType, handler: Callable[[GameEvent], None]):
        """Subscribe to a specific event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[GameEvent], None]):
        """Subscribe to all events"""
        self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def emit(self, event_type: EventType, data: Dict[str, Any] = None, message: str = ""):
        """Emit an event to all subscribers"""
        event = GameEvent(
            type=event_type,
            data=data or {},
            message=message
        )

        # Call specific subscribers
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                handler(event)

        # Call global subscribers
        for handler in self._global_subscribers:
            handler(event)

        # Log messages
        if message:
            self._message_log.append(message)
            if len(self._message_log) > self._max_messages:
                self._message_log.pop(0)

    def emit_message(self, message: str):
        """Convenience method to emit a message event"""
        self.emit(EventType.MESSAGE, {'text': message}, message)

    def get_messages(self, count: int = 10) -> List[str]:
        """Get recent messages"""
        return self._message_log[-count:]

    def clear_messages(self):
        """Clear message log"""
        self._message_log.clear()


# Global event bus instance (can be replaced for testing)
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """Get the global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(bus: EventBus):
    """Set the global event bus (for testing)"""
    global _event_bus
    _event_bus = bus
