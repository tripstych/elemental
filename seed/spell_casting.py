"""
Spell Casting System
D&D-style spell checks with stats, difficulty, failures, and critical effects
"""

import random
from typing import Dict, Optional, Tuple
from enum import Enum


class SpellResult(Enum):
    """Spell casting outcomes"""
    CRITICAL_SUCCESS = "critical_success"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"
    INSUFFICIENT_ESSENCE = "insufficient_essence"
    SPELL_UNKNOWN = "spell_unknown"


class SpellCaster:
    """
    Handles spell casting mechanics separate from Animate class
    Makes it easy to plug into any entity system
    """
    
    # Base difficulty classes for spell tiers
    SPELL_DC = {
        'cantrip': 8,      # Very easy
        'minor': 12,       # Easy
        'moderate': 16,    # Medium
        'major': 20,       # Hard
        'legendary': 25,   # Very hard
    }
    
    @staticmethod
    def calculate_spell_tier(essence_total: int) -> str:
        """Determine spell tier based on total essence cost"""
        if essence_total <= 20:
            return 'cantrip'
        elif essence_total <= 50:
            return 'minor'
        elif essence_total <= 100:
            return 'moderate'
        elif essence_total <= 200:
            return 'major'
        else:
            return 'legendary'
    
    @staticmethod
    def calculate_spell_dc(spell_data: Dict) -> int:
        """
        Calculate the Difficulty Class for casting a spell
        
        Factors:
        - Base DC from tier
        - Complexity (number of different elements)
        - Imbalance (heavy reliance on one element)
        """
        composition = spell_data.get('composition', {})
        
        # Get total essence cost
        total = sum(composition.values())
        tier = SpellCaster.calculate_spell_tier(total)
        base_dc = SpellCaster.SPELL_DC[tier]
        
        # Complexity bonus (more elements = harder)
        elements_used = sum(1 for v in composition.values() if v > 0)
        complexity_bonus = (elements_used - 1)  # No penalty for 1 element
        
        # Imbalance penalty (heavily skewed to one element = easier)
        if total > 0:
            max_element = max(composition.values())
            imbalance_ratio = max_element / total
            if imbalance_ratio > 0.7:  # 70%+ in one element
                complexity_bonus -= 2
        
        return max(base_dc, base_dc + complexity_bonus)  # Never go below base
    
    @staticmethod
    def roll_spell_check(caster_stats: Dict, 
                        spell_dc: int,
                        advantage: bool = False,
                        disadvantage: bool = False) -> Tuple[int, SpellResult]:
        """
        Roll a spell casting check
        
        Roll: 1d20 + spell_modifier
        Spell modifier = (INT + WIS) / 2 + proficiency
        
        Args:
            caster_stats: Dict with 'intelligence', 'wisdom', 'level' (optional)
            spell_dc: Difficulty class to beat
            advantage: Roll twice, take higher
            disadvantage: Roll twice, take lower
            
        Returns:
            (total_roll, result_type)
        """
        intelligence = caster_stats.get('intelligence', 10)
        wisdom = caster_stats.get('wisdom', 10)
        level = caster_stats.get('level', 1)
        
        # Calculate modifier
        int_mod = (intelligence - 10) // 2
        wis_mod = (wisdom - 10) // 2
        spell_modifier = (int_mod + wis_mod) // 2
        
        # Proficiency bonus (scales with level)
        proficiency = 2 + (level - 1) // 4
        
        # Roll d20
        rolls = []
        if advantage or disadvantage:
            rolls = [random.randint(1, 20), random.randint(1, 20)]
            if advantage:
                d20 = max(rolls)
            else:
                d20 = min(rolls)
        else:
            d20 = random.randint(1, 20)
            rolls = [d20]
        
        total = d20 + spell_modifier + proficiency
        
        # Determine result
        if d20 == 20:
            result = SpellResult.CRITICAL_SUCCESS
        elif d20 == 1:
            result = SpellResult.CRITICAL_FAILURE
        elif total >= spell_dc + 10:
            result = SpellResult.CRITICAL_SUCCESS
        elif total >= spell_dc:
            result = SpellResult.SUCCESS
        elif total >= spell_dc - 5:
            result = SpellResult.PARTIAL_SUCCESS
        else:
            result = SpellResult.FAILURE
        
        return total, result
    
    @staticmethod
    def calculate_essence_cost(spell_data: Dict, result: SpellResult) -> Dict[str, float]:
        """
        Calculate actual essence cost based on casting result
        
        - Critical Success: 50% cost
        - Success: Full cost
        - Partial: 100% cost (inefficient)
        - Failure: 50% cost (wasted)
        - Critical Failure: Full cost (wasted)
        """
        base_cost = spell_data.get('composition', {})
        
        multipliers = {
            SpellResult.CRITICAL_SUCCESS: 0.5,
            SpellResult.SUCCESS: 1.0,
            SpellResult.PARTIAL_SUCCESS: 1.0,
            SpellResult.FAILURE: 0.5,
            SpellResult.CRITICAL_FAILURE: 1.0,
        }
        
        multiplier = multipliers.get(result, 1.0)
        
        return {
            element: amount * multiplier 
            for element, amount in base_cost.items()
        }
    
    @staticmethod
    def calculate_spell_power(spell_data: Dict, 
                             result: SpellResult,
                             caster_stats: Dict) -> float:
        """
        Calculate the effective power of a spell
        Used to scale damage, healing, duration, etc.
        
        Base power = spell_level * (1.0 + magic_power_mod)
        Modified by casting result
        """
        composition = spell_data.get('composition', {})
        total = sum(composition.values())
        
        # Get magic power modifier from stats
        intelligence = caster_stats.get('intelligence', 10)
        magic_power = caster_stats.get('magic_power', 10)
        
        int_mod = (intelligence - 10) / 20  # -0.5 to +0.5
        power_mod = magic_power / 100  # 0.1 for power=10, 0.5 for power=50
        
        base_power = total * (1.0 + int_mod + power_mod)
        
        # Result multipliers
        multipliers = {
            SpellResult.CRITICAL_SUCCESS: 2.0,    # Double effect!
            SpellResult.SUCCESS: 1.0,             # Full effect
            SpellResult.PARTIAL_SUCCESS: 0.6,     # Reduced effect
            SpellResult.FAILURE: 0.0,             # No effect
            SpellResult.CRITICAL_FAILURE: -0.5,   # Backfire!
        }
        
        multiplier = multipliers.get(result, 1.0)
        
        return base_power * multiplier
    
    @staticmethod
    def apply_spell_effect(spell_data: Dict,
                          power: float,
                          caster,
                          target=None) -> Dict:
        """
        Apply spell effects based on calculated power
        
        Returns dict with effect details
        """
        effect = spell_data.get('spell_effect', {})
        effect_type = effect.get('type', 'damage')
        
        result = {
            'type': effect_type,
            'power': power,
        }
        
        if effect_type == 'damage':
            # Calculate damage
            base_damage = caster.stats.magic_power if hasattr(caster, 'stats') else 10
            damage = int(base_damage * power / 10)
            
            if target and hasattr(target, 'stats'):
                # Apply target's magic defense
                reduced = max(1, damage - target.stats.magic_defense // 2)
                target.stats.take_damage(reduced)
                result['damage'] = reduced
                result['target'] = target.name
                result['target_alive'] = target.stats.is_alive()
            else:
                result['damage'] = damage
        
        elif effect_type == 'heal':
            # Calculate healing
            heal_amount = int(20 * power / 10)
            
            if target and hasattr(target, 'stats'):
                target.stats.heal(heal_amount)
                result['healed'] = heal_amount
                result['target'] = target.name
            elif hasattr(caster, 'stats'):
                caster.stats.heal(heal_amount)
                result['healed'] = heal_amount
                result['target'] = caster.name
        
        elif effect_type == 'buff':
            # Apply stat buff
            result['duration'] = int(5 + power / 20)  # 5-15 turns typically
            result['magnitude'] = power / 10
        
        elif effect_type == 'debuff':
            # Apply stat debuff
            result['duration'] = int(3 + power / 30)
            result['magnitude'] = power / 10
        
        return result
    
    @staticmethod
    def handle_critical_failure(caster, spell_data: Dict) -> Dict:
        """
        Handle critical failure effects
        
        Possible outcomes:
        - Essence backlash (take damage)
        - Essence corruption (lose extra essence)
        - Wild magic surge (random effect)
        """
        outcomes = ['backlash', 'corruption', 'wild_surge']
        outcome = random.choice(outcomes)
        
        composition = spell_data.get('composition', {})
        total = sum(composition.values())
        
        result = {
            'outcome': outcome,
        }
        
        if outcome == 'backlash':
            # Take damage equal to spell power
            damage = total // 5
            if hasattr(caster, 'stats'):
                caster.stats.take_damage(damage)
            result['damage'] = damage
            result['message'] = f"The spell backfires! {caster.name} takes {damage} damage!"
        
        elif outcome == 'corruption':
            # Lose extra essence
            if hasattr(caster, 'inventory'):
                for element, amount in composition.items():
                    caster.inventory.remove_essence(element, amount * 0.5)
            result['message'] = f"Essence spirals out of control! Extra essence lost!"
        
        elif outcome == 'wild_surge':
            # Random wild magic effect
            surges = [
                "A burst of colorful sparks erupts!",
                "The caster's hair stands on end!",
                "A small animal appears and quickly runs away!",
                "Everything nearby smells like roses for a moment.",
                "The caster hiccups uncontrollably for a few seconds.",
            ]
            result['message'] = random.choice(surges)
        
        return result


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def cast_spell_full(caster, 
                    spell_synset: str,
                    spell_data: Dict,
                    target=None,
                    advantage: bool = False,
                    disadvantage: bool = False) -> Dict:
    """
    Complete spell casting with all D&D mechanics
    
    This is the main function to use for spell casting
    
    Args:
        caster: Entity casting the spell (must have inventory, stats)
        spell_synset: Spell identifier
        spell_data: Spell definition dict
        target: Target entity (if applicable)
        advantage: Cast with advantage
        disadvantage: Cast with disadvantage
        
    Returns:
        Dict with complete results
    """
    # Check if we know the spell
    if not caster.inventory.knows_spell(spell_synset):
        return {
            'success': False,
            'result': SpellResult.SPELL_UNKNOWN,
            'message': f"{caster.name} doesn't know this spell!"
        }
    
    # Check essence cost
    base_cost = spell_data.get('composition', {})
    if not caster.inventory.has_essence(base_cost):
        return {
            'success': False,
            'result': SpellResult.INSUFFICIENT_ESSENCE,
            'message': f"{caster.name} lacks the essence to cast this spell!",
            'needed': base_cost,
            'have': caster.inventory.essences
        }
    
    # Calculate DC
    spell_dc = SpellCaster.calculate_spell_dc(spell_data)
    
    # Gather caster stats
    caster_stats = {
        'intelligence': caster.stats.intelligence,
        'wisdom': caster.stats.wisdom,
        'magic_power': caster.stats.magic_power,
        'level': getattr(caster, 'level', 1)
    }
    
    # Roll the check!
    total_roll, result = SpellCaster.roll_spell_check(
        caster_stats, 
        spell_dc, 
        advantage, 
        disadvantage
    )
    
    # Calculate actual essence cost
    actual_cost = SpellCaster.calculate_essence_cost(spell_data, result)
    
    # Spend essence
    for element, amount in actual_cost.items():
        caster.inventory.remove_essence(element, amount)
    
    # Build response
    response = {
        'success': result in [SpellResult.SUCCESS, SpellResult.CRITICAL_SUCCESS, SpellResult.PARTIAL_SUCCESS],
        'result': result,
        'spell': spell_data.get('word', spell_synset),
        'caster': caster.name,
        'roll': total_roll,
        'dc': spell_dc,
        'essence_spent': actual_cost,
    }
    
    # Handle critical failure
    if result == SpellResult.CRITICAL_FAILURE:
        failure_result = SpellCaster.handle_critical_failure(caster, spell_data)
        response.update(failure_result)
        return response
    
    # Calculate and apply effects
    if result != SpellResult.FAILURE:
        power = SpellCaster.calculate_spell_power(spell_data, result, caster_stats)
        effect_result = SpellCaster.apply_spell_effect(spell_data, power, caster, target)
        response.update(effect_result)
    else:
        response['message'] = f"{caster.name}'s spell fizzles out!"
    
    return response


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SPELL CASTING SYSTEM")
    print("=" * 70)
    
    # Mock objects for testing
    class MockStats:
        def __init__(self):
            self.intelligence = 16  # +3 modifier
            self.wisdom = 14        # +2 modifier
            self.magic_power = 30
            self.magic_defense = 10
            self.current_health = 100
            self.max_health = 100
        
        def take_damage(self, amount):
            self.current_health -= amount
        
        def heal(self, amount):
            self.current_health = min(self.max_health, self.current_health + amount)
        
        def is_alive(self):
            return self.current_health > 0
    
    class MockInventory:
        def __init__(self):
            self.essences = {'fire': 500, 'water': 200, 'earth': 200, 'air': 200}
            self.grimoire = {'fireball.n.01', 'heal.v.01'}
        
        def knows_spell(self, synset):
            return synset in self.grimoire
        
        def has_essence(self, requirements):
            for elem, amount in requirements.items():
                if self.essences.get(elem, 0) < amount:
                    return False
            return True
        
        def remove_essence(self, element, amount):
            self.essences[element] -= amount
    
    class MockCaster:
        def __init__(self, name, intelligence=16, wisdom=14):
            self.name = name
            self.stats = MockStats()
            self.stats.intelligence = intelligence
            self.stats.wisdom = wisdom
            self.inventory = MockInventory()
            self.level = 5
    
    # Create caster and target
    wizard = MockCaster("Gandalf", intelligence=18, wisdom=16)
    goblin = MockCaster("Goblin", intelligence=8, wisdom=8)
    
    # Define a spell
    fireball = {
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
    
    print("\n🧙 Wizard Stats:")
    print(f"  Intelligence: {wizard.stats.intelligence} (+{(wizard.stats.intelligence-10)//2})")
    print(f"  Wisdom: {wizard.stats.wisdom} (+{(wizard.stats.wisdom-10)//2})")
    print(f"  Level: {wizard.level}")
    print(f"  Essences: {wizard.inventory.essences}")
    
    print("\n👹 Target Stats:")
    print(f"  HP: {goblin.stats.current_health}/{goblin.stats.max_health}")
    print(f"  Magic Defense: {goblin.stats.magic_defense}")
    
    # Calculate spell DC
    spell_dc = SpellCaster.calculate_spell_dc(fireball)
    tier = SpellCaster.calculate_spell_tier(sum(fireball['composition'].values()))
    
    print("\n🔥 Fireball Spell:")
    print(f"  Total Essence Cost: {sum(fireball['composition'].values())}")
    print(f"  Tier: {tier}")
    print(f"  Difficulty Class (DC): {spell_dc}")
    
    # Cast spell multiple times to see different outcomes
    print("\n" + "=" * 70)
    print("CASTING ATTEMPTS")
    print("=" * 70)
    
    for i in range(5):
        print(f"\n🎲 Attempt {i+1}:")
        
        # Reset goblin health
        goblin.stats.current_health = 100
        
        result = cast_spell_full(wizard, 'fireball.n.01', fireball, target=goblin)
        
        print(f"  Roll: {result.get('roll', '?')} vs DC {result.get('dc', '?')}")
        print(f"  Result: {result['result'].value}")
        print(f"  Essence spent: {result.get('essence_spent', {})}")
        
        if result['success']:
            if 'damage' in result:
                print(f"  ⚔️  Damage: {result['damage']}")
                print(f"  🎯 Target HP: {goblin.stats.current_health}/{goblin.stats.max_health}")
            if 'power' in result:
                print(f"  ⚡ Power: {result['power']:.1f}")
        else:
            if 'message' in result:
                print(f"  💬 {result['message']}")
    
    # Test with different stats
    print("\n" + "=" * 70)
    print("STAT COMPARISON")
    print("=" * 70)
    
    novice = MockCaster("Novice", intelligence=10, wisdom=10)
    novice.level = 1
    
    print("\n📊 Novice Wizard (INT 10, WIS 10, Level 1):")
    successes = 0
    for _ in range(20):
        result = cast_spell_full(novice, 'fireball.n.01', fireball, target=goblin)
        if result['success']:
            successes += 1
    print(f"  Success rate: {successes}/20 ({successes*5}%)")
    
    expert = MockCaster("Expert", intelligence=20, wisdom=18)
    expert.level = 10
    
    print("\n📊 Expert Wizard (INT 20, WIS 18, Level 10):")
    successes = 0
    criticals = 0
    for _ in range(20):
        result = cast_spell_full(expert, 'fireball.n.01', fireball, target=goblin)
        if result['success']:
            successes += 1
        if result['result'] == SpellResult.CRITICAL_SUCCESS:
            criticals += 1
    print(f"  Success rate: {successes}/20 ({successes*5}%)")
    print(f"  Critical rate: {criticals}/20 ({criticals*5}%)")
    
    print("\n" + "=" * 70)
    print("✅ Spell casting system complete!")
    print("=" * 70)
    
    print("\n💡 Features:")
    print("  - D&D-style d20 + modifiers vs DC")
    print("  - Intelligence and Wisdom affect success")
    print("  - Critical successes (2x power, 50% cost)")
    print("  - Critical failures (backfire, corruption, wild magic)")
    print("  - Partial successes (reduced effect)")
    print("  - Spell tiers (cantrip to legendary)")
    print("  - Advantage/disadvantage system")
    print("  - Level-based proficiency bonus")
