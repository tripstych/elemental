"""
Elemental Essence & Solvent System
An alchemical magic system where you dissolve objects to extract essences for spellcasting
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from spell_system import GameObject, Creature, TerrainObject, SpellDictionary, SpellExecutor
import json


# ============================================================================
# SOLVENT DEFINITIONS
# ============================================================================

SOLVENTS = {
    "aqua_ignis": {
        "name": "Aqua Ignis",
        "extracts": ["fire", "air"],
        "strength": 0.8,
        "description": "Boiling alchemical water that pulls heat and vapor from matter. The steam rises carrying the volatile essences.",
        "color": "shimmering orange",
        "rarity": "common"
    },
    
    "oleum_terra": {
        "name": "Oleum Terra", 
        "extracts": ["earth", "water"],
        "strength": 0.9,
        "description": "Thick mineral oil that dissolves stone and moisture. It flows like liquid earth.",
        "color": "muddy brown",
        "rarity": "common"
    },
    
    "aether_flux": {
        "name": "Aether Flux",
        "extracts": ["air", "fire"],
        "strength": 0.95,
        "description": "Ethereal liquid that extracts breath and flame. Shimmers with invisible currents.",
        "color": "pale blue shimmer",
        "rarity": "uncommon"
    },
    
    "aqua_profundis": {
        "name": "Aqua Profundis",
        "extracts": ["water", "earth"],
        "strength": 0.95,
        "description": "Deep water from underground wells, heavy with dissolved minerals.",
        "color": "dark blue-green",
        "rarity": "uncommon"
    },
    
    "alkahest": {
        "name": "Alkahest",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "The legendary universal solvent. Dissolves all matter completely, extracting every trace of elemental essence.",
        "color": "clear as diamond",
        "rarity": "legendary"
    },
    
    "void_essence": {
        "name": "Void Essence",
        "extracts": [],
        "adds": (-10, -10, -10, -10),
        "strength": 1.0,
        "description": "Emptiness made liquid. It doesn't extract - it drains, pulling elemental power into nothingness.",
        "color": "impossible darkness",
        "rarity": "rare"
    },
    
    "prima_materia": {
        "name": "Prima Materia",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 0.6,
        "transmutes": True,
        "description": "The primordial substance. Extracts essences but also transforms the object's nature.",
        "color": "shifting prismatic",
        "rarity": "rare"
    }
}


# ============================================================================
# OBJECT ESSENCE COMPOSITIONS
# ============================================================================

OBJECT_ESSENCES = {
    # Natural materials
    'wood': {'fire': 30, 'water': 10, 'earth': 15, 'air': 5},
    'stone': {'fire': 5, 'water': 5, 'earth': 50, 'air': 3},
    'water': {'fire': 0, 'water': 40, 'earth': 5, 'air': 10},
    'ice': {'fire': 0, 'water': 50, 'earth': 10, 'air': 5},
    'steam': {'fire': 15, 'water': 40, 'earth': 2, 'air': 30},
    'cloud': {'fire': 5, 'water': 35, 'earth': 2, 'air': 45},
    
    # Fire sources
    'flame': {'fire': 45, 'water': 0, 'earth': 3, 'air': 20},
    'ember': {'fire': 35, 'water': 0, 'earth': 8, 'air': 12},
    'ash': {'fire': 10, 'water': 5, 'earth': 20, 'air': 15},
    'coal': {'fire': 40, 'water': 2, 'earth': 25, 'air': 8},
    'lava': {'fire': 55, 'water': 5, 'earth': 45, 'air': 8},
    
    # Earth materials
    'clay': {'fire': 3, 'water': 15, 'earth': 40, 'air': 5},
    'sand': {'fire': 8, 'water': 5, 'earth': 35, 'air': 20},
    'mud': {'fire': 2, 'water': 25, 'earth': 35, 'air': 5},
    'crystal': {'fire': 15, 'water': 20, 'earth': 30, 'air': 25},
    'metal': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'ore': {'fire': 20, 'water': 8, 'earth': 45, 'air': 5},
    
    # Organic materials
    'bone': {'fire': 8, 'water': 12, 'earth': 35, 'air': 8},
    'blood': {'fire': 15, 'water': 40, 'earth': 8, 'air': 10},
    'flesh': {'fire': 12, 'water': 35, 'earth': 20, 'air': 8},
    'scale': {'fire': 10, 'water': 15, 'earth': 30, 'air': 5},
    'feather': {'fire': 5, 'water': 8, 'earth': 5, 'air': 35},
    
    # Plant materials
    'leaf': {'fire': 15, 'water': 20, 'earth': 10, 'air': 15},
    'flower': {'fire': 10, 'water': 25, 'earth': 8, 'air': 20},
    'root': {'fire': 8, 'water': 18, 'earth': 30, 'air': 5},
    'bark': {'fire': 20, 'water': 10, 'earth': 22, 'air': 8},
    'sap': {'fire': 12, 'water': 30, 'earth': 15, 'air': 8},
    
    # Magical materials
    'moonstone': {'fire': 5, 'water': 35, 'earth': 20, 'air': 30},
    'sunstone': {'fire': 45, 'water': 8, 'earth': 20, 'air': 20},
    'stardust': {'fire': 25, 'water': 25, 'earth': 25, 'air': 25},
    'dragon_scale': {'fire': 50, 'water': 10, 'earth': 35, 'air': 25},
    'phoenix_feather': {'fire': 55, 'water': 5, 'earth': 5, 'air': 50},
    'unicorn_horn': {'fire': 15, 'water': 45, 'earth': 25, 'air': 35},
    
    # Default
    'generic': {'fire': 10, 'water': 10, 'earth': 10, 'air': 10}
}


# ============================================================================
# ============================================================================
# ESSENCE EXTRACTION
# ============================================================================

def get_object_essence(obj: GameObject) -> Dict[str, int]:
    """Get the elemental composition of an object"""
    obj_type = 'generic'
    
    if hasattr(obj, 'terrain_type'):
        obj_type = obj.terrain_type
    elif hasattr(obj, 'material_type'):
        obj_type = obj.material_type
    elif hasattr(obj, 'object_type'):
        obj_type = obj.object_type
    
    return OBJECT_ESSENCES.get(obj_type, OBJECT_ESSENCES['generic']).copy()


# ============================================================================
# ESSENCE REFINEMENT
# ============================================================================

def mix_essences(essence1: Dict[str, float], essence2: Dict[str, float]) -> Dict[str, float]:
    """Combine two essence samples"""
    mixed = {}
    for element in ['fire', 'water', 'earth', 'air']:
        mixed[element] = essence1.get(element, 0) + essence2.get(element, 0)
    return mixed


# ============================================================================
# DEMONSTRATION
# ============================================================================

def demo_alchemy_system():
    """Demonstrate the complete alchemy system"""
    print("=" * 80)
    print("ELEMENTAL ALCHEMY SYSTEM DEMO")
    print("=" * 80)
    print()
    
    # Setup
    inventory = AlchemistInventory()
    dictionary = SpellDictionary('elemental_spells.json')
    spellcaster = EssenceSpellcaster(inventory, dictionary)
    
    player = Creature("Alchemist", hp=100)
    goblin = Creature("Goblin", hp=50)
    
    print("🧙 The Alchemist's Journey")
    print("-" * 80)
    print(f"Starting essences: {inventory.essences}")
    print(f"Starting solvents: {inventory.solvents}")
    print()
    
    # Scene 1: Gathering materials
    print("SCENE 1: Gathering Materials")
    print("-" * 80)
    
    campfire = TerrainObject("Campfire", "flame", hp=20)
    dead_tree = TerrainObject("Dead Oak", "wood", hp=100)
    boulder = TerrainObject("Boulder", "stone", hp=200)
    
    inventory.add_object(campfire)
    inventory.add_object(dead_tree)
    inventory.add_object(boulder)
    
    print("You gather materials from the forest:")
    for obj in inventory.objects:
        essence = get_object_essence(obj)
        print(f"  • {obj.name}: {essence}")
    print()
    
    # Scene 2: Extracting essences
    print("SCENE 2: Essence Extraction")
    print("-" * 80)
    
    print("Dissolving campfire in Aqua Ignis...")
    success, message, extracted = dissolve_object(inventory, campfire, "aqua_ignis")
    print(message)
    print()
    
    print("Dissolving dead oak in Aqua Ignis...")
    success, message, extracted = dissolve_object(inventory, dead_tree, "aqua_ignis")
    print(message)
    print()
    
    print(f"Current essences: {inventory.essences}")
    print()
    
    # Scene 3: Learning spells
    print("SCENE 3: Studying Spellcraft")
    print("-" * 80)
    
    print("You study your grimoire and learn basic spells...")
    for word in ["kata", "krata", "lumno"]:
        success, message = spellcaster.study_spell(word)
        print(message)
        print()
    
    print(f"Grimoire: {inventory.grimoire}")
    print()
    
    # Scene 4: Casting a spell
    print("SCENE 4: Combat!")
    print("-" * 80)
    
    print(f"🧙 {player.name}: {player.hp} HP")
    print(f"👹 {goblin.name}: {goblin.hp} HP")
    print()
    
    print("Attempting to cast 'krata' (Fireball)...")
    success, messages = spellcaster.cast_spell("krata", player, [goblin])
    
    if success:
        for msg in messages:
            print(f"  {msg}")
    else:
        for msg in messages:
            print(f"  ❌ {msg}")
    print()
    
    print(f"Remaining essences: {inventory.essences}")
    print()
    
    # Scene 5: Need more essence - dissolve boulder
    print("SCENE 5: Gathering More Essence")
    print("-" * 80)
    
    print("You need more essence! Dissolving boulder in Oleum Terra...")
    success, message, extracted = dissolve_object(inventory, boulder, "oleum_terra")
    print(message)
    print()
    
    print(f"Current essences: {inventory.essences}")
    print()
    
    # Scene 6: Spell transformation
    print("SCENE 6: Alchemical Transformation")
    print("-" * 80)
    
    print("Attempting to transform 'kata' (ignite) by adding 13 fire...")
    success, message, new_word = spellcaster.transform_spell("kata", fire=13)
    print(message)
    print()
    
    if new_word:
        print(f"New spell discovered: '{new_word}'")
        print(f"Updated grimoire: {inventory.grimoire}")
    print()
    
    # Scene 7: Essence distillation
    print("SCENE 7: Essence Refinement")
    print("-" * 80)
    
    print("Distilling essences to concentrate fire...")
    success, message = distill_essence(inventory, "fire", sacrifice_amount=5, efficiency=0.6)
    print(message)
    print()
    
    print(f"Final essences: {inventory.essences}")
    print()
    
    print("=" * 80)
    print("ALCHEMY COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  Spells learned: {len(inventory.grimoire)}")
    print(f"  Solvents remaining: {inventory.solvents}")
    print(f"  Essence reserves: {inventory.essences}")


# ESSENCE DATA ONLY - See seed/animate.py for actual inventory management
