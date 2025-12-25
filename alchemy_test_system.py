#!/usr/bin/env python3
"""
Integrated Alchemy Test System
Tests the full gameplay loop: gather objects → dissolve → extract essences → transform → cast spells
"""

import json
import sys
from pathlib import Path

# ============================================================================
# MOCK IMPORTS (since we can't import the full system easily)
# ============================================================================

class SimpleInventory:
    """Simplified alchemist inventory for testing"""
    def __init__(self):
        self.essences = {'fire': 0.0, 'water': 0.0, 'earth': 0.0, 'air': 0.0}
        self.grimoire = set()  # Known spells
        self.objects = []  # Physical objects in inventory
        
    def add_essence(self, element, amount):
        self.essences[element] += amount
        
    def can_afford(self, cost):
        """Check if we have enough essences"""
        for elem in ['fire', 'water', 'earth', 'air']:
            if self.essences[elem] < cost.get(elem, 0):
                return False
        return True
    
    def spend_essence(self, cost):
        """Spend essences"""
        for elem in ['fire', 'water', 'earth', 'air']:
            self.essences[elem] -= cost.get(elem, 0)
    
    def learn_spell(self, word):
        self.grimoire.add(word)
    
    def add_object(self, obj):
        self.objects.append(obj)

class SimpleObject:
    """Simple game object with essence composition"""
    def __init__(self, name, essence_composition):
        self.name = name
        self.essence = essence_composition  # {fire, water, earth, air}

# ============================================================================
# LOAD GAME DATA
# ============================================================================

def load_spells(filepath='elemental_build_data_modifiers.json'):
    """Load spell definitions"""
    with open(filepath, 'r') as f:
        return json.load(f)

def load_objects(filepath='game_objects_wordnet.json'):
    """Load game objects"""
    with open(filepath, 'r') as f:
        objects_data = json.load(f)
    
    # For now, just return first 20 for testing
    return objects_data[:20]

def load_materials():
    """Material → essence mappings"""
    return {
        'wood': {'fire': 30, 'water': 10, 'earth': 15, 'air': 5},
        'stone': {'fire': 5, 'water': 5, 'earth': 50, 'air': 3},
        'metal': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
        'steel': {'fire': 30, 'water': 5, 'earth': 38, 'air': 5},
        'iron': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
        'glass': {'fire': 20, 'water': 12, 'earth': 25, 'air': 20},
        'cloth': {'fire': 20, 'water': 15, 'earth': 8, 'air': 15},
        'leather': {'fire': 18, 'water': 20, 'earth': 15, 'air': 8},
        'organic': {'fire': 12, 'water': 35, 'earth': 20, 'air': 8},
        'liquid': {'fire': 5, 'water': 40, 'earth': 5, 'air': 10},
        'bone': {'fire': 8, 'water': 12, 'earth': 35, 'air': 8},
        'gold': {'fire': 35, 'water': 8, 'earth': 35, 'air': 8},
        'silver': {'fire': 20, 'water': 12, 'earth': 30, 'air': 10},
    }

# ============================================================================
# SOLVENTS
# ============================================================================

SOLVENTS = {
    "aqua_ignis": {
        "name": "Aqua Ignis",
        "extracts": ["fire", "air"],
        "strength": 0.8,
        "description": "Boiling alchemical water",
    },
    "oleum_terra": {
        "name": "Oleum Terra", 
        "extracts": ["earth", "water"],
        "strength": 0.9,
        "description": "Thick mineral oil",
    },
    "alkahest": {
        "name": "Alkahest",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal solvent",
    },
    "void_essence": {
        "name": "Void Essence",
        "extracts": [],
        "drains": {'fire': 10, 'water': 10, 'earth': 10, 'air': 10},
        "description": "Drains elemental power",
    },
}

# ============================================================================
# CORE MECHANICS
# ============================================================================

def dissolve_object(obj, solvent_name, inventory):
    """
    Dissolve an object in a solvent to extract essences
    
    Returns: (success, message, extracted_essences)
    """
    if solvent_name not in SOLVENTS:
        return False, f"Unknown solvent: {solvent_name}", {}
    
    solvent = SOLVENTS[solvent_name]
    extracted = {}
    messages = []
    
    messages.append(f"\n💧 Dissolving {obj.name} in {solvent['name']}...")
    messages.append(f"   {solvent['description']}")
    
    # Void essence drains
    if solvent_name == "void_essence":
        for elem in ['fire', 'water', 'earth', 'air']:
            drain = solvent['drains'][elem]
            extracted[elem] = -drain
            messages.append(f"   Drained -{drain} {elem}")
    else:
        # Normal extraction
        for elem in solvent['extracts']:
            amount = obj.essence[elem] * solvent['strength']
            extracted[elem] = amount
            inventory.add_essence(elem, amount)
            messages.append(f"   Extracted {amount:.1f} {elem}")
    
    messages.append(f"\n✅ {obj.name} consumed")
    
    return True, "\n".join(messages), extracted

