"""
Animate Entity System
Base class for all living/moving entities: Players, NPCs, Monsters, Companions
"""

import json
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field

GOD_MODE = True

if TYPE_CHECKING:
    from pathfinding import Pathfinder

# Import spell casting system
try:
    from spell_casting import cast_spell_full, SpellResult
    HAS_SPELL_CASTING = True
except ImportError:
    HAS_SPELL_CASTING = False
    SpellResult = None


@dataclass
class Inventory:
    """Inventory for carrying objects and essences"""
    
    # Elemental essences
    essences: Dict[str, float] = field(default_factory=lambda: {
        'fire': 0.0,
        'water': 0.0,
        'earth': 0.0,
        'air': 0.0
    })
    
    # Physical objects
    objects: List[Dict] = field(default_factory=list)
    
    # Spell grimoire (known spells by synset)
    grimoire: set = field(default_factory=set)
    
    # Capacity limits
    max_weight: float = 100.0
    max_objects: int = 50
    max_essence: float = 100.0  # Per-element capacity
    
    def add_essence(self, element: str, amount: float) -> float:
        """Add elemental essence, capped at max_essence. Returns amount actually added."""
        if element in self.essences:
            old = self.essences[element]
            self.essences[element] = min(self.essences[element] + amount, self.max_essence)
            return self.essences[element] - old
        return 0.0
    
    def grow_essence_capacity(self, amount: float):
        """Increase max essence capacity (from leveling, items, etc.)"""
        self.max_essence += amount
    
    def remove_essence(self, element: str, amount: float) -> bool:
        """Remove essence if available"""
        if element in self.essences and self.essences[element] >= amount:
            self.essences[element] -= amount
            return True
        return False
    
    def has_essence(self, requirements: Dict[str, float]) -> bool:
        """Check if we have required essences"""
        for element, amount in requirements.items():
            if self.essences.get(element, 0) < amount:
                return False
        return True
    
    def add_object(self, obj: Dict) -> bool:
        """Add object if space available"""
        if len(self.objects) < self.max_objects or GOD_MODE:
            total_weight = sum(o.get('weight', 0) for o in self.objects)
            if total_weight + obj.get('weight', 0) <= self.max_weight or GOD_MODE:
                self.objects.append(obj)
                return True
        return False
    
    def remove_object(self, obj: Dict) -> bool:
        """Remove object from inventory"""
        if obj in self.objects:
            self.objects.remove(obj)
            return True
        return False
    
    def learn_spell(self, synset: str):
        """Add spell to grimoire"""
        self.grimoire.add(synset)
    
    def knows_spell(self, synset: str) -> bool:
        """Check if spell is known"""
        return synset in self.grimoire
    
    def get_total_weight(self) -> float:
        """Get total carried weight"""
        return sum(o.get('weight', 0) for o in self.objects)


@dataclass
class Stats:
    """Character statistics"""
    
    # Core attributes
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Derived stats
    max_health: int = 100
    current_health: int = 100
    max_stamina: int = 100
    current_stamina: int = 100
    
    # Combat
    attack_power: int = 10
    defense: int = 10
    magic_power: int = 10
    magic_defense: int = 10
    
    # Movement
    move_speed: float = 1.0
    
    def is_alive(self) -> bool:
        """Check if entity is alive"""
        return self.current_health > 0
    
    def take_damage(self, amount: int):
        """Reduce health"""
        self.current_health = max(0, self.current_health - amount)
    
    def heal(self, amount: int):
        """Restore health"""
        self.current_health = min(self.max_health, self.current_health + amount)
    
    def use_stamina(self, amount: int) -> bool:
        """Use stamina if available"""
        if self.current_stamina >= amount:
            self.current_stamina -= amount
            return True
        return False
    
    def restore_stamina(self, amount: int):
        """Restore stamina"""
        self.current_stamina = min(self.max_stamina, self.current_stamina + amount)


