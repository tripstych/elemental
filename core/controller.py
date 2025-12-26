"""
Game Controller - Central facade for all game systems.

This provides a clean API for the UI layer to interact with game logic.
The UI calls controller methods, the controller coordinates between systems.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from .alchemy import AlchemySystem, AlchemyResult, SpellBookEntry
from .events import EventBus, EventType, get_event_bus


@dataclass
class ActionResult:
    """Result of any game action"""
    success: bool
    message: str
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class GameController:
    """
    Central controller that coordinates all game systems.

    The UI layer should only interact with this class, not directly
    with individual systems. This provides a clean API boundary and
    makes it easy to swap UI implementations.

    Usage:
        controller = GameController(world)

        # UI calls these methods
        result = controller.move_player(1, 0)
        result = controller.attack_target(monster)
        result = controller.meditate_on_item(item)
        result = controller.transmute(item, solvent, ...)

        # Controller emits events that UI can subscribe to
        controller.events.subscribe(EventType.PLAYER_DAMAGED, handler)
    """

    def __init__(self, world=None):
        """
        Initialize the controller with a game world.

        Args:
            world: GameWorld instance (from game.py), or None for testing
        """
        self.world = world
        self.alchemy = AlchemySystem()
        self.events = get_event_bus()

        # Message log for UI
        self._messages: List[str] = []
        self._max_messages = 50

    # -------------------------------------------------------------------------
    # PROPERTIES - Read game state
    # -------------------------------------------------------------------------

    @property
    def player(self):
        """Get the player entity"""
        return self.world.player if self.world else None

    @property
    def inventory(self):
        """Get player inventory"""
        return self.player.inventory if self.player else None

    @property
    def monsters(self):
        """Get all monsters"""
        return self.world.monsters if self.world else []

    def get_items(self) -> List[Dict]:
        """Get regular items from inventory (not solvents/coagulants)"""
        if not self.inventory:
            return []
        return [obj for obj in self.inventory.objects
                if not obj.get('is_solvent') and not obj.get('is_coagulant')]

    def get_solvents(self) -> List[Dict]:
        """Get solvents from inventory"""
        if not self.inventory:
            return []
        return [obj for obj in self.inventory.objects if obj.get('is_solvent')]

    def get_coagulants(self) -> List[Dict]:
        """Get coagulants from inventory"""
        if not self.inventory:
            return []
        return [obj for obj in self.inventory.objects if obj.get('is_coagulant')]

    def get_known_essences(self) -> List[SpellBookEntry]:
        """Get all known essence patterns from spell book"""
        return self.alchemy.get_known_essences()

    def get_essence_for_item(self, item: Dict) -> Optional[Dict[str, float]]:
        """Get known essence for an item, if we've meditated on it"""
        return self.alchemy.get_essence_for_item(item)

    # -------------------------------------------------------------------------
    # MESSAGES
    # -------------------------------------------------------------------------

    def add_message(self, message: str):
        """Add a message to the log"""
        self._messages.append(message)
        if len(self._messages) > self._max_messages:
            self._messages.pop(0)
        self.events.emit_message(message)

    def get_messages(self, count: int = 10) -> List[str]:
        """Get recent messages"""
        return self._messages[-count:]

    # -------------------------------------------------------------------------
    # MOVEMENT
    # -------------------------------------------------------------------------

    def move_player(self, dx: int, dy: int) -> ActionResult:
        """
        Move the player by delta.

        Returns:
            ActionResult with success status
        """
        if not self.player:
            return ActionResult(False, "No player")

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Check bounds and walkability
        if not self._is_walkable(new_x, new_y):
            return ActionResult(False, "Can't move there")

        # Check for monsters blocking
        for m in self.monsters:
            if m.x == new_x and m.y == new_y and m.stats.is_alive():
                return ActionResult(False, "Monster blocking", {'monster': m})

        # Move
        self.player.x = new_x
        self.player.y = new_y

        self.events.emit(EventType.PLAYER_MOVED, {
            'x': new_x, 'y': new_y, 'dx': dx, 'dy': dy
        })

        return ActionResult(True, "Moved")

    def _is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable"""
        if not self.world:
            return False
        if x < 0 or y < 0 or x >= self.world.width or y >= self.world.height:
            return False
        tile = self.world.dungeon.grid[y, x]
        return tile in self.world.walkable_tiles

    # -------------------------------------------------------------------------
    # COMBAT
    # -------------------------------------------------------------------------

    def attack(self, target) -> ActionResult:
        """
        Attack a target entity.

        Args:
            target: Monster or entity to attack

        Returns:
            ActionResult with damage info
        """
        if not self.player:
            return ActionResult(False, "No player")

        if not target.stats.is_alive():
            return ActionResult(False, "Target already dead")

        # Calculate damage
        attack_power = self.player.stats.attack_power
        defense = target.stats.defense
        damage = max(1, attack_power - defense // 2)

        # Apply damage
        target.stats.take_damage(damage)

        self.events.emit(EventType.ATTACK_HIT, {
            'attacker': self.player,
            'target': target,
            'damage': damage
        })

        message = f"Hit {target.name} for {damage} damage!"

        if not target.stats.is_alive():
            self.events.emit(EventType.MONSTER_DIED, {'monster': target})
            message += f" {target.name} defeated!"

        self.add_message(message)
        return ActionResult(True, message, {'damage': damage, 'killed': not target.stats.is_alive()})

    def cast_spell(self, spell_name: str, target=None) -> ActionResult:
        """
        Cast a spell.

        Args:
            spell_name: Name of spell to cast
            target: Optional target for targeted spells

        Returns:
            ActionResult with spell effect info
        """
        if not self.player:
            return ActionResult(False, "No player")

        # Check if player knows the spell
        castable = self.alchemy.get_castable_spells()
        spell = None
        for s in castable:
            if s.name.lower() == spell_name.lower():
                spell = s
                break

        if not spell:
            return ActionResult(False, f"Don't know spell: {spell_name}")

        # TODO: Check essence cost, apply effect
        self.events.emit(EventType.SPELL_CAST, {
            'spell': spell_name,
            'target': target
        })

        message = f"Cast {spell_name}!"
        self.add_message(message)
        return ActionResult(True, message)

    # -------------------------------------------------------------------------
    # ALCHEMY
    # -------------------------------------------------------------------------

    def meditate(self, item: Dict) -> ActionResult:
        """
        Meditate on an item to learn its essence.

        Args:
            item: Item dict to meditate on

        Returns:
            ActionResult with essence info if successful
        """
        result = self.alchemy.meditate(item)

        if result.success:
            self.events.emit(EventType.MEDITATION_COMPLETE, result.details)
        else:
            self.events.emit(EventType.MEDITATION_FAILED, {'item': item})

        self.add_message(result.message)
        return ActionResult(result.success, result.message, result.details)

    def dissolve(
        self,
        item: Dict,
        solvent: Dict,
        amount: int = 10
    ) -> ActionResult:
        """
        Dissolve an item to extract essence.

        Args:
            item: Item to dissolve
            solvent: Solvent to use
            amount: Amount of solvent in ml

        Returns:
            ActionResult with extraction info
        """
        result = self.alchemy.dissolve(item, solvent, amount)

        if result.success:
            # Update solvent quantity in inventory
            solvent['quantity'] = result.details.get('solvent_remaining', 0)
            if result.details.get('solvent_empty'):
                self.inventory.objects.remove(solvent)

            self.events.emit(EventType.DISSOLUTION_COMPLETE, result.details)
        else:
            self.events.emit(EventType.DISSOLUTION_FAILED, {'item': item})

        self.add_message(result.message)
        return ActionResult(result.success, result.message, result.details)

    def transmute(
        self,
        item: Dict,
        solvent: Dict,
        solvent_amount: int,
        coagulant: Dict,
        coagulant_amount: int,
        pattern: SpellBookEntry
    ) -> ActionResult:
        """
        Transmute an item using the full alchemy process.

        Args:
            item: Source item
            solvent: Solvent to use
            solvent_amount: Amount of solvent in ml
            coagulant: Coagulant to use
            coagulant_amount: Amount of coagulant in ml
            pattern: Target pattern from spell book

        Returns:
            ActionResult with transmutation outcome
        """
        # Get spell definitions from world if available
        spell_defs = self.world.spells if self.world else None

        result = self.alchemy.transmute(
            item=item,
            solvent=solvent,
            solvent_amount=solvent_amount,
            coagulant=coagulant,
            coagulant_amount=coagulant_amount,
            pattern=pattern,
            spell_defs=spell_defs
        )

        if result.success:
            # Update reagent quantities
            solvent['quantity'] = result.details.get('solvent_remaining', 0)
            coagulant['quantity'] = result.details.get('coagulant_remaining', 0)

            # Remove empty containers
            if result.details.get('solvent_empty') and solvent in self.inventory.objects:
                self.inventory.objects.remove(solvent)
            if result.details.get('coagulant_empty') and coagulant in self.inventory.objects:
                self.inventory.objects.remove(coagulant)

            self.events.emit(EventType.TRANSMUTATION_SUCCESS, result.details)
        else:
            self.events.emit(EventType.TRANSMUTATION_FAILED, result.details)

        self.add_message(result.message)
        return ActionResult(result.success, result.message, result.details)

    # -------------------------------------------------------------------------
    # INVENTORY
    # -------------------------------------------------------------------------

    def pickup_item(self, x: int = None, y: int = None) -> ActionResult:
        """
        Pick up items at position (defaults to player position).

        Returns:
            ActionResult with picked up items
        """
        if not self.player:
            return ActionResult(False, "No player")

        x = x if x is not None else self.player.x
        y = y if y is not None else self.player.y

        if not self.world:
            return ActionResult(False, "No world")

        items = self.world.items_on_ground.get((x, y), [])
        if not items:
            return ActionResult(False, "Nothing to pick up")

        picked = []
        for item in items[:]:
            if self.inventory.add_object(item):
                items.remove(item)
                picked.append(item)
                self.events.emit(EventType.ITEM_PICKED_UP, {'item': item})

        if not items:
            del self.world.items_on_ground[(x, y)]

        if picked:
            names = ", ".join(i.get('name', 'item') for i in picked)
            message = f"Picked up: {names}"
            self.add_message(message)
            return ActionResult(True, message, {'items': picked})
        else:
            return ActionResult(False, "Inventory full")

    # -------------------------------------------------------------------------
    # GAME FLOW
    # -------------------------------------------------------------------------

    def end_turn(self):
        """
        End player turn and run monster turns.
        """
        # TODO: Run monster AI, update world state
        self.events.emit(EventType.MODE_CHANGED, {'mode': 'monster_turn'})

    def get_nearby_monsters(self, radius: int = 10) -> List:
        """Get monsters within radius of player"""
        if not self.player:
            return []

        nearby = []
        for m in self.monsters:
            if not m.stats.is_alive():
                continue
            dist = ((m.x - self.player.x)**2 + (m.y - self.player.y)**2)**0.5
            if dist <= radius:
                nearby.append((m, dist))

        return [m for m, d in sorted(nearby, key=lambda x: x[1])]