def calculate_transformation(current_comp, target_comp):
    """
    Calculate what essences to add/remove to transform object into spell
    
    Returns: (additions, subtractions)
    """
    additions = {}
    subtractions = {}
    
    for elem in ['fire', 'water', 'earth', 'air']:
        current = current_comp.get(elem, 0)
        target = target_comp.get(elem, 0)
        diff = target - current
        
        if diff > 0:
            additions[elem] = diff
        elif diff < 0:
            subtractions[elem] = abs(diff)
    
    return additions, subtractions

def transform_object_to_spell(obj, target_spell, inventory):
    """
    Transform an object into a spell by modifying its elemental composition
    
    Returns: (success, message, spell_word)
    """
    messages = []
    messages.append(f"\n🔮 TRANSFORMATION: {obj.name} → {target_spell['word']}")
    messages.append(f"   Target: {target_spell['definition']}")
    
    # Calculate what we need
    additions, subtractions = calculate_transformation(obj.essence, target_spell['composition'])
    
    messages.append(f"\n   Current: fire={obj.essence['fire']}, water={obj.essence['water']}, earth={obj.essence['earth']}, air={obj.essence['air']}")
    messages.append(f"   Target:  fire={target_spell['composition']['fire']}, water={target_spell['composition']['water']}, earth={target_spell['composition']['earth']}, air={target_spell['composition']['air']}")
    
    if additions:
        messages.append(f"\n   Need to ADD:")
        for elem, amount in additions.items():
            messages.append(f"      +{amount} {elem}")
    
    if subtractions:
        messages.append(f"\n   Need to REMOVE:")
        for elem, amount in subtractions.items():
            messages.append(f"      -{amount} {elem}")
    
    # Check if we can afford additions
    cost = {elem: additions.get(elem, 0) for elem in ['fire', 'water', 'earth', 'air']}
    
    if not inventory.can_afford(cost):
        shortage = []
        for elem, needed in cost.items():
            if needed > 0:
                have = inventory.essences[elem]
                if have < needed:
                    shortage.append(f"{elem}: need {needed}, have {have:.1f}")
        
        messages.append(f"\n❌ FAILED: Not enough essence!")
        messages.append(f"   Shortage: {', '.join(shortage)}")
        return False, "\n".join(messages), None
    
    # Pay the cost
    inventory.spend_essence(cost)
    messages.append(f"\n✅ Transformation successful!")
    messages.append(f"   Consumed: {', '.join(f'{v} {k}' for k, v in cost.items() if v > 0)}")
    
    # Learn the spell
    inventory.learn_spell(target_spell['word'])
    messages.append(f"   Learned spell: '{target_spell['word']}'")
    
    return True, "\n".join(messages), target_spell['word']

def cast_spell(spell_word, spells, inventory):
    """
    Cast a spell (checking essence cost)
    
    Returns: (success, message)
    """
    # Find spell
    spell = None
    for spell_data in spells.values():
        if spell_data['word'] == spell_word:
            spell = spell_data
            break
    
    if not spell:
        return False, f"Unknown spell: {spell_word}"
    
    if spell_word not in inventory.grimoire:
        return False, f"You don't know the spell '{spell_word}'!"
    
    # Check cost
    cost = spell['composition']
    if not inventory.can_afford(cost):
        shortage = []
        for elem in ['fire', 'water', 'earth', 'air']:
            needed = cost[elem]
            have = inventory.essences[elem]
            if have < needed:
                shortage.append(f"{elem}: need {needed}, have {have:.1f}")
        
        return False, f"Not enough essence! {', '.join(shortage)}"
    
    # Pay cost
    inventory.spend_essence(cost)
    
    message = f"\n⚡ CASTING: '{spell_word}'\n"
    message += f"   {spell['spell_effect']['description']}\n"
    message += f"   Cost: fire={cost['fire']}, water={cost['water']}, earth={cost['earth']}, air={cost['air']}"
    
    return True, message

# ============================================================================
# TEST SCENARIOS
# ============================================================================

def test_scenario_1_basic_fireball():
    """Test: Find rock, transform to fireball, cast it"""
    print("=" * 70)
    print("SCENARIO 1: BASIC FIREBALL")
    print("=" * 70)
    
    # Setup
    spells = load_spells()
    materials = load_materials()
    inventory = SimpleInventory()
    
    # Create a rock object
    rock = SimpleObject("Rock", materials['stone'].copy())
    
    print(f"\n📦 Found: {rock.name}")
    print(f"   Essence: {rock.essence}")
    
    # Get fireball spell
    fireball = spells['fireball.n.01']
    
    # Calculate transformation
    additions, subtractions = calculate_transformation(rock.essence, fireball['composition'])
    
    print(f"\n🎯 Target spell: '{fireball['word']}' (Fireball)")
    print(f"   Target essence: {fireball['composition']}")
    print(f"\n   To transform:")
    print(f"      Need to ADD: {additions}")
    print(f"      Need to REMOVE: {subtractions}")
    
    # We need fire essence! Dissolve something fiery
    print(f"\n💭 We need fire essence... let's find some wood to burn!")
    
    # Create campfire
    campfire = SimpleObject("Campfire", {'fire': 45, 'water': 0, 'earth': 3, 'air': 20})
    
    # Dissolve campfire in Aqua Ignis (extracts fire + air)
    success, msg, extracted = dissolve_object(campfire, "aqua_ignis", inventory)
    print(msg)
    
    print(f"\n📊 Current essences: {inventory.essences}")
    
    # Now try transformation
    success, msg, spell_word = transform_object_to_spell(rock, fireball, inventory)
    print(msg)
    
    if success:
        print(f"\n📊 Remaining essences: {inventory.essences}")
        
        # Try to cast it
        print(f"\n" + "=" * 70)
        print("ATTEMPTING TO CAST FIREBALL")
        print("=" * 70)
        
        success, msg = cast_spell(spell_word, spells, inventory)
        print(msg)
        
        if success:
            print(f"\n📊 Essences after casting: {inventory.essences}")
            print(f"\n🎉 SUCCESS! Full cycle complete!")
        else:
            print(f"\n❌ Cast failed: {msg}")
    
    print("\n" + "=" * 70)

