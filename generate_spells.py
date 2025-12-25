#!/usr/bin/env python3
"""
Spell Generator - Create expanded spell database
Generates spells across:
- All 4 elements (fire, water, earth, air)
- Power tiers (minor, standard, major, legendary)
- Effect types (damage, heal, buff, debuff, summon, transform, utility)
"""

import json
from pathlib import Path

# ============================================================================
# SPELL GENERATION PATTERNS
# ============================================================================

def generate_spells():
    """Generate comprehensive spell database"""
    
    spells = {}
    
    # ========================================================================
    # FIRE SPELLS - Damage, burning, destruction
    # ========================================================================
    
    # Minor fire spells (20-35 fire)
    spells['ember.n.01'] = {
        "word": "kata-min",
        "spirit": "fire",
        "composition": {"fire": 25, "water": 3, "earth": 5, "air": 5},
        "definition": "small glowing coal",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": "fire * 0.6",
            "element": "fire",
            "description": "A tiny ember floats toward the target, singeing them."
        }
    }
    
    spells['scorch.v.01'] = {
        "word": "skrat",
        "spirit": "fire",
        "composition": {"fire": 35, "water": 5, "earth": 8, "air": 10},
        "definition": "burn the surface",
        "spell_effect": {
            "type": "apply_status",
            "target": "Enemy",
            "status": "scorched",
            "duration": 3,
            "damage_per_turn": 5,
            "description": "Intense heat scorches the target's exterior."
        }
    }
    
    # Standard fire spells (40-50 fire)
    spells['immolate.v.01'] = {
        "word": "kratik",
        "spirit": "fire",
        "composition": {"fire": 50, "water": 3, "earth": 8, "air": 15},
        "definition": "consume in flames",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": "fire * 0.9",
            "element": "fire",
            "description": "Flames engulf the target completely, burning intensely!"
        }
    }
    
    spells['flame_burst.n.01'] = {
        "word": "kratok",
        "spirit": "fire",
        "composition": {"fire": 48, "water": 5, "earth": 12, "air": 20},
        "definition": "explosive flame",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 3,
            "effects": [
                {"type": "damage", "amount": 20, "to": "all", "element": "fire"}
            ],
            "description": "A burst of flame explodes outward in all directions!"
        }
    }
    
    # Major fire spells (55-63 fire)
    spells['inferno.n.01'] = {
        "word": "kratesh-kai",
        "spirit": "fire",
        "composition": {"fire": 60, "water": 3, "earth": 15, "air": 25},
        "definition": "raging fire",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 6,
            "effects": [
                {"type": "damage", "amount": "fire * 0.7", "to": "all", "element": "fire"},
                {"type": "apply_status", "status": "burning", "to": "all", "duration": 5}
            ],
            "description": "A towering inferno erupts, consuming everything in flames!"
        }
    }
    
    spells['solar_flare.n.01'] = {
        "word": "skatresh",
        "spirit": "fire",
        "composition": {"fire": 63, "water": 5, "earth": 10, "air": 40},
        "definition": "blinding solar eruption",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 8,
            "effects": [
                {"type": "damage", "amount": 40, "to": "all", "element": "fire"},
                {"type": "apply_status", "status": "blinded", "to": "all", "duration": 3}
            ],
            "description": "Blinding light and searing heat erupt like the sun itself!"
        }
    }
    
    # ========================================================================
    # WATER SPELLS - Healing, cold, flow
    # ========================================================================
    
    # Minor water spells (20-35 water)
    spells['mist.n.01'] = {
        "word": "lumfi",
        "spirit": "water",
        "composition": {"fire": 5, "water": 25, "earth": 5, "air": 20},
        "definition": "fine water droplets",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 4,
            "effects": [
                {"type": "apply_status", "status": "obscured", "to": "all", "duration": 3}
            ],
            "description": "A thick mist rolls in, obscuring vision."
        }
    }
    
    spells['soothe.v.01'] = {
        "word": "lumna",
        "spirit": "water",
        "composition": {"fire": 5, "water": 30, "earth": 10, "air": 12},
        "definition": "calm and relieve",
        "spell_effect": {
            "type": "heal",
            "target": "Ally",
            "amount": "water * 0.5",
            "description": "Gentle waters ease pain and suffering."
        }
    }
    
    # Standard water spells (40-50 water)
    spells['ice_shard.n.01'] = {
        "word": "woukat",
        "spirit": "water",
        "composition": {"fire": 3, "water": 45, "earth": 18, "air": 15},
        "definition": "sharp ice projectile",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": "water * 0.7",
            "element": "water",
            "description": "A jagged shard of ice pierces the target!"
        }
    }
    
    spells['restore.v.01'] = {
        "word": "lumresh",
        "spirit": "water",
        "composition": {"fire": 10, "water": 48, "earth": 20, "air": 15},
        "definition": "return to full health",
        "spell_effect": {
            "type": "heal",
            "target": "Ally",
            "amount": "water * 0.8",
            "remove_status": ["poison", "burning", "bleeding"],
            "description": "Pure waters wash over wounds, restoring vitality completely."
        }
    }
    
    # Major water spells (55-63 water)
    spells['blizzard.n.01'] = {
        "word": "woukresh",
        "spirit": "water",
        "composition": {"fire": 3, "water": 60, "earth": 15, "air": 45},
        "definition": "violent snowstorm",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 7,
            "effects": [
                {"type": "damage", "amount": 25, "to": "all", "element": "water"},
                {"type": "apply_status", "status": "frozen", "to": "all", "duration": 2},
                {"type": "apply_status", "status": "slowed", "to": "all", "duration": 4}
            ],
            "description": "A raging blizzard freezes everything in its path!"
        }
    }
    
    spells['tidal_wave.n.01'] = {
        "word": "lumgodresh",
        "spirit": "water",
        "composition": {"fire": 5, "water": 63, "earth": 30, "air": 20},
        "definition": "massive water wave",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 10,
            "effects": [
                {"type": "damage", "amount": 35, "to": "all", "element": "water"},
                {"type": "apply_status", "status": "swept", "to": "all"}
            ],
            "description": "A towering wave of water crashes down, sweeping away everything!"
        }
    }
    
    # ========================================================================
    # EARTH SPELLS - Defense, strength, endurance
    # ========================================================================
    
    # Minor earth spells (20-35 earth)
    spells['stone_skin.n.01'] = {
        "word": "brudna",
        "spirit": "earth",
        "composition": {"fire": 8, "water": 8, "earth": 28, "air": 5},
        "definition": "hardened protective layer",
        "spell_effect": {
            "type": "buff",
            "stat": "armor",
            "amount": "earth * 0.4",
            "duration": "earth / 5",
            "target": "Self",
            "description": "Your skin hardens like stone, resisting damage."
        }
    }
    
    spells['earthen_grasp.n.01'] = {
        "word": "brugra",
        "spirit": "earth",
        "composition": {"fire": 10, "water": 12, "earth": 35, "air": 8},
        "definition": "hands of earth emerge",
        "spell_effect": {
            "type": "apply_status",
            "target": "Enemy",
            "status": "grappled",
            "duration": "earth / 8",
            "description": "Hands of earth burst from the ground, gripping the target!"
        }
    }
    
    # Standard earth spells (40-50 earth)
    spells['boulder_throw.n.01'] = {
        "word": "godbru",
        "spirit": "earth",
        "composition": {"fire": 20, "water": 8, "earth": 45, "air": 12},
        "definition": "hurl massive rock",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": "earth * 0.8",
            "element": "earth",
            "description": "A massive boulder flies through the air and crashes into the target!"
        }
    }
    
    spells['stone_fortress.n.01'] = {
        "word": "brukresh",
        "spirit": "earth",
        "composition": {"fire": 15, "water": 10, "earth": 50, "air": 8},
        "definition": "impenetrable stone walls",
        "spell_effect": {
            "type": "create_object",
            "object_class": "Fortress",
            "properties": {
                "hp": "earth * 2",
                "blocks": "all"
            },
            "target": "Ground",
            "description": "Walls of solid stone rise up, forming an impenetrable fortress!"
        }
    }
    
    # Major earth spells (55-63 earth)
    spells['mountain_rise.n.01'] = {
        "word": "godkresh",
        "spirit": "earth",
        "composition": {"fire": 25, "water": 12, "earth": 63, "air": 15},
        "definition": "create mountain",
        "spell_effect": {
            "type": "create_object",
            "object_class": "Mountain",
            "properties": {
                "hp": "earth * 3",
                "impassable": True
            },
            "target": "Ground",
            "description": "The earth heaves and a mountain rises, reshaping the battlefield!"
        }
    }
    
    spells['crystal_prison.n.01'] = {
        "word": "brukratal",
        "spirit": "earth",
        "composition": {"fire": 15, "water": 20, "earth": 58, "air": 25},
        "definition": "crystalline cage",
        "spell_effect": {
            "type": "transform",
            "into": "Crystal Statue",
            "target": "Enemy",
            "description": "Crystals rapidly grow around the target, imprisoning them completely!"
        }
    }
    
    # ========================================================================
    # AIR SPELLS - Speed, movement, lightning
    # ========================================================================
    
    # Minor air spells (20-35 air)
    spells['gust.n.01'] = {
        "word": "seifa",
        "spirit": "air",
        "composition": {"fire": 5, "water": 8, "earth": 5, "air": 25},
        "definition": "sudden blast of wind",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": 10,
            "element": "air",
            "description": "A sudden gust of wind pushes the target backward."
        }
    }
    
    spells['feather_fall.n.01'] = {
        "word": "seiyun",
        "spirit": "air",
        "composition": {"fire": 5, "water": 10, "earth": 3, "air": 30},
        "definition": "slow descent",
        "spell_effect": {
            "type": "buff",
            "stat": "falling_speed",
            "amount": "-air * 0.9",
            "duration": "air / 5",
            "target": "Self",
            "description": "You drift down gently, as light as a feather."
        }
    }
    
    # Standard air spells (40-50 air)
    spells['chain_lightning.n.01'] = {
        "word": "seikrat",
        "spirit": "air",
        "composition": {"fire": 40, "water": 8, "earth": 10, "air": 48},
        "definition": "branching lightning",
        "spell_effect": {
            "type": "area_effect",
            "target": "Enemies",
            "radius": 5,
            "effects": [
                {"type": "damage", "amount": "air * 0.6", "to": "all", "element": "air"}
            ],
            "description": "Lightning arcs from target to target, chaining between enemies!"
        }
    }
    
    spells['fly.v.01'] = {
        "word": "seikresh",
        "spirit": "air",
        "composition": {"fire": 12, "water": 10, "earth": 5, "air": 50},
        "definition": "soar through the air",
        "spell_effect": {
            "type": "buff",
            "stat": "flight",
            "amount": "air",
            "duration": "air / 8",
            "target": "Self",
            "description": "You rise into the air, weightless and free!"
        }
    }
    
    # Major air spells (55-63 air)
    spells['tornado.n.01'] = {
        "word": "heikresh",
        "spirit": "air",
        "composition": {"fire": 20, "water": 15, "earth": 10, "air": 60},
        "definition": "violent rotating wind",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 8,
            "effects": [
                {"type": "damage", "amount": 30, "to": "all", "element": "air"},
                {"type": "apply_status", "status": "airborne", "to": "all", "duration": 3}
            ],
            "description": "A massive tornado tears across the battlefield, hurling everything skyward!"
        }
    }
    
    spells['tempest.n.01'] = {
        "word": "heikratgod",
        "spirit": "air",
        "composition": {"fire": 35, "water": 25, "earth": 15, "air": 63},
        "definition": "violent storm",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 12,
            "effects": [
                {"type": "damage", "amount": 25, "to": "all", "element": "air"},
                {"type": "damage", "amount": 15, "to": "all", "element": "water"},
                {"type": "apply_status", "status": "deafened", "to": "all", "duration": 4}
            ],
            "description": "Wind and rain rage with apocalyptic fury!"
        }
    }
    
    # ========================================================================
    # HYBRID SPELLS - Combining elements
    # ========================================================================
    
    # Fire + Air = Lightning
    spells['spark.n.01'] = {
        "word": "kratsei-min",
        "spirit": "fire",
        "composition": {"fire": 30, "water": 5, "earth": 8, "air": 28},
        "definition": "small electric discharge",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": 20,
            "element": "air",
            "description": "A crackling spark leaps to the target!"
        }
    }
    
    spells['thunderbolt.n.01'] = {
        "word": "kratseigod",
        "spirit": "fire",
        "composition": {"fire": 50, "water": 8, "earth": 15, "air": 45},
        "definition": "lightning with thunder",
        "spell_effect": {
            "type": "damage",
            "target": "Enemy",
            "amount": "(fire + air) / 1.8",
            "element": "air",
            "description": "A massive thunderbolt strikes with deafening force!"
        }
    }
    
    # Fire + Earth = Lava/Magma
    spells['magma_spray.n.01'] = {
        "word": "kratgod-lum",
        "spirit": "fire",
        "composition": {"fire": 45, "water": 5, "earth": 40, "air": 15},
        "definition": "molten rock spray",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 4,
            "effects": [
                {"type": "damage", "amount": 25, "to": "all", "element": "fire"},
                {"type": "apply_status", "status": "burning", "to": "all", "duration": 3}
            ],
            "description": "Molten lava sprays outward, burning everything it touches!"
        }
    }
    
    # Water + Air = Storm/Ice
    spells['ice_storm.n.01'] = {
        "word": "wousei",
        "spirit": "water",
        "composition": {"fire": 5, "water": 50, "earth": 15, "air": 48},
        "definition": "freezing wind and ice",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 6,
            "effects": [
                {"type": "damage", "amount": 20, "to": "all", "element": "water"},
                {"type": "damage", "amount": 15, "to": "all", "element": "air"},
                {"type": "apply_status", "status": "slowed", "to": "all", "duration": 3}
            ],
            "description": "Freezing wind and ice shards assault all in the area!"
        }
    }
    
    # Water + Earth = Mud/Quicksand
    spells['quicksand.n.01'] = {
        "word": "brulum",
        "spirit": "earth",
        "composition": {"fire": 5, "water": 35, "earth": 45, "air": 5},
        "definition": "loose wet sand",
        "spell_effect": {
            "type": "area_effect",
            "target": "Ground",
            "radius": 5,
            "effects": [
                {"type": "apply_status", "status": "trapped", "to": "all", "duration": 5}
            ],
            "description": "The ground becomes treacherous quicksand, trapping those who step on it!"
        }
    }
    
    # Earth + Air = Dust/Sand Storm
    spells['sandstorm.n.01'] = {
        "word": "brusei",
        "spirit": "earth",
        "composition": {"fire": 15, "water": 5, "earth": 40, "air": 50},
        "definition": "whirling sand",
        "spell_effect": {
            "type": "area_effect",
            "target": "All",
            "radius": 7,
            "effects": [
                {"type": "damage", "amount": 15, "to": "all", "element": "earth"},
                {"type": "apply_status", "status": "blinded", "to": "all", "duration": 3}
            ],
            "description": "A violent sandstorm whips through, blinding and abrading!"
        }
    }
    
    # ========================================================================
    # UTILITY SPELLS - Non-combat effects
    # ========================================================================
    
    spells['detect_magic.v.01'] = {
        "word": "seimna",
        "spirit": "air",
        "composition": {"fire": 10, "water": 15, "earth": 10, "air": 35},
        "definition": "sense magical energy",
        "spell_effect": {
            "type": "buff",
            "stat": "magic_sight",
            "amount": "air",
            "duration": "air / 5",
            "target": "Self",
            "description": "Your vision shifts, revealing flows of magical energy."
        }
    }
    
    spells['light.n.01'] = {
        "word": "skatmin",
        "spirit": "fire",
        "composition": {"fire": 20, "water": 5, "earth": 5, "air": 15},
        "definition": "illumination",
        "spell_effect": {
            "type": "create_object",
            "object_class": "Light Source",
            "properties": {
                "brightness": "fire",
                "duration": "fire * 2"
            },
            "target": "Self",
            "description": "A soft light emanates, illuminating the darkness."
        }
    }
    
    spells['invisibility.n.01'] = {
        "word": "seiyresh",
        "spirit": "air",
        "composition": {"fire": 8, "water": 20, "earth": 5, "air": 55},
        "definition": "unable to be seen",
        "spell_effect": {
            "type": "buff",
            "stat": "visibility",
            "amount": "-air",
            "duration": "air / 10",
            "target": "Self",
            "description": "You fade from sight, becoming invisible to the naked eye."
        }
    }
    
    spells['levitate.v.01'] = {
        "word": "seikal",
        "spirit": "air",
        "composition": {"fire": 8, "water": 12, "earth": 15, "air": 40},
        "definition": "hover in the air",
        "spell_effect": {
            "type": "buff",
            "stat": "levitation",
            "amount": "air * 0.5",
            "duration": "air / 6",
            "target": "Target",
            "description": "The target lifts gently off the ground, hovering in place."
        }
    }
    
    spells['shape_stone.v.01'] = {
        "word": "brumold",
        "spirit": "earth",
        "composition": {"fire": 15, "water": 12, "earth": 42, "air": 8},
        "definition": "mold rock like clay",
        "spell_effect": {
            "type": "modify_state",
            "target": "Stone",
            "modification": {"malleable": True},
            "description": "Stone becomes soft and pliable, reshaping to your will."
        }
    }
    
    spells['water_breathing.n.01'] = {
        "word": "lumsei-brea",
        "spirit": "water",
        "composition": {"fire": 5, "water": 40, "earth": 10, "air": 35},
        "definition": "breathe underwater",
        "spell_effect": {
            "type": "buff",
            "stat": "underwater_breathing",
            "amount": 1,
            "duration": "water / 4",
            "target": "Self",
            "description": "Gills form on your neck, allowing you to breathe water as easily as air."
        }
    }
    
    # ========================================================================
    # SUMMONING SPELLS
    # ========================================================================
    
    spells['summon_fire_elemental.v.01'] = {
        "word": "kratesh",
        "spirit": "fire",
        "composition": {"fire": 50, "water": 15, "earth": 20, "air": 25},
        "definition": "call fire spirit",
        "spell_effect": {
            "type": "summon",
            "creature": "Fire Elemental",
            "hp": "fire * 0.6",
            "duration": "fire / 10",
            "description": "Flames coalesce into a living form - a Fire Elemental rises to serve you!"
        }
    }
    
    spells['summon_water_elemental.v.01'] = {
        "word": "lumesh",
        "spirit": "water",
        "composition": {"fire": 15, "water": 50, "earth": 20, "air": 25},
        "definition": "call water spirit",
        "spell_effect": {
            "type": "summon",
            "creature": "Water Elemental",
            "hp": "water * 0.6",
            "duration": "water / 10",
            "description": "Water swirls and takes form - a Water Elemental emerges to aid you!"
        }
    }
    
    spells['summon_earth_elemental.v.01'] = {
        "word": "bruesh",
        "spirit": "earth",
        "composition": {"fire": 20, "water": 15, "earth": 50, "air": 20},
        "definition": "call earth spirit",
        "spell_effect": {
            "type": "summon",
            "creature": "Earth Elemental",
            "hp": "earth * 0.8",
            "duration": "earth / 10",
            "description": "Stone and soil gather together - an Earth Elemental stands ready!"
        }
    }
    
    spells['summon_air_elemental.v.01'] = {
        "word": "seiesh",
        "spirit": "air",
        "composition": {"fire": 20, "water": 15, "earth": 20, "air": 50},
        "definition": "call air spirit",
        "spell_effect": {
            "type": "summon",
            "creature": "Air Elemental",
            "hp": "air * 0.5",
            "duration": "air / 10",
            "description": "Wind spirals into a vaguely humanoid form - an Air Elemental appears!"
        }
    }
    
    spells['summon_swarm.v.01'] = {
        "word": "seibrum",
        "spirit": "air",
        "composition": {"fire": 10, "water": 15, "earth": 25, "air": 40},
        "definition": "call many small creatures",
        "spell_effect": {
            "type": "summon",
            "creature": "Insect Swarm",
            "hp": 20,
            "duration": "air / 8",
            "description": "A buzzing swarm of insects materializes, swarming your enemies!"
        }
    }
    
    # ========================================================================
    # TRANSFORMATION SPELLS
    # ========================================================================
    
    spells['polymorph.v.01'] = {
        "word": "brukralmold",
        "spirit": "earth",
        "composition": {"fire": 20, "water": 30, "earth": 45, "air": 35},
        "definition": "change form completely",
        "spell_effect": {
            "type": "transform",
            "into": "Random Creature",
            "target": "Enemy",
            "description": "The target's body ripples and transforms into a different creature entirely!"
        }
    }
    
    spells['enlarge.v.01'] = {
        "word": "godresh",
        "spirit": "earth",
        "composition": {"fire": 15, "water": 15, "earth": 48, "air": 20},
        "definition": "grow larger",
        "spell_effect": {
            "type": "buff",
            "stat": "size",
            "amount": "earth * 0.4",
            "duration": "earth / 8",
            "target": "Target",
            "description": "The target grows to massive proportions!"
        }
    }
    
    spells['shrink.v.01'] = {
        "word": "seimin",
        "spirit": "air",
        "composition": {"fire": 10, "water": 15, "earth": 20, "air": 45},
        "definition": "become tiny",
        "spell_effect": {
            "type": "buff",
            "stat": "size",
            "amount": "-air * 0.4",
            "duration": "air / 8",
            "target": "Target",
            "description": "The target shrinks down to a fraction of their size!"
        }
    }
    
    return spells

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Generate and save expanded spell database"""
    
    # Load existing spells
    existing_file = Path('elemental_build_data_modifiers.json')
    if existing_file.exists():
        with open(existing_file, 'r') as f:
            existing_spells = json.load(f)
    else:
        existing_spells = {}
    
    # Generate new spells
    new_spells = generate_spells()
    
    # Merge (new spells don't overwrite existing)
    all_spells = {**new_spells, **existing_spells}
    
    # Save to new file
    output_file = 'elemental_spells_expanded.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_spells, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Spell Database Generated!")
    print(f"   Total spells: {len(all_spells)}")
    print(f"   New spells: {len(new_spells)}")
    print(f"   Existing spells: {len(existing_spells)}")
    print(f"   Saved to: {output_file}")
    
    # Stats
    by_element = {'fire': 0, 'water': 0, 'earth': 0, 'air': 0}
    by_type = {}
    
    for spell in all_spells.values():
        by_element[spell['spirit']] += 1
        effect_type = spell['spell_effect'].get('type', 'unknown')
        by_type[effect_type] = by_type.get(effect_type, 0) + 1
    
    print(f"\n📊 By Element:")
    for elem, count in sorted(by_element.items(), key=lambda x: -x[1]):
        print(f"   {elem:10s}: {count:3d}")
    
    print(f"\n📊 By Type:")
    for typ, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {typ:20s}: {count:3d}")
    
    # Show samples
    print(f"\n🔥 Sample Fire Spells:")
    fire_spells = [s for s in all_spells.values() if s['spirit'] == 'fire'][:5]
    for s in fire_spells:
        print(f"   • {s['word']:20s} - {s['definition']}")
    
    print(f"\n💧 Sample Water Spells:")
    water_spells = [s for s in all_spells.values() if s['spirit'] == 'water'][:5]
    for s in water_spells:
        print(f"   • {s['word']:20s} - {s['definition']}")
    
    print(f"\n🌍 Sample Earth Spells:")
    earth_spells = [s for s in all_spells.values() if s['spirit'] == 'earth'][:5]
    for s in earth_spells:
        print(f"   • {s['word']:20s} - {s['definition']}")
    
    print(f"\n💨 Sample Air Spells:")
    air_spells = [s for s in all_spells.values() if s['spirit'] == 'air'][:5]
    for s in air_spells:
        print(f"   • {s['word']:20s} - {s['definition']}")

if __name__ == '__main__':
    main()
