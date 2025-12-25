"""
Elemental Magic Spell System
A word-based magic system where elemental composition determines spell power
"""

import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class GameObject:
    """Base class for all game objects"""
    name: str
    hp: int = 100
    max_hp: int = 100
    object_type: str = 'object'
    element_resistances: Dict[str, float] = field(default_factory=lambda: {
        'fire': 0, 'water': 0, 'earth': 0, 'air': 0, 'neutral': 0
    })
    status_effects: List[Tuple[str, int]] = field(default_factory=list)
    position: Tuple[float, float, float] = (0, 0, 0)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def is_alive(self):
        return self.hp > 0
    
    def take_damage(self, amount: float, element: str = 'neutral'):
        """Apply damage with resistance calculation"""
        resistance = self.element_resistances.get(element, 0)
        actual_damage = max(0, amount - resistance)
        self.hp -= actual_damage
        return actual_damage
    
    def heal(self, amount: float):
        """Restore HP, capped at max"""
        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        return self.hp - old_hp
    
    def add_status(self, status: str, duration: int):
        """Add a status effect"""
        self.status_effects.append((status, duration))
    
    def tick_statuses(self):
        """Reduce status durations by 1, remove expired"""
        self.status_effects = [
            (status, duration - 1) 
            for status, duration in self.status_effects 
            if duration > 1
        ]


@dataclass
class Creature(GameObject):
    """A living creature"""
    def __init__(self, name: str, hp: int = 100):
        super().__init__(name, hp, hp, 'creature')
        self.speed = 10
        self.following = 0  # Number of creatures following this one


@dataclass  
class TerrainObject(GameObject):
    """Terrain or environmental object"""
    def __init__(self, name: str, terrain_type: str, hp: int = 50):
        super().__init__(name, hp, hp, 'terrain')
        self.terrain_type = terrain_type  # 'wood', 'stone', 'water', etc.


@dataclass
class Shield(GameObject):
    """A magical shield"""
    def __init__(self, hp: int, blocks: str = 'physical'):
        super().__init__("Shield", hp, hp, 'shield')
        self.blocks = blocks


@dataclass
class Projectile(GameObject):
    """A magical projectile in flight"""
    def __init__(self, spell_word: str, spell_vector: Tuple[int, int, int, int], 
                 target: GameObject):
        super().__init__(f"{spell_word} projectile", 1, 1, 'projectile')
        self.spell_word = spell_word
        self.spell_vector = spell_vector
        self.target = target


class SpellExecutor:
    """Executes spell effects based on their definitions"""
    
    def __init__(self, spell_data: Dict[str, Any]):
        self.data = spell_data
        self.word = spell_data.get('word', 'unknown')
        self.composition = spell_data['composition']
        self.effect = spell_data['spell_effect']
    
    def _eval_value(self, value: Any) -> float:
        """Evaluate a value that might be a formula"""
        if isinstance(value, str):
            # Allow formulas like "fire * 0.8" or "water + earth"
            try:
                return eval(value, {"__builtins__": {}}, self.composition)
            except:
                return 0
        return float(value)
    
    def cast(self, caster: GameObject, targets: List[GameObject], 
             context: Dict[str, Any] = None) -> List[str]:
        """Execute the spell and return narrative messages"""
        if context is None:
            context = {}
        
        effect_type = self.effect['type']
        
        # Route to appropriate handler
        handlers = {
            'damage': self._do_damage,
            'heal': self._do_heal,
            'modify_state': self._modify_state,
            'create_object': self._create_object,
            'apply_status': self._apply_status,
            'area_effect': self._area_effect,
            'relocate': self._relocate,
            'summon': self._summon,
            'transform': self._transform,
            'buff': self._buff,
            'debuff': self._debuff,
        }
        
        handler = handlers.get(effect_type)
        if handler:
            return handler(caster, targets, context)
        else:
            return [f"Unknown spell effect type: {effect_type}"]
    
    def _do_damage(self, caster, targets, context) -> List[str]:
        """Deal damage to targets"""
        messages = [self.effect['description']]
        damage = self._eval_value(self.effect['amount'])
        element = self.effect.get('element', 'neutral')
        
        for target in targets:
            actual_damage = target.take_damage(damage, element)
            messages.append(
                f"{target.name} takes {actual_damage:.0f} {element} damage! "
                f"({target.hp:.0f}/{target.max_hp} HP)"
            )
            
            if not target.is_alive():
                messages.append(f"{target.name} has fallen!")
        
        return messages
    
    def _do_heal(self, caster, targets, context) -> List[str]:
        """Restore HP to targets"""
        messages = [self.effect['description']]
        healing = self._eval_value(self.effect['amount'])
        
        for target in targets:
            actual_healing = target.heal(healing)
            messages.append(
                f"{target.name} recovers {actual_healing:.0f} HP! "
                f"({target.hp:.0f}/{target.max_hp})"
            )
            
            # Remove negative fire-based statuses
            if 'remove_status' in self.effect:
                statuses_to_remove = self.effect['remove_status']
                target.status_effects = [
                    (s, d) for s, d in target.status_effects 
                    if s not in statuses_to_remove
                ]
                messages.append(f"Burning and poison effects are cleansed!")
        
        return messages
    
    def _modify_state(self, caster, targets, context) -> List[str]:
        """Modify attributes of targets"""
        messages = [self.effect['description']]
        
        for target in targets:
            for key, value in self.effect['modification'].items():
                # Handle nested attributes like "following"
                current = getattr(target, key, 0)
                new_value = current + self._eval_value(value)
                setattr(target, key, new_value)
                
                if value < 0:
                    messages.append(f"{target.name} stops pursuing you.")
                else:
                    messages.append(f"{target.name}'s {key} changed to {new_value}")
        
        return messages
    
    def _create_object(self, caster, targets, context) -> List[str]:
        """Create a new game object"""
        messages = [self.effect['description']]
        
        obj_class = self.effect['object_class']
        properties = self.effect.get('properties', {})
        
        # Evaluate property values
        eval_props = {
            k: self._eval_value(v) for k, v in properties.items()
        }
        
        # Create the object
        if obj_class == 'Shield':
            new_obj = Shield(
                hp=eval_props.get('hp', 50),
                blocks=properties.get('blocks', 'physical')
            )
        else:
            new_obj = GameObject(obj_class, **eval_props)
        
        # Attach to target
        target = targets[0] if targets else caster
        target.properties['created_object'] = new_obj
        
        messages.append(f"Created {new_obj.name} with {new_obj.hp:.0f} HP")
        
        return messages
    
    def _apply_status(self, caster, targets, context) -> List[str]:
        """Apply status effects to targets"""
        messages = [self.effect['description']]
        
        status = self.effect['status']
        duration = int(self._eval_value(self.effect.get('duration', 3)))
        
        for target in targets:
            target.add_status(status, duration)
            messages.append(
                f"{target.name} is afflicted with {status} for {duration} turns!"
            )
            
            # Apply immediate effects if specified
            if 'effects' in self.effect:
                for eff in self.effect['effects']:
                    if eff['type'] == 'modify':
                        attr = eff['modify']
                        value = self._eval_value(eff['value'])
                        current = getattr(target, attr, 0)
                        setattr(target, attr, current + value)
        
        return messages
    
    def _area_effect(self, caster, targets, context) -> List[str]:
        """Area of effect spell hitting multiple targets"""
        messages = [self.effect['description']]
        
        radius = self._eval_value(self.effect.get('radius', 5))
        messages.append(f"Area of effect: {radius:.1f} units")
        
        # Apply each sub-effect
        for sub_effect in self.effect.get('effects', []):
            effect_type = sub_effect['type']
            target_filter = sub_effect.get('to', 'all')
            
            # Filter targets
            filtered = [
                t for t in targets 
                if target_filter == 'all' or t.object_type == target_filter
            ]
            
            if effect_type == 'damage':
                damage = self._eval_value(sub_effect['amount'])
                element = sub_effect.get('element', 'neutral')
                for target in filtered:
                    actual = target.take_damage(damage, element)
                    messages.append(f"{target.name} takes {actual:.0f} damage!")
            
            elif effect_type == 'apply_status':
                status = sub_effect['status']
                for target in filtered:
                    target.add_status(status, 1)
                    messages.append(f"{target.name} is {status}!")
        
        return messages
    
    def _relocate(self, caster, targets, context) -> List[str]:
        """Teleport or move targets"""
        messages = [self.effect['description']]
        
        range_dist = self._eval_value(self.effect.get('range', 10))
        
        for target in targets:
            # Simple teleport - in real game would check valid positions
            old_pos = target.position
            # Just move forward for demo
            target.position = (old_pos[0] + range_dist, old_pos[1], old_pos[2])
            messages.append(
                f"{target.name} teleports {range_dist:.0f} units away!"
            )
        
        return messages
    
    def _summon(self, caster, targets, context) -> List[str]:
        """Summon a creature or object"""
        messages = [self.effect['description']]
        
        creature_type = self.effect.get('creature', 'Elemental')
        hp = self._eval_value(self.effect.get('hp', 30))
        duration = int(self._eval_value(self.effect.get('duration', 5)))
        
        summoned = Creature(f"{creature_type}", hp=hp)
        summoned.add_status('summoned', duration)
        
        context['summoned'] = context.get('summoned', [])
        context['summoned'].append(summoned)
        
        messages.append(f"A {creature_type} appears with {hp:.0f} HP!")
        messages.append(f"It will last for {duration} turns.")
        
        return messages
    
    def _transform(self, caster, targets, context) -> List[str]:
        """Transform one object into another"""
        messages = [self.effect['description']]
        
        new_type = self.effect.get('into', 'object')
        
        for target in targets:
            old_name = target.name
            target.name = new_type
            target.object_type = new_type
            messages.append(f"{old_name} transforms into {new_type}!")
        
        return messages
    
    def _buff(self, caster, targets, context) -> List[str]:
        """Enhance target's abilities"""
        messages = [self.effect['description']]
        
        stat = self.effect.get('stat', 'hp')
        amount = self._eval_value(self.effect.get('amount', 10))
        duration = int(self._eval_value(self.effect.get('duration', 3)))
        
        for target in targets:
            target.add_status(f'buffed_{stat}', duration)
            target.properties[f'buff_{stat}'] = amount
            messages.append(
                f"{target.name}'s {stat} increased by {amount:.0f} "
                f"for {duration} turns!"
            )
        
        return messages
    
    def _debuff(self, caster, targets, context) -> List[str]:
        """Weaken target's abilities"""  
        messages = [self.effect['description']]
        
        stat = self.effect.get('stat', 'speed')
        amount = self._eval_value(self.effect.get('amount', -5))
        duration = int(self._eval_value(self.effect.get('duration', 3)))
        
        for target in targets:
            target.add_status(f'debuffed_{stat}', duration)
            if hasattr(target, stat):
                current = getattr(target, stat)
                setattr(target, stat, max(0, current + amount))
            messages.append(
                f"{target.name}'s {stat} reduced for {duration} turns!"
            )
        
        return messages


class SpellDictionary:
    """Manages the spell dictionary and transformations"""
    
    def __init__(self, spell_data_path: str):
        with open(spell_data_path, 'r') as f:
            self.spell_data = json.load(f)
        
        # Build reverse lookup: composition -> word
        self.elemental_dictionary = {}
        for spell_id, data in self.spell_data.items():
            comp = data['composition']
            vector = (comp['fire'], comp['water'], comp['earth'], comp['air'])
            self.elemental_dictionary[vector] = data['word']
    
    def get_spell(self, word: str) -> Dict[str, Any]:
        """Get spell data by word"""
        for spell_id, data in self.spell_data.items():
            if data.get('word') == word:
                return data
        return None
    
    def transform_spell(self, word: str, fire=0, water=0, earth=0, air=0) -> str:
        """Transform a spell by adding elemental components"""
        # Find the base spell
        base_spell = self.get_spell(word)
        if not base_spell:
            return None
        
        # Calculate new composition
        comp = base_spell['composition']
        new_vector = (
            self._clamp(comp['fire'] + fire),
            self._clamp(comp['water'] + water),
            self._clamp(comp['earth'] + earth),
            self._clamp(comp['air'] + air)
        )
        
        # Look up what spell this new vector represents
        return self.elemental_dictionary.get(new_vector, "undefined")
    
    def permute_spell(self, word: str, permutation: str) -> str:
        """Permute elemental positions (anagram-style transformation)"""
        base_spell = self.get_spell(word)
        if not base_spell:
            return None
        
        comp = base_spell['composition']
        f, w, e, a = comp['fire'], comp['water'], comp['earth'], comp['air']
        
        permutations = {
            'swap_fw': (w, f, e, a),
            'swap_ea': (f, w, a, e),
            'swap_fe': (e, w, f, a),
            'swap_wa': (f, a, e, w),
            'rotate_left': (w, e, a, f),
            'rotate_right': (a, f, w, e),
            'reverse': (a, e, w, f),
        }
        
        new_vector = permutations.get(permutation)
        if new_vector:
            return self.elemental_dictionary.get(new_vector, "undefined")
        return None
    
    @staticmethod
    def _clamp(value: int, min_val: int = 0, max_val: int = 63) -> int:
        """Clamp value to valid range"""
        return max(min_val, min(max_val, value))


def demo_combat():
    """Demo combat scenario"""
    print("=" * 80)
    print("ELEMENTAL MAGIC COMBAT DEMO")
    print("=" * 80)
    print()
    
    # Load spells
    dictionary = SpellDictionary('elemental_spells.json')
    
    # Create combatants
    player = Creature("Hero", hp=100)
    goblin = Creature("Goblin", hp=50)
    goblin.following = 1  # Chasing player
    orc = Creature("Orc", hp=80)
    campfire = TerrainObject("Campfire", "wood", hp=20)
    campfire.add_status('damp', 5)
    
    print(f"🧙 {player.name}: {player.hp} HP")
    print(f"👹 {goblin.name}: {goblin.hp} HP (pursuing!)")
    print(f"👺 {orc.name}: {orc.hp} HP")
    print(f"🔥 {campfire.name}: {campfire.hp} HP (damp)")
    print()
    
    # Turn 1: Cast fireball
    print("TURN 1: Hero casts 'krata' (Fireball)")
    print("-" * 80)
    spell_data = dictionary.get_spell("krata")
    executor = SpellExecutor(spell_data)
    messages = executor.cast(player, [goblin, orc], {})
    for msg in messages:
        print(f"  {msg}")
    print()
    
    # Turn 2: Cast abandon
    print("TURN 2: Hero casts 'heysa' (Abandon)")
    print("-" * 80)
    spell_data = dictionary.get_spell("heysa")
    executor = SpellExecutor(spell_data)
    messages = executor.cast(player, [goblin], {})
    for msg in messages:
        print(f"  {msg}")
    print()
    
    # Turn 3: Heal self
    print("TURN 3: Hero casts 'lumno' (Heal)")
    print("-" * 80)
    player.hp = 60  # Simulate damage taken
    spell_data = dictionary.get_spell("lumno")
    executor = SpellExecutor(spell_data)
    messages = executor.cast(player, [player], {})
    for msg in messages:
        print(f"  {msg}")
    print()
    
    # Turn 4: Transformation!
    print("TURN 4: Hero transforms 'lumno' by adding 40 fire")
    print("-" * 80)
    new_word = dictionary.transform_spell("lumno", fire=40)
    print(f"  'lumno' + 40 fire = '{new_word}'")
    spell_data = dictionary.get_spell(new_word)
    if spell_data:
        executor = SpellExecutor(spell_data)
        messages = executor.cast(player, [orc], {})
        for msg in messages:
            print(f"  {msg}")
    print()
    
    # Turn 5: Summon elemental
    print("TURN 5: Hero casts 'kratesh' (Summon Fire Elemental)")
    print("-" * 80)
    spell_data = dictionary.get_spell("kratesh")
    context = {}
    executor = SpellExecutor(spell_data)
    messages = executor.cast(player, [], context)
    for msg in messages:
        print(f"  {msg}")
    print()
    
    print("=" * 80)
    print("COMBAT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    demo_combat()