def test_scenario_2_heal_to_steam():
    """Test: Transform heal spell into steam by adding fire"""
    print("\n\n" + "=" * 70)
    print("SCENARIO 2: HEAL → STEAM TRANSFORMATION")
    print("=" * 70)
    
    spells = load_spells()
    materials = load_materials()
    inventory = SimpleInventory()
    
    # Start with water-rich object
    water_source = SimpleObject("Spring Water", {'fire': 0, 'water': 60, 'earth': 5, 'air': 10})
    
    print(f"\n📦 Found: {water_source.name}")
    print(f"   Essence: {water_source.essence}")
    
    # Target: heal spell first
    heal = spells['heal.v.01']
    
    print(f"\n🎯 Step 1: Transform to '{heal['word']}' (Heal)")
    print(f"   Target: {heal['composition']}")
    
    # Calculate what we need
    additions, subtractions = calculate_transformation(water_source.essence, heal['composition'])
    print(f"   Need: ADD {additions}, REMOVE {subtractions}")
    
    # Give player some starting essences for demo
    inventory.essences = {'fire': 50, 'water': 10, 'earth': 20, 'air': 20}
    print(f"\n📊 Starting essences: {inventory.essences}")
    
    # Transform to heal
    success, msg, heal_word = transform_object_to_spell(water_source, heal, inventory)
    print(msg)
    
    if success:
        print(f"\n📊 Essences after heal transform: {inventory.essences}")
        
        # Now transform heal → steam
        steam = spells['steam.n.01']
        print(f"\n🎯 Step 2: We know '{heal_word}', now add fire to make steam!")
        print(f"   Heal:  {heal['composition']}")
        print(f"   Steam: {steam['composition']}")
        
        fire_diff = steam['composition']['fire'] - heal['composition']['fire']
        print(f"   Need +{fire_diff} fire to transform heal → steam")
        
        # Create new object with heal composition, then transform to steam
        heal_object = SimpleObject("Heal Essence", heal['composition'].copy())
        success2, msg2, steam_word = transform_object_to_spell(heal_object, steam, inventory)
        print(msg2)
        
        if success2:
            print(f"\n🎉 SUCCESS! Healing water became scalding steam!")
            print(f"📊 Final essences: {inventory.essences}")

def test_scenario_3_object_catalog():
    """Show sample objects and what spells they could become"""
    print("\n\n" + "=" * 70)
    print("SCENARIO 3: OBJECT → SPELL POSSIBILITIES")
    print("=" * 70)
    
    spells = load_spells()
    materials = load_materials()
    
    test_objects = [
        ("Boulder", materials['stone']),
        ("Iron Sword", materials['iron']),
        ("Oak Staff", materials['wood']),
        ("Glass Vial", materials['glass']),
        ("Bone Dagger", materials['bone']),
    ]
    
    # Pick 3 target spells
    target_spells = [
        ('fireball.n.01', "Fireball"),
        ('shield.n.01', "Shield"),
        ('heal.v.01', "Heal"),
    ]
    
    print("\n📋 TRANSFORMATION COSTS:")
    print("=" * 70)
    
    for obj_name, obj_essence in test_objects:
        print(f"\n🔹 {obj_name}: {obj_essence}")
        
        for spell_key, spell_name in target_spells:
            spell = spells[spell_key]
            additions, subtractions = calculate_transformation(obj_essence, spell['composition'])
            
            total_cost = sum(additions.values())
            print(f"   → {spell_name:12s}: +{total_cost:3.0f} essence total  {additions}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all test scenarios"""
    print("\n🧪 ALCHEMY SYSTEM TEST SUITE")
    print("=" * 70)
    print("Testing: Object gathering → Dissolution → Transformation → Casting")
    print("=" * 70)
    
    try:
        test_scenario_1_basic_fireball()
        test_scenario_2_heal_to_steam()
        test_scenario_3_object_catalog()
        
        print("\n\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: Could not find data file: {e}")
        print("Make sure you have:")
        print("  - elemental_build_data_modifiers.json")
        print("  - game_objects_wordnet.json")
        print("in the same directory")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()