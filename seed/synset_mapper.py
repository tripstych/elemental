"""
WordNet Synset Mappings for Generators
Maps all generator tiles and terrain features to WordNet synsets (e.g., 'wall.n.01')
for integration with the glockblocks magic system
"""

import json
from typing import Dict, Optional, List


class SynsetMapper:
    """
    Maps game elements to WordNet synsets
    All objects get proper synset IDs for use in magic system
    """
    
    # Dungeon elements
    DUNGEON_SYNSETS = {
        'floor': 'floor.n.01',
        'wall': 'wall.n.01',
        'door': 'door.n.01',
        'corridor': 'corridor.n.01',
        'stair': 'stairway.n.01',
        'entrance': 'entrance.n.01',
        'exit': 'exit.n.01',
        'room': 'room.n.01',
        'torch': 'torch.n.01',
        'pillar': 'pillar.n.01',
        'chest': 'chest.n.02',
        'altar': 'altar.n.01'
    }
    
    # City elements
    CITY_SYNSETS = {
        'road': 'road.n.01',
        'building': 'building.n.01',
        'wall': 'wall.n.01',
        'door': 'door.n.01',
        'gate': 'gate.n.01',
        'plaza': 'plaza.n.01',
        'park': 'park.n.01',
        'market': 'marketplace.n.01',
        'fountain': 'fountain.n.01',
        'house': 'house.n.01',
        'shop': 'shop.n.01',
        'tavern': 'tavern.n.01',
        'street': 'street.n.01'
    }
    
    # Terrain features (from landscape_features.json)
    TERRAIN_SYNSETS = {
        'cactus': 'cactus.n.01',
        'rock': 'rock.n.01',
        'sand_dune': 'dune.n.01',
        'pine': 'pine.n.01',
        'oak': 'oak.n.01',
        'tree': 'tree.n.01',
        'mushroom': 'mushroom.n.02',
        'boulder': 'boulder.n.01',
        'flower': 'flower.n.01',
        'grass_tuft': 'grass.n.01',
        'grass': 'grass.n.01',
        'peak': 'peak.n.01',
        'cliff': 'cliff.n.01',
        'wave': 'wave.n.01',
        'fish': 'fish.n.01',
        'water': 'water.n.01',
        'willow': 'willow.n.01',
        'log': 'log.n.01',
        'lava': 'lava.n.01'
    }
    
    @classmethod
    def get_synset(cls, name: str) -> str:
        """Get synset for an element name, searching all categories"""
        # Search all mappings
        for mapping in [cls.DUNGEON_SYNSETS, cls.CITY_SYNSETS, cls.TERRAIN_SYNSETS]:
            if name in mapping:
                return mapping[name]
        
        # Default: use name with .n.01 suffix
        return f"{name}.n.01"
    
    @classmethod
    def add_synsets_to_landscape_features(cls, features_file: str, output_file: str = None):
        """
        Load landscape_features.json and add synsets to each feature
        
        Args:
            features_file: Path to input landscape_features.json
            output_file: Path to save updated version (None = overwrite input)
        """
        with open(features_file, 'r') as f:
            features = json.load(f)
        
        # Add synsets to each feature
        for terrain_name, terrain_def in features.items():
            for feature in terrain_def.get('features', []):
                feature_name = feature['name']
                feature['synset'] = cls.get_synset(feature_name)
        
        # Save
        output_path = output_file if output_file else features_file
        with open(output_path, 'w') as f:
            json.dump(features, f, indent=2)
        
        print(f"Added synsets to landscape features → {output_path}")
        return features


# ============================================================================
# GENERATOR OBJECT CREATION
# ============================================================================

def create_dungeon_object(tile_value: int) -> Dict:
    """Create game object for dungeon tile with synset"""
    from dungeon_generator import DungeonGenerator
    
    tiles = {
        DungeonGenerator.FLOOR: {
            'name': 'floor',
            'synset': 'floor.n.01',
            'char': '.',
            'color': 'gray',
            'type': 'dungeon_floor'
        },
        DungeonGenerator.WALL: {
            'name': 'wall',
            'synset': 'wall.n.01',
            'char': '#',
            'color': 'white',
            'type': 'dungeon_wall'
        },
        DungeonGenerator.DOOR: {
            'name': 'door',
            'synset': 'door.n.01',
            'char': '+',
            'color': 'brown',
            'type': 'dungeon_door'
        },
        DungeonGenerator.CORRIDOR: {
            'name': 'corridor',
            'synset': 'corridor.n.01',
            'char': ',',
            'color': 'gray',
            'type': 'dungeon_corridor'
        },
        DungeonGenerator.ROOM_FLOOR: {
            'name': 'floor',
            'synset': 'floor.n.01',
            'char': '·',
            'color': 'yellow',
            'type': 'dungeon_room'
        },
        DungeonGenerator.ENTRANCE: {
            'name': 'entrance',
            'synset': 'entrance.n.01',
            'char': '<',
            'color': 'bright_green',
            'type': 'dungeon_entrance'
        },
        DungeonGenerator.EXIT: {
            'name': 'exit',
            'synset': 'exit.n.01',
            'char': '>',
            'color': 'bright_red',
            'type': 'dungeon_exit'
        }
    }
    
    return tiles.get(tile_value, {
        'name': 'unknown',
        'synset': 'object.n.01',
        'char': '?',
        'color': 'white',
        'type': 'unknown'
    })