class Animate:
    """
    Base class for all animate entities
    Players, NPCs, Monsters, Companions all inherit from this
    """
    
    def __init__(self, 
                 name: str,
                 entity_type: str,
                 x: int = 0,
                 y: int = 0,
                 faction: str = 'neutral',
                 **kwargs):
        """
        Args:
            name: Entity name
            entity_type: 'player', 'npc', 'monster', 'companion'
            x, y: Starting position
            faction: 'player', 'enemy', 'neutral', 'ally'
            **kwargs: Additional attributes
        """
        self.name = name
        self.entity_type = entity_type
        self.faction = faction
        
        # Position
        self.x = x
        self.y = y
        self.facing = 'north'  # north, south, east, west
        
        # Components
        self.stats = Stats()
        self.inventory = Inventory()
        
        # Pathfinding
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self.pathfinder: Optional['Pathfinder'] = None  # Set by world/game
        
        # State
        self.is_active = True
        self.is_hostile = (faction == 'enemy')
        
        # AI/Behavior (can be overridden)
        self.ai_state = 'idle'  # idle, patrol, combat, flee, follow
        self.target = None  # Current target entity
        
        # Apply any additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    # ========================================================================
    # MOVEMENT
    # ========================================================================
    
    def set_pathfinder(self, pathfinder: 'Pathfinder'):
        """Set the pathfinder instance for this entity"""
        self.pathfinder = pathfinder
    
    def move_to(self, x: int, y: int, check_collision: bool = True) -> bool:
        """
        Move to position
        
        Args:
            x, y: Target position
            check_collision: Check if position is walkable
            
        Returns:
            True if moved successfully
        """
        if check_collision and self.pathfinder:
            if not self.pathfinder.is_valid_position(x, y):
                return False
        
        # Update facing based on movement
        dx = x - self.x
        dy = y - self.y
        
        if abs(dx) > abs(dy):
            self.facing = 'east' if dx > 0 else 'west'
        elif dy != 0:
            self.facing = 'south' if dy > 0 else 'north'
        
        self.x = x
        self.y = y
        return True
    
    def find_path_to(self, 
                     goal: Tuple[int, int], 
                     algorithm: str = 'astar',
                     allow_diagonal: bool = False,
                     smooth: bool = True) -> bool:
        """
        Find a path to goal position
        
        Args:
            goal: Target (x, y)
            algorithm: 'astar', 'dijkstra', 'bfs', 'greedy'
            allow_diagonal: Allow diagonal movement
            smooth: Smooth the path to remove zigzags
            
        Returns:
            True if path found
        """
        if not self.pathfinder:
            return False
        
        start = (self.x, self.y)
        
        # Choose algorithm
        if algorithm == 'astar':
            path = self.pathfinder.astar(start, goal, allow_diagonal)
        elif algorithm == 'dijkstra':
            path = self.pathfinder.dijkstra(start, goal, allow_diagonal)
        elif algorithm == 'bfs':
            path = self.pathfinder.bfs(start, goal, allow_diagonal)
        elif algorithm == 'greedy':
            path = self.pathfinder.greedy_best_first(start, goal, allow_diagonal)
        else:
            return False
        
        if not path:
            return False
        
        # Smooth path if requested
        if smooth and len(path) > 2:
            path = self.pathfinder.smooth_path(path)
        
        # Store path (skip first point since that's where we are)
        self.current_path = path[1:] if len(path) > 1 else []
        self.path_index = 0
        
        return True
    
    def follow_path(self) -> bool:
        """
        Move one step along current path
        
        Returns:
            True if moved, False if path complete or no path
        """
        if not self.current_path or self.path_index >= len(self.current_path):
            self.current_path = None
            self.path_index = 0
            return False
        
        next_pos = self.current_path[self.path_index]
        if self.move_to(next_pos[0], next_pos[1]):
            self.path_index += 1
            return True
        else:
            # Blocked! Path is invalid
            self.current_path = None
            self.path_index = 0
            return False
    
    def has_path(self) -> bool:
        """Check if entity has a current path"""
        return self.current_path is not None and self.path_index < len(self.current_path)
    
    def clear_path(self):
        """Clear current path"""
        self.current_path = None
        self.path_index = 0
    
    def move_toward(self, target: Tuple[int, int], max_steps: int = 1) -> int:
        """
        Move up to max_steps toward target
        Creates path if needed
        
        Args:
            target: Target position (x, y)
            max_steps: Maximum number of steps to take
            
        Returns:
            Number of steps actually taken
        """
        # Create path if we don't have one
        if not self.has_path():
            if not self.find_path_to(target):
                return 0
        
        # Follow path
        steps = 0
        for _ in range(max_steps):
            if self.follow_path():
                steps += 1
            else:
                break
        
        return steps
    
    def move_away_from(self, threat: Tuple[int, int], distance: int = 5) -> bool:
        """
        Flee from a threat position
        
        Args:
            threat: Position to flee from (x, y)
            distance: Desired distance to maintain
            
        Returns:
            True if found escape route
        """
        if not self.pathfinder:
            return False
        
        # Find reachable positions
        reachable = self.pathfinder.find_all_reachable(
            (self.x, self.y), 
            max_distance=distance * 2,
            allow_diagonal=False
        )
        
        # Find position farthest from threat
        best_pos = None
        best_dist = 0
        
        for pos in reachable:
            dist = ((pos[0] - threat[0]) ** 2 + (pos[1] - threat[1]) ** 2) ** 0.5
            if dist > best_dist:
                best_dist = dist
                best_pos = pos
        
        if best_pos and best_dist >= distance:
            return self.find_path_to(best_pos)
        
        return False
    
    def move_direction(self, direction: str) -> Tuple[int, int]:
        """Get target coordinates for a direction"""
        dx, dy = 0, 0
        
        if direction == 'north':
            dy = -1
        elif direction == 'south':
            dy = 1
        elif direction == 'east':
            dx = 1
        elif direction == 'west':
            dx = -1
        
        return (self.x + dx, self.y + dy)
    
    def distance_to(self, other: 'Animate') -> float:
        """Calculate distance to another entity"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
    
    def distance_to_pos(self, pos: Tuple[int, int]) -> float:
        """Calculate distance to a position"""
        return ((self.x - pos[0]) ** 2 + (self.y - pos[1]) ** 2) ** 0.5
    
    # ========================================================================
    # COMBAT
    # ========================================================================
    
    def attack(self, target: 'Animate') -> Dict:
        """Basic attack"""
        if not self.stats.is_alive():
            return {'success': False, 'reason': 'attacker dead'}
        
        if not target.stats.is_alive():
            return {'success': False, 'reason': 'target already dead'}
        
        # Simple damage calculation
        damage = max(1, self.stats.attack_power - target.stats.defense // 2)
        target.stats.take_damage(damage)
        
        return {
            'success': True,
            'damage': damage,
            'target_alive': target.stats.is_alive()
        }
    
    def cast_spell(self, 
                   spell_synset: str, 
                   spell_data: Dict, 
                   target: Optional['Animate'] = None,
                   advantage: bool = False,
                   disadvantage: bool = False) -> Dict:
        """
        Cast a spell using D&D-style mechanics
        
        Args:
            spell_synset: Spell identifier (e.g., 'fireball.n.01')
            spell_data: Spell definition dict with composition, effects, etc.
            target: Target entity (if applicable)
            advantage: Roll with advantage (roll twice, take higher)
            disadvantage: Roll with disadvantage (roll twice, take lower)
            
        Returns:
            Dict with casting results
        """
        if HAS_SPELL_CASTING:
            # Use full D&D spell casting system
            return cast_spell_full(
                self, 
                spell_synset, 
                spell_data, 
                target,
                advantage,
                disadvantage
            )
        else:
            # Fallback to basic spell casting (no skill checks)
            return self._cast_spell_basic(spell_synset, spell_data, target)
    
    def _cast_spell_basic(self, spell_synset: str, spell_data: Dict, target: Optional['Animate'] = None) -> Dict:
        """
        Basic spell casting without D&D mechanics (fallback)
        This is the old simple system for when spell_casting.py isn't available
        """
        # Check if we know the spell
        if not self.inventory.knows_spell(spell_synset):
            return {'success': False, 'reason': 'spell unknown'}
        
        # Check essence cost
        cost = spell_data.get('composition', {})
        if not self.inventory.has_essence(cost):
            return {'success': False, 'reason': 'insufficient essence'}
        
        # Pay cost
        for element, amount in cost.items():
            self.inventory.remove_essence(element, amount)
        
        # Apply spell effect (simple version)
        effect = spell_data.get('spell_effect', {})
        effect_type = effect.get('type', 'damage')
        
        result = {
            'success': True,
            'spell': spell_data.get('word', spell_synset),
            'caster': self.name,
            'effect_type': effect_type
        }
        
        if effect_type == 'damage' and target:
            # Calculate damage from spell
            element = effect.get('element', 'fire')
            base_damage = self.stats.magic_power
            damage = max(1, base_damage - target.stats.magic_defense // 2)
            
            target.stats.take_damage(damage)
            result['damage'] = damage
            result['target'] = target.name
            result['target_alive'] = target.stats.is_alive()
        
        elif effect_type == 'heal':
            amount = effect.get('amount', 20)
            if target:
                target.stats.heal(amount)
                result['healed'] = amount
                result['target'] = target.name
            else:
                self.stats.heal(amount)
                result['healed'] = amount
                result['target'] = self.name
        
        return result
    
    # ========================================================================
    # ALCHEMY
    # ========================================================================
    
    def dissolve_object(self, obj: Dict, solvent: Dict) -> Dict:
        """Dissolve an object to extract essences"""
        if obj not in self.inventory.objects:
            return {'success': False, 'reason': 'object not in inventory'}
        
        # Get object essence composition
        essence_comp = obj.get('essence', {})
        
        # Extract based on solvent
        extracted = {}
        extracts = solvent.get('extracts', ['fire', 'water', 'earth', 'air'])
        strength = solvent.get('strength', 1.0)
        
        for element in extracts:
            if element in essence_comp:
                amount = essence_comp[element] * strength
                extracted[element] = amount
                self.inventory.add_essence(element, amount)
        
        # Remove object
        self.inventory.remove_object(obj)
        
        return {
            'success': True,
            'object': obj.get('name', 'unknown'),
            'extracted': extracted,
            'solvent': solvent.get('name', 'unknown')
        }
    
    def transform_object(self, obj: Dict, target_spell: Dict) -> Dict:
        """Transform an object into a spell"""
        if obj not in self.inventory.objects:
            return {'success': False, 'reason': 'object not in inventory'}
        
        # Get what we need to add/remove
        current = obj.get('essence', {})
        target = target_spell.get('composition', {})
        
        needed = {}
        excess = {}
        
        for element in ['fire', 'water', 'earth', 'air']:
            diff = target.get(element, 0) - current.get(element, 0)
            if diff > 0:
                needed[element] = diff
            elif diff < 0:
                excess[element] = -diff
        
        # Check if we have needed essences
        if not self.inventory.has_essence(needed):
            return {'success': False, 'reason': 'insufficient essence', 'needed': needed}
        
        # Pay the cost
        for element, amount in needed.items():
            self.inventory.remove_essence(element, amount)
        
        # Remove object, learn spell
        self.inventory.remove_object(obj)
        spell_synset = target_spell.get('synset', 'unknown.n.01')
        self.inventory.learn_spell(spell_synset)
        
        return {
            'success': True,
            'object': obj.get('name', 'unknown'),
            'spell': target_spell.get('word', 'unknown'),
            'synset': spell_synset,
            'consumed': needed
        }
    
    # ========================================================================
    # INTERACTION
    # ========================================================================
    
    def pick_up(self, obj: Dict) -> bool:
        """Pick up an object"""
        return self.inventory.add_object(obj)
    
    def drop(self, obj: Dict) -> bool:
        """Drop an object"""
        return self.inventory.remove_object(obj)
    
    def give_to(self, obj: Dict, target: 'Animate') -> bool:
        """Give object to another entity"""
        if self.inventory.remove_object(obj):
            return target.inventory.add_object(obj)
        return False
    
    # ========================================================================
    # AI / BEHAVIOR (Override in subclasses)
    # ========================================================================
    
    def update(self, world, delta_time: float):
        """Update entity (called each game tick)"""
        # Override in subclasses for AI behavior
        pass
    
    def on_damaged(self, attacker: 'Animate', damage: int):
        """Called when damaged"""
        # Override for special behavior
        if self.faction == 'neutral':
            self.faction = 'enemy'
            self.is_hostile = True
            self.target = attacker
    
    def on_death(self):
        """Called when health reaches 0"""
        self.is_active = False
        # Override for death behavior (drop loot, etc)
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for saving"""
        return {
            'name': self.name,
            'entity_type': self.entity_type,
            'faction': self.faction,
            'x': self.x,
            'y': self.y,
            'facing': self.facing,
            'stats': {
                'strength': self.stats.strength,
                'dexterity': self.stats.dexterity,
                'constitution': self.stats.constitution,
                'intelligence': self.stats.intelligence,
                'wisdom': self.stats.wisdom,
                'charisma': self.stats.charisma,
                'current_health': self.stats.current_health,
                'max_health': self.stats.max_health,
                'current_stamina': self.stats.current_stamina,
                'max_stamina': self.stats.max_stamina,
            },
            'inventory': {
                'essences': self.inventory.essences.copy(),
                'objects': self.inventory.objects.copy(),
                'grimoire': list(self.inventory.grimoire),
            },
            'is_active': self.is_active,
            'ai_state': self.ai_state,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Animate':
        """Load from dictionary"""
        # Create entity with basic info
        entity = cls.__new__(cls)  # Create without calling __init__
        
        # Set basic attributes
        entity.name = data['name']
        entity.entity_type = data['entity_type']
        entity.faction = data.get('faction', 'neutral')
        entity.x = data['x']
        entity.y = data['y']
        entity.facing = data.get('facing', 'north')
        
        # Create components
        entity.stats = Stats()
        entity.inventory = Inventory()
        
        # Restore stats
        stats_data = data.get('stats', {})
        for key, value in stats_data.items():
            setattr(entity.stats, key, value)
        
        # Restore inventory
        inv_data = data.get('inventory', {})
        entity.inventory.essences = inv_data.get('essences', {})
        entity.inventory.objects = inv_data.get('objects', [])
        entity.inventory.grimoire = set(inv_data.get('grimoire', []))
        
        # Restore state
        entity.is_active = data.get('is_active', True)
        entity.is_hostile = (entity.faction == 'enemy')
        entity.ai_state = data.get('ai_state', 'idle')
        entity.target = None
        
        # Player-specific attributes
        if entity.entity_type == 'player':
            entity.experience = data.get('experience', 0)
            entity.level = data.get('level', 1)
            entity.skill_points = data.get('skill_points', 0)
        
        return entity
    
    def __repr__(self):
        alive = "💚" if self.stats.is_alive() else "💀"
        return f"{alive} {self.name} ({self.entity_type}) at ({self.x}, {self.y})"


# ============================================================================
# SPECIALIZED SUBCLASSES
# ============================================================================

class Player(Animate):
    """Player-controlled entity"""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, entity_type='player', faction='player', **kwargs)
        
        # Player-specific attributes
        self.experience = 0
        self.level = 1
        self.skill_points = 0
        
        # Give player better starting stats for spell casting
        if 'intelligence' not in kwargs:
            self.stats.intelligence = 14  # +2 modifier
        if 'wisdom' not in kwargs:
            self.stats.wisdom = 12  # +1 modifier
        if 'magic_power' not in kwargs:
            self.stats.magic_power = 15
    
    def gain_xp(self, amount: int) -> Dict:
        """Gain experience, potentially leveling up. Returns level-up info."""
        self.experience += amount
        result = {'xp_gained': amount, 'leveled_up': False}
        
        # XP needed for next level: level * 100 (100, 200, 300...)
        xp_for_next = self.level * 100
        
        while self.experience >= xp_for_next:
            self.experience -= xp_for_next
            self.level += 1
            self.skill_points += 1
            
            # Grow essence capacity by 25 per level
            self.inventory.grow_essence_capacity(25)
            
            # Boost stats slightly
            self.stats.max_health += 10
            self.stats.current_health = min(self.stats.current_health + 10, self.stats.max_health)
            self.stats.magic_power += 2
            
            result['leveled_up'] = True
            result['new_level'] = self.level
            result['new_max_essence'] = self.inventory.max_essence
            
            xp_for_next = self.level * 100
        
        result['xp_to_next'] = xp_for_next - self.experience
        return result
    
    def xp_for_next_level(self) -> int:
        """XP needed to reach next level"""
        return self.level * 100 - self.experience


class NPC(Animate):
    """Non-player character (friendly or neutral)"""
    
    def __init__(self, name: str, role: str = 'villager', **kwargs):
        super().__init__(name, entity_type='npc', faction='neutral', **kwargs)
        
        self.role = role  # merchant, guard, villager, quest_giver
        self.dialogue = []
        self.shop_inventory = []
        self.patrol_points: List[Tuple[int, int]] = []
        self.patrol_index = 0
    
    def set_patrol_route(self, points: List[Tuple[int, int]]):
        """Set patrol waypoints"""
        self.patrol_points = points
        self.patrol_index = 0
    
    def update(self, world, delta_time: float):
        """AI with patrol behavior"""
        if self.ai_state == 'patrol' and self.patrol_points:
            # Follow patrol route
            if not self.has_path():
                target = self.patrol_points[self.patrol_index]
                if self.find_path_to(target):
                    # Move to next waypoint when reached
                    if (self.x, self.y) == target:
                        self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            else:
                self.follow_path()
        
        elif self.ai_state == 'idle':
            # Occasionally wander
            import random
            if random.random() < 0.05:  # 5% chance per update
                if self.pathfinder:
                    # Find random nearby position
                    reachable = self.pathfinder.find_all_reachable(
                        (self.x, self.y), 
                        max_distance=5
                    )
                    if reachable:
                        target = random.choice(list(reachable))
                        self.find_path_to(target)


