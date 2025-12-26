"""
Core game modules - pure game logic separated from UI.
"""

from .controller import GameController, ActionResult
from .alchemy import AlchemySystem, AlchemyResult, SpellBookEntry, Essence
from .events import EventBus, EventType, GameEvent, get_event_bus