def create_city_object(tile_value: int) -> Dict:
    """Create game object for city tile with synset"""
    from city_generator import CityGenerator
    
    tiles = {
        CityGenerator.EMPTY: {
            'name': 'grass',
            'synset': 'grass.n.01',
            'char': '.',
            'color': 'green',
            'type': 'city_ground'
        },
        CityGenerator.ROAD: {
            'name': 'road',
            'synset': 'road.n.01',
            'char': '=',
            'color': 'gray',
            'type': 'city_road'
        },
        CityGenerator.BUILDING: {
            'name': 'building',
            'synset': 'building.n.01',
            'char': '▓',
            'color': 'yellow',
            'type': 'city_building'
        },
        CityGenerator.WALL: {
            'name': 'wall',
            'synset': 'wall.n.01',
            'char': '#',
            'color': 'brown',
            'type': 'city_wall'
        },
        CityGenerator.DOOR: {
            'name': 'door',
            'synset': 'door.n.01',
            'char': '+',
            'color': 'brown',
            'type': 'city_door'
        },
        CityGenerator.PLAZA: {
            'name': 'plaza',
            'synset': 'plaza.n.01',
            'char': '□',
            'color': 'white',
            'type': 'city_plaza'
        },
        CityGenerator.PARK: {
            'name': 'park',
            'synset': 'park.n.01',
            'char': '♣',
            'color': 'green',
            'type': 'city_park'
        },
        CityGenerator.MARKET: {
            'name': 'market',
            'synset': 'marketplace.n.01',
            'char': 'M',
            'color': 'yellow',
            'type': 'city_market'
        },
        CityGenerator.GATE: {
            'name': 'gate',
            'synset': 'gate.n.01',
            'char': 'Π',
            'color': 'bright_white',
            'type': 'city_gate'
        }
    }
    
    return tiles.get(tile_value, {
        'name': 'unknown',
        'synset': 'object.n.01',
        'char': '?',
        'color': 'white',
        'type': 'unknown'
    })


def get_tile_synset(generator, x: int, y: int) -> Optional[str]:
    """Get synset for tile at position"""
    from dungeon_generator import DungeonGenerator
    from city_generator import CityGenerator
    
    if not generator.is_valid_position(x, y):
        return None
    
    tile_value = generator.grid[y, x]
    
    if isinstance(generator, DungeonGenerator):
        obj = create_dungeon_object(tile_value)
    elif isinstance(generator, CityGenerator):
        obj = create_city_object(tile_value)
    else:
        return None
    
    return obj.get('synset')


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("WORDNET SYNSET MAPPER")
    print("=" * 70)
    
    # Test synset lookups
    print("\nSynset lookups:")
    for name in ['wall', 'door', 'tree', 'flower', 'road']:
        synset = SynsetMapper.get_synset(name)
        print(f"  {name:15s} → {synset}")
    
    # Update landscape features
    print("\nAdding synsets to landscape_features.json...")
    try:
        features = SynsetMapper.add_synsets_to_landscape_features(
            'landscape_features.json',
            'landscape_features_with_synsets.json'
        )
        
        # Show example
        desert = features.get('desert', {})
        print("\nDesert features:")
        for feat in desert.get('features', []):
            print(f"  {feat['name']:15s} → {feat.get('synset', 'N/A')}")
    except FileNotFoundError:
        print("  landscape_features.json not found")
    
    # Test generator objects
    print("\nDungeon tile objects:")
    from dungeon_generator import DungeonGenerator
    
    for tile in [DungeonGenerator.FLOOR, DungeonGenerator.WALL, DungeonGenerator.DOOR]:
        obj = create_dungeon_object(tile)
        print(f"  {obj['name']:15s} → {obj['synset']}")
    
    print("\n" + "=" * 70)
    print("All objects now have WordNet synsets for magic system!")
    print("=" * 70)