class Monster(Animate):
    """Hostile creature"""
    
    def __init__(self, name: str, monster_type: str = 'generic', **kwargs):
        super().__init__(name, entity_type='monster', faction='enemy', **kwargs)
        
        self.monster_type = monster_type
        self.aggro_range = 5.0
        self.attack_range = 1.5
        self.loot_table = []
    
    def update(self, world, delta_time: float):
        """Aggressive AI with pathfinding"""
        if not self.stats.is_alive():
            return
        
        # Combat AI
        if self.ai_state == 'combat' and self.target:
            dist = self.distance_to(self.target)
            
            if dist > self.attack_range:
                # Move toward target using pathfinding
                self.move_toward((self.target.x, self.target.y), max_steps=1)
            else:
                # In range - attack!
                self.attack(self.target)
                # Clear path so we recalculate next frame
                self.clear_path()
        
        elif self.ai_state == 'idle':
            # Look for targets in aggro range
            # (world would need to provide nearby entities)
            pass
    
    def on_death(self):
        """Drop loot on death"""
        super().on_death()
        # Loot drops would be handled by game system


class Companion(Animate):
    """Allied follower"""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name, entity_type='companion', faction='ally', **kwargs)
        
        self.master = None  # Player they follow
        self.loyalty = 100
        self.follow_distance = 2.0
    
    def update(self, world, delta_time: float):
        """Follow master using pathfinding"""
        if self.ai_state == 'follow' and self.master:
            dist = self.distance_to(self.master)
            
            # Only follow if too far
            if dist > self.follow_distance:
                # Move toward master
                self.move_toward((self.master.x, self.master.y), max_steps=1)
            else:
                # Close enough, clear path
                self.clear_path()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import numpy as np
    
    print("=" * 70)
    print("ANIMATE ENTITY SYSTEM WITH PATHFINDING")
    print("=" * 70)
    
    # Create a simple dungeon grid
    grid = np.array([
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ])
    
    # Setup pathfinder
    try:
        from pathfinding import Pathfinder
        pathfinder = Pathfinder(grid, walkable_tiles={0})
        has_pathfinding = True
    except ImportError:
        print("⚠️  Pathfinding module not available")
        print("   Movement will be basic (no collision detection)")
        pathfinder = None
        has_pathfinding = False
    
    # Create entities
    player = Player("Hero", x=1, y=1)
    npc = NPC("Village Elder", role="quest_giver", x=7, y=3)
    monster = Monster("Goblin", monster_type="goblin", x=13, y=1)
    companion = Companion("Faithful Dog", x=2, y=1)
    companion.master = player
    companion.ai_state = 'follow'
    
    # Set pathfinder for all entities
    if has_pathfinding:
        player.set_pathfinder(pathfinder)
        npc.set_pathfinder(pathfinder)
        monster.set_pathfinder(pathfinder)
        companion.set_pathfinder(pathfinder)
    
    print("\n📍 Entities created:")
    print(f"  {player}")
    print(f"  {npc}")
    print(f"  {monster}")
    print(f"  {companion}")
    
    if has_pathfinding:
        # Demonstrate pathfinding movement
        print("\n" + "=" * 70)
        print("🗺️  PATHFINDING DEMONSTRATION")
        print("=" * 70)
        
        # Show initial grid
        def show_grid(entities):
            vis = []
            for y in range(grid.shape[0]):
                row = []
                for x in range(grid.shape[1]):
                    # Check for entities
                    entity_here = None
                    for e in entities:
                        if e.x == x and e.y == y:
                            entity_here = e
                            break
                    
                    if entity_here:
                        if entity_here.entity_type == 'player':
                            row.append('P')
                        elif entity_here.entity_type == 'monster':
                            row.append('M')
                        elif entity_here.entity_type == 'companion':
                            row.append('C')
                        elif entity_here.entity_type == 'npc':
                            row.append('N')
                    elif grid[y, x] == 0:
                        row.append('.')
                    else:
                        row.append('#')
                vis.append(''.join(row))
            return '\n'.join(vis)
        
        entities = [player, npc, monster, companion]
        
        print("\n📍 Initial positions:")
        print("   P=Player, M=Monster, C=Companion, N=NPC")
        print(show_grid(entities))
        
        # Player pathfinds to NPC
        print("\n🎯 Player finds path to NPC...")
        if player.find_path_to((npc.x, npc.y), smooth=True):
            print(f"   Path found! Length: {len(player.current_path)}")
            print(f"   Path: {player.current_path[:5]}..." if len(player.current_path) > 5 else f"   Path: {player.current_path}")
        
        # Move player 3 steps
        print("\n👣 Player moves 3 steps...")
        steps = player.move_toward((npc.x, npc.y), max_steps=3)
        print(f"   Moved {steps} steps")
        print(f"   New position: ({player.x}, {player.y})")
        
        print("\n📍 After movement:")
        print(show_grid(entities))
        
        # Companion follows
        print("\n🐕 Companion follows player...")
        companion.update(None, 0.1)
        print(f"   Companion position: ({companion.x}, {companion.y})")
        
        # Monster aggros and chases
        print("\n👹 Monster enters combat mode...")
        monster.ai_state = 'combat'
        monster.target = player
        
        for i in range(3):
            monster.update(None, 0.1)
        
        print(f"   Monster moved toward player")
        print(f"   Monster position: ({monster.x}, {monster.y})")
        print(f"   Distance to player: {monster.distance_to(player):.1f}")
        
        print("\n📍 Final positions:")
        print(show_grid(entities))
    
    # Give player some essences
    print("\n" + "=" * 70)
    print("🔮 ALCHEMY & SPELL CASTING")
    print("=" * 70)
    
    print("\n🔮 Player gathering essences...")
    player.inventory.add_essence('fire', 500)
    player.inventory.add_essence('water', 200)
    player.inventory.add_essence('earth', 200)
    player.inventory.add_essence('air', 200)
    print(f"  Essences: {player.inventory.essences}")
    
    # Player learns spells
    print("\n📖 Player learns spells...")
    player.inventory.learn_spell('fireball.n.01')
    player.inventory.learn_spell('heal.v.01')
    print(f"  Grimoire: {player.inventory.grimoire}")
    
    # Define spells for testing
    fireball_spell = {
        'word': 'krata',
        'composition': {
            'fire': 58,
            'water': 5,
            'earth': 10,
            'air': 12
        },
        'definition': 'a ball of fire',
        'spell_effect': {
            'type': 'damage',
            'element': 'fire'
        }
    }
    
    heal_spell = {
        'word': 'lumno',
        'composition': {
            'fire': 8,
            'water': 55,
            'earth': 15,
            'air': 18
        },
        'definition': 'restore to health',
        'spell_effect': {
            'type': 'heal'
        }
    }
    
    if HAS_SPELL_CASTING:
        print("\n" + "=" * 70)
        print("🎲 D&D-STYLE SPELL CASTING")
        print("=" * 70)
        
        # Show stats
        print(f"\n🧙 {player.name}'s Spell Stats:")
        print(f"  Intelligence: {player.stats.intelligence} (+{(player.stats.intelligence-10)//2})")
        print(f"  Wisdom: {player.stats.wisdom} (+{(player.stats.wisdom-10)//2})")
        print(f"  Magic Power: {player.stats.magic_power}")
        print(f"  Level: {player.level}")
        
        print(f"\n👹 {monster.name}'s Defense:")
        print(f"  HP: {monster.stats.current_health}/{monster.stats.max_health}")
        print(f"  Magic Defense: {monster.stats.magic_defense}")
        
        # Cast fireball at monster
        print("\n⚡ Casting Fireball at monster...")
        result = player.cast_spell('fireball.n.01', fireball_spell, target=monster)
        
        if 'roll' in result:
            print(f"  🎲 Roll: {result['roll']} vs DC {result['dc']}")
            print(f"  📊 Result: {result['result'].value}")
        
        if result['success']:
            print(f"  ✅ Success!")
            if 'damage' in result:
                print(f"  ⚔️  Damage: {result['damage']}")
                print(f"  💀 Monster HP: {monster.stats.current_health}/{monster.stats.max_health}")
            if 'power' in result:
                print(f"  ⚡ Spell Power: {result['power']:.1f}")
            print(f"  💎 Essence Spent: {result.get('essence_spent', {})}")
        else:
            print(f"  ❌ Failed!")
            if 'message' in result:
                print(f"  💬 {result['message']}")
        
        # Player takes damage
        print("\n💔 Player takes damage...")
        player.stats.take_damage(30)
        print(f"  HP: {player.stats.current_health}/{player.stats.max_health}")
        
        # Cast heal on self
        print("\n💚 Casting Heal on self...")
        result = player.cast_spell('heal.v.01', heal_spell)
        
        if 'roll' in result:
            print(f"  🎲 Roll: {result['roll']} vs DC {result['dc']}")
        
        if result['success']:
            if 'healed' in result:
                print(f"  ✅ Healed {result['healed']} HP!")
                print(f"  💚 HP: {player.stats.current_health}/{player.stats.max_health}")
        
        # Try casting with advantage
        print("\n⚡ Casting Fireball with ADVANTAGE...")
        monster.stats.current_health = 100  # Reset
        result = player.cast_spell('fireball.n.01', fireball_spell, target=monster, advantage=True)
        
        if 'roll' in result:
            print(f"  🎲 Roll: {result['roll']} vs DC {result['dc']} (with advantage)")
            print(f"  📊 Result: {result['result'].value}")
        
        if result['success'] and 'damage' in result:
            print(f"  ⚔️  Damage: {result['damage']}")
    
    else:
        print("\n⚠️  Advanced spell casting not available")
        print("   Using basic spell system")
        
        # Basic combat
        print("\n⚔️  Basic combat scenario:")
        print(f"  Player HP: {player.stats.current_health}/{player.stats.max_health}")
        print(f"  Monster HP: {monster.stats.current_health}/{monster.stats.max_health}")
        
        # Player attacks
        result = player.attack(monster)
        print(f"\n  Player attacks! Damage: {result['damage']}")
        print(f"  Monster HP: {monster.stats.current_health}/{monster.stats.max_health}")
    
    # Save/Load
    print("\n💾 Serialization test:")
    player_data = player.to_dict()
    print(f"  Saved player data: {len(str(player_data))} bytes")
    
    loaded_player = Player.from_dict(player_data)
    print(f"  Loaded: {loaded_player}")
    print(f"  Essences preserved: {loaded_player.inventory.essences}")
    print(f"  Grimoire preserved: {loaded_player.inventory.grimoire}")
    
    print("\n" + "=" * 70)
    print("✅ Animate system with pathfinding ready!")
    print("=" * 70)
    
    print("\n💡 Movement Features:")
    print("  - find_path_to(goal) - A* pathfinding to target")
    print("  - move_toward(pos, max_steps) - Move along path")
    print("  - move_away_from(threat, distance) - Flee behavior")
    print("  - follow_path() - Single step along current path")
    print("  - Automatic path smoothing for natural movement")
    print("  - NPCs patrol routes")
    print("  - Monsters chase targets")
    print("  - Companions follow masters")
