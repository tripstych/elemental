"""
Core game logic modules - no pygame dependencies.
"""

from .alchemy import AlchemySystem, SOLVENTS, COAGULANTS, MATERIAL_ESSENCES
from .events import EventBus, EventType, GameEvent, get_event_bus
from .controller import GameController, ActionResult
