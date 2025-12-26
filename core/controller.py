"""
Game Controller - Central facade for all game systems.

This provides a clean API for the UI layer to interact with game logic.
The UI calls controller methods, the controller coordinates between systems.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import random

from .alchemy import AlchemySystem, AlchemyResult, SpellBookEntry, SOLVENTS, COAGULANTS
from .vector_engine import VectorEngine, CastResult
from .events import EventBus, EventType, get_event_bus
from constants import VIAL_SIZES


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
        self.vector_engine = VectorEngine()
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
            ActionResult with success status and movement data
        """
        if not self.player:
            return ActionResult(False, "No player")

        new_x = self.player.x + dx
        new_y = self.player.y + dy
        direction = {(0,-1): 'n', (0,1): 's', (1,0): 'e', (-1,0): 'w'}.get((dx, dy), '?')

        # Check for entity blocking movement
        entity = self.world.get_entity_at(new_x, new_y) if self.world else None
        if entity and entity != self.player:
            return ActionResult(False, "Blocked by entity", {'entity': entity})

        # Check bounds and walkability
        if not self._is_walkable(new_x, new_y):
            return ActionResult(False, "Can't move there")

        # Move
        self.player.x = new_x
        self.player.y = new_y

        self.events.emit(EventType.PLAYER_MOVED, {
            'x': new_x, 'y': new_y, 'dx': dx, 'dy': dy
        })

        # Check for items at new position
        items_here = []
        if self.world and (new_x, new_y) in self.world.items_on_ground:
            items_here = self.world.items_on_ground[(new_x, new_y)]

        # Check for exit tile
        is_exit = False
        if self.world:
            from seed.dungeon_generator import DungeonGenerator
            if self.world.dungeon.grid[new_y, new_x] == DungeonGenerator.EXIT:
                is_exit = True

        return ActionResult(True, "Moved", {
            'x': new_x,
            'y': new_y,
            'direction': direction,
            'items_here': items_here,
            'is_exit': is_exit
        })

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
        Attack a target entity using player's attack method.

        Args:
            target: Monster or entity to attack

        Returns:
            ActionResult with damage info
        """
        if not self.player:
            return ActionResult(False, "No player")

        if not target.stats.is_alive():
            return ActionResult(False, "Target already dead")

        # Use player's attack method (handles damage calculation)
        result = self.player.attack(target)

        if result['success']:
            # Calculate direction for UI
            dx = target.x - self.player.x
            dy = target.y - self.player.y
            direction = {(0,-1):'n', (1,-1):'ne', (1,0):'e', (1,1):'se',
                        (0,1):'s', (-1,1):'sw', (-1,0):'w', (-1,-1):'nw'}.get((dx, dy), '?')

            self.events.emit(EventType.ATTACK_HIT, {
                'attacker': self.player,
                'target': target,
                'damage': result['damage']
            })

            killed = not result['target_alive']
            if killed:
                self.events.emit(EventType.MONSTER_DIED, {'monster': target})

            return ActionResult(True, f"Hit {target.name}!", {
                'damage': result['damage'],
                'killed': killed,
                'direction': direction,
                'target_hp': f"{target.stats.current_health}/{target.stats.max_health}"
            })
        else:
            return ActionResult(False, "Attack failed")

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
    # SPOKEN SPELLS (Vector Engine)
    # -------------------------------------------------------------------------

    def speak_spell(self, phrase: str, target_item: Dict) -> ActionResult:
        """
        Speak a spell using elemental syllables to transform an item.

        Args:
            phrase: Space-separated syllables (e.g., "OOM SHII KRAK")
            target_item: Item dict to transform

        Returns:
            ActionResult with transformation outcome and burn damage if any
        """
        if not self.player:
            return ActionResult(False, "No player")

        if not target_item:
            return ActionResult(False, "No target item selected")

        # Get player stats for load calculation
        # Use player's intelligence/willpower as conduit limit
        conduit_limit = getattr(self.player.stats, 'conduit_limit', 100)
        if conduit_limit == 100:
            # Fallback: derive from wisdom or intelligence
            wisdom = getattr(self.player.stats, 'wisdom', 10)
            conduit_limit = 50 + wisdom * 10

        current_hp = self.player.stats.current_health

        # Cast the spell through vector engine
        result = self.vector_engine.cast(
            phrase=phrase,
            item=target_item,
            caster_conduit=conduit_limit,
            caster_hp=current_hp
        )

        # Apply burn damage if any
        if result.burn_damage > 0:
            self.player.stats.current_health -= result.burn_damage
            self.events.emit(EventType.PLAYER_DAMAGED, {
                'source': 'spell_overload',
                'damage': result.burn_damage
            })

            if not self.player.stats.is_alive():
                self.events.emit(EventType.PLAYER_DIED, {'killer': 'spell_overload'})

        # Update item with new stats if successful
        if result.success and result.item_after:
            for key, value in result.item_after.items():
                target_item[key] = value

        self.add_message(result.message)
        return ActionResult(
            success=result.success,
            message=result.message,
            data={
                'load': result.load,
                'overload': result.overload,
                'burn_damage': result.burn_damage,
                'vectors': result.vectors,
                'item_before': result.item_before,
                'item_after': result.item_after
            }
        )

    def get_elemental_syllables(self, element: str = None) -> List[Dict]:
        """
        Get available syllables for spell speaking.

        Args:
            element: Optional filter by element (fire/water/earth/air)

        Returns:
            List of syllable dicts with spelling, value, quality
        """
        if element:
            return self.vector_engine.get_syllables_for_element(element)

        # Return all syllables organized by element
        all_syllables = []
        for elem in self.vector_engine.get_all_elements():
            for syl in self.vector_engine.get_syllables_for_element(elem):
                syl_copy = syl.copy()
                syl_copy['element'] = elem
                all_syllables.append(syl_copy)
        return all_syllables

    def parse_spoken_phrase(self, phrase: str) -> Dict:
        """
        Parse a phrase without casting it (for preview).

        Args:
            phrase: Space-separated syllables

        Returns:
            Dict with vectors, total_strain, total_power, unknown_words
        """
        parsed = self.vector_engine.parse_phrase(phrase)
        return {
            'phrase': parsed.phrase,
            'words': parsed.words,
            'vectors': parsed.vectors,
            'total_strain': parsed.total_strain,  # Absolute cost
            'total_power': parsed.total_power,    # Signed net effect
            'unknown_words': parsed.unknown_words,
            'dominant_element': parsed.dominant_element
        }

    def calculate_spell_load(self, phrase: str, item_weight: float) -> float:
        """
        Calculate the load for a phrase on an item.

        Args:
            phrase: The spoken syllables
            item_weight: Weight of target item

        Returns:
            Calculated load value
        """
        parsed = self.vector_engine.parse_phrase(phrase)
        return self.vector_engine.calculate_load(parsed, item_weight)

    def get_player_conduit_limit(self) -> int:
        """Get the player's current conduit limit (max safe load)"""
        if not self.player:
            return 100
        conduit_limit = getattr(self.player.stats, 'conduit_limit', 100)
        if conduit_limit == 100:
            wisdom = getattr(self.player.stats, 'wisdom', 10)
            conduit_limit = 50 + wisdom * 10
        return conduit_limit

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
            return ActionResult(True, f"Picked up: {names}", {'items': picked})
        else:
            return ActionResult(False, "Inventory full")

    def drop_item(self, index: int) -> ActionResult:
        """
        Drop an inventory item to the ground.

        Args:
            index: Index of item in inventory

        Returns:
            ActionResult with dropped item info
        """
        if not self.player:
            return ActionResult(False, "No player")

        items = self.inventory.objects
        if index >= len(items):
            return ActionResult(False, "No item at that slot")

        item = items[index]

        # Remove from inventory
        self.inventory.objects.pop(index)

        # Add to ground at player position
        pos = (self.player.x, self.player.y)
        if pos not in self.world.items_on_ground:
            self.world.items_on_ground[pos] = []
        self.world.items_on_ground[pos].append(item)

        self.events.emit(EventType.ITEM_DROPPED, {'item': item, 'position': pos})

        return ActionResult(True, f"Dropped {item['name']}", {
            'item': item,
            'position': pos
        })

    # -------------------------------------------------------------------------
    # GAME FLOW
    # -------------------------------------------------------------------------

    def end_turn(self):
        """
        End player turn and run monster turns.
        """
        self.events.emit(EventType.MODE_CHANGED, {'mode': 'monster_turn'})
        return self.process_monster_turns()

    def process_monster_turns(self) -> List[ActionResult]:
        """
        Process AI for all monsters.

        Returns:
            List of ActionResults for monster actions (attacks, movements)
        """
        if not self.player or not self.world:
            return []

        results = []
        player = self.player

        for monster in self.monsters:
            if not monster.stats.is_alive():
                continue

            dist = monster.distance_to(player)

            # If adjacent, attack
            if dist <= 1.5:
                attack_result = monster.attack(player)
                if attack_result['success']:
                    self.events.emit(EventType.PLAYER_DAMAGED, {
                        'attacker': monster,
                        'damage': attack_result['damage']
                    })

                    results.append(ActionResult(
                        True,
                        f"{monster.name} hits you for {attack_result['damage']} damage!",
                        {
                            'monster': monster.name,
                            'damage': attack_result['damage'],
                            'player_alive': player.stats.is_alive()
                        }
                    ))

                    if not player.stats.is_alive():
                        self.events.emit(EventType.PLAYER_DIED, {'killer': monster})

            # If close, move toward player
            elif dist < 10:
                dx = 1 if player.x > monster.x else -1 if player.x < monster.x else 0
                dy = 1 if player.y > monster.y else -1 if player.y < monster.y else 0

                new_x, new_y = monster.x + dx, monster.y + dy

                # Check if position is walkable and not blocked
                if self.world.is_walkable(new_x, new_y):
                    blocking_entity = self.world.get_entity_at(new_x, new_y)
                    if not blocking_entity:
                        monster.x = new_x
                        monster.y = new_y

        return results

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

    # -------------------------------------------------------------------------
    # SPAWNING
    # -------------------------------------------------------------------------

    def spawn_solvents(self, count: int):
        """Spawn solvent items in the dungeon with random vial sizes"""
        if not self.world:
            return

        from seed.dungeon_generator import DungeonGenerator

        solvent_keys = list(SOLVENTS.keys())

        # Weighted vial size distribution (smaller vials more common)
        vial_weights = [
            ("tiny", 30),
            ("small", 35),
            ("medium", 20),
            ("large", 10),
            ("grand", 5),
        ]
        vial_pool = []
        for vial_key, weight in vial_weights:
            vial_pool.extend([vial_key] * weight)

        floors = (self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) +
                  self.world.dungeon.find_positions(DungeonGenerator.CORRIDOR))

        for _ in range(count):
            if not floors:
                break
            pos = random.choice(floors)
            solvent_key = random.choice(solvent_keys)
            vial_key = random.choice(vial_pool)

            solvent_data = SOLVENTS[solvent_key]
            vial_data = VIAL_SIZES[vial_key]

            solvent_item = {
                'name': f"{vial_data['name']} of {solvent_data['name']}",
                'type': 'solvent',
                'is_solvent': True,
                'solvent_type': solvent_key,
                'vial_size': vial_key,
                'quantity': vial_data['volume'],
                'max_quantity': vial_data['volume'],
                'description': f"{solvent_data['description']} ({vial_data['volume']}ml)",
                'weight': vial_data['weight'],
            }

            if pos not in self.world.items_on_ground:
                self.world.items_on_ground[pos] = []
            self.world.items_on_ground[pos].append(solvent_item)

    def spawn_coagulants(self, count: int):
        """Spawn coagulant items in the dungeon with random vial sizes"""
        if not self.world:
            return

        from seed.dungeon_generator import DungeonGenerator

        coagulant_keys = list(COAGULANTS.keys())

        # Weighted vial size distribution (smaller vials more common)
        vial_weights = [
            ("tiny", 30),
            ("small", 35),
            ("medium", 20),
            ("large", 10),
            ("grand", 5),
        ]
        vial_pool = []
        for vial_key, weight in vial_weights:
            vial_pool.extend([vial_key] * weight)

        floors = (self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) +
                  self.world.dungeon.find_positions(DungeonGenerator.CORRIDOR))

        for _ in range(count):
            if not floors:
                break
            pos = random.choice(floors)
            coagulant_key = random.choice(coagulant_keys)
            vial_key = random.choice(vial_pool)

            coagulant_data = COAGULANTS[coagulant_key]
            vial_data = VIAL_SIZES[vial_key]

            coagulant_item = {
                'name': f"{vial_data['name']} of {coagulant_data['name']}",
                'type': 'coagulant',
                'is_coagulant': True,
                'coagulant_type': coagulant_key,
                'vial_size': vial_key,
                'quantity': vial_data['volume'],
                'max_quantity': vial_data['volume'],
                'description': f"{coagulant_data['description']} ({vial_data['volume']}ml)",
                'weight': vial_data['weight'],
            }

            if pos not in self.world.items_on_ground:
                self.world.items_on_ground[pos] = []
            self.world.items_on_ground[pos].append(coagulant_item)
