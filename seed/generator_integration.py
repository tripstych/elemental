"""
Generator Integration with RenderFeatures
Connects dungeon/city generators to the landscape feature rendering system
"""

import json
import numpy as np
from typing import Dict, List, Optional
from base_generator import BaseGenerator
from dungeon_generator import DungeonGenerator
from city_generator import CityGenerator
from nltk.corpus import wordnet as wn

class GeneratorFeatureMapper:
    """
    Maps generator tiles to landscape features for RenderFeatures compatibility
    Creates feature definitions that work with your existing rendering system
    """
    
    # Dungeon tile → feature mapping
    DUNGEON_FEATURES = {
        'floor': {
            "features": [
                {
                    "char": ".",
                    "name": "floor",
                    "density": 1.0,
                    "color": "gray",
                    "cluster": False
                }
            ],
            "ground_char": ".",
            "ground_color": "gray"
        },
        'wall': {
            "features": [
                {
                    "char": "#",
                    "name": "wall",
                    "density": 1.0,
                    "color": "white",
                    "cluster": False
                }
            ],
            "ground_char": "#",
            "ground_color": "white"
        },
        'corridor': {
            "features": [
                {
                    "char": ",",
                    "name": "corridor",
                    "density": 1.0,
                    "color": "gray",
                    "cluster": False
                }
            ],
            "ground_char": ",",
            "ground_color": "gray"
        },
        'door': {
            "features": [
                {
                    "char": "+",
                    "name": "door",
                    "density": 1.0,
                    "color": "brown",
                    "cluster": False
                }
            ],
            "ground_char": "+",
            "ground_color": "brown"
        },
        'entrance': {
            "features": [
                {
                    "char": "<",
                    "name": "entrance",
                    "density": 1.0,
                    "color": "bright_green",
                    "cluster": False
                }
            ],
            "ground_char": "<",
            "ground_color": "bright_green"
        },
        'exit': {
            "features": [
                {
                    "char": ">",
                    "name": "exit",
                    "density": 1.0,
                    "color": "bright_red",
                    "cluster": False
                }
            ],
            "ground_char": ">",
            "ground_color": "bright_red"
        }
    }
    
    # City tile → feature mapping
    CITY_FEATURES = {
        'empty': {
            "features": [
                {
                    "char": ".",
                    "name": "grass",
                    "density": 1.0,
                    "color": "green",
                    "cluster": False
                }
            ],
            "ground_char": ".",
            "ground_color": "green"
        },
        'road': {
            "features": [
                {
                    "char": "=",
                    "name": "road",
                    "density": 1.0,
                    "color": "gray",
                    "cluster": False
                }
            ],
            "ground_char": "=",
            "ground_color": "gray"
        },
        'building': {
            "features": [
                {
                    "char": "▓",
                    "name": "building_interior",
                    "density": 1.0,
                    "color": "yellow",
                    "cluster": False
                }
            ],
            "ground_char": "▓",
            "ground_color": "yellow"
        },
        'wall': {
            "features": [
                {
                    "char": "#",
                    "name": "building_wall",
                    "density": 1.0,
                    "color": "brown",
                    "cluster": False
                }
            ],
            "ground_char": "#",
            "ground_color": "brown"
        },
        'door': {
            "features": [
                {
                    "char": "+",
                    "name": "door",
                    "density": 1.0,
                    "color": "brown",
                    "cluster": False
                }
            ],
            "ground_char": "+",
            "ground_color": "brown"
        },
        'plaza': {
            "features": [
                {
                    "char": "□",
                    "name": "plaza",
                    "density": 1.0,
                    "color": "white",
                    "cluster": False
                }
            ],
            "ground_char": "□",
            "ground_color": "white"
        },
        'park': {
            "features": [
                {
                    "char": "♣",
                    "name": "tree",
                    "density": 0.3,
                    "color": "green",
                    "cluster": True,
                    "cluster_size": 5
                },
                {
                    "char": "*",
                    "name": "flower",
                    "density": 0.1,
                    "color": "yellow",
                    "cluster": True,
                    "cluster_size": 3
                }
            ],
            "ground_char": ".",
            "ground_color": "green"
        },
        'market': {
            "features": [
                {
                    "char": "M",
                    "name": "market_stall",
                    "density": 0.4,
                    "color": "yellow",
                    "cluster": True,
                    "cluster_size": 4
                },
                {
                    "char": "C",
                    "name": "crate",
                    "density": 0.2,
                    "color": "brown",
                    "cluster": True,
                    "cluster_size": 3
                }
            ],
            "ground_char": ".",
            "ground_color": "yellow"
        },
        'gate': {
            "features": [
                {
                    "char": "Π",
                    "name": "city_gate",
                    "density": 1.0,
                    "color": "bright_white",
                    "cluster": False
                }
            ],
            "ground_char": "Π",
            "ground_color": "bright_white"
        }
    }
    
    @classmethod
    def create_dungeon_features(cls, dungeon: DungeonGenerator) -> Dict:
        """
        Create feature definitions for a dungeon
        Returns a dict compatible with RenderFeatures
        """
        # Map tile values to feature types
        tile_map = {
            DungeonGenerator.FLOOR: 'floor',
            DungeonGenerator.WALL: 'wall',
            DungeonGenerator.CORRIDOR: 'corridor',
            DungeonGenerator.DOOR: 'door',
            DungeonGenerator.ROOM_FLOOR: 'floor',
            DungeonGenerator.ENTRANCE: 'entrance',
            DungeonGenerator.EXIT: 'exit'
        }
        
        # Create unique feature set for this dungeon
        features = {}
        for tile_value, feature_name in tile_map.items():
            if feature_name in cls.DUNGEON_FEATURES:
                syns = wn.synsets(feature_name)
                print(syns,"--")
                features[f"dungeon_{feature_name}"] = cls.DUNGEON_FEATURES[feature_name]
        exit()
        return features
    
    @classmethod
    def create_city_features(cls, city: CityGenerator) -> Dict:
        """
        Create feature definitions for a city
        Returns a dict compatible with RenderFeatures
        """
        tile_map = {
            CityGenerator.EMPTY: 'empty',
            CityGenerator.ROAD: 'road',
            CityGenerator.BUILDING: 'building',
            CityGenerator.WALL: 'wall',
            CityGenerator.DOOR: 'door',
            CityGenerator.PLAZA: 'plaza',
            CityGenerator.PARK: 'park',
            CityGenerator.MARKET: 'market',
            CityGenerator.GATE: 'gate'
        }
        
        features = {}
        for tile_value, feature_name in tile_map.items():
            if feature_name in cls.CITY_FEATURES:
                features[f"city_{feature_name}"] = cls.CITY_FEATURES[feature_name]
        
        return features


class GeneratorRenderer:
    """
    Renders generators using RenderFeatures-compatible system
    Provides zoom views and detailed rendering of generator content
    """
    
    # ANSI color codes (matching RenderFeatures)
    COLORS = {
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'gray': '\033[90m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
        'dark_green': '\033[32m',
        'dark_cyan': '\033[36m',
        'brown': '\033[33m',
        'reset': '\033[0m'
    }
    
    @classmethod
    def render_with_features(cls, generator: BaseGenerator, 
                            tile_x: int, tile_y: int,
                            zoom_size: int = 50) -> str:
        """
        Render a zoomed portion of the generator with features
        Similar to RenderFeatures zoom view
        
        Args:
            generator: DungeonGenerator or CityGenerator
            tile_x, tile_y: Center point to zoom on
            zoom_size: Size of zoom view
            
        Returns:
            Colored ASCII string
        """
        # Get tile mapping
        if isinstance(generator, DungeonGenerator):
            tile_chars, tile_colors = cls._get_dungeon_tile_mapping()
        elif isinstance(generator, CityGenerator):
            tile_chars, tile_colors = cls._get_city_tile_mapping()
        else:
            # Generic
            tile_chars = {0: '.', 1: '#'}
            tile_colors = {0: 'green', 1: 'white'}
        
        # Calculate bounds
        start_x = max(0, tile_x - zoom_size // 2)
        start_y = max(0, tile_y - zoom_size // 2)
        end_x = min(generator.width, start_x + zoom_size)
        end_y = min(generator.height, start_y + zoom_size)
        
        # Render
        lines = []
        for y in range(start_y, end_y):
            line = ""
            for x in range(start_x, end_x):
                tile_value = generator.grid[y, x]
                
                # Check for objects at this position
                objects = generator.get_objects_at(x, y)
                if objects:
                    # Render first object
                    obj = objects[0]
                    char = obj.get('char', '?')
                    color = obj.get('color', 'white')
                else:
                    # Render tile
                    char = tile_chars.get(tile_value, '?')
                    color = tile_colors.get(tile_value, 'white')
                
                line += cls._colorize(char, color)
            
            lines.append(line)
        
        return '\n'.join(lines)
    
    @classmethod
    def _get_dungeon_tile_mapping(cls):
        """Get tile char and color mappings for dungeons"""
        chars = {
            DungeonGenerator.FLOOR: '.',
            DungeonGenerator.WALL: '#',
            DungeonGenerator.DOOR: '+',
            DungeonGenerator.CORRIDOR: ',',
            DungeonGenerator.ROOM_FLOOR: '·',
            DungeonGenerator.ENTRANCE: '<',
            DungeonGenerator.EXIT: '>'
        }
        
        colors = {
            DungeonGenerator.FLOOR: 'gray',
            DungeonGenerator.WALL: 'white',
            DungeonGenerator.DOOR: 'brown',
            DungeonGenerator.CORRIDOR: 'gray',
            DungeonGenerator.ROOM_FLOOR: 'yellow',
            DungeonGenerator.ENTRANCE: 'bright_green',
            DungeonGenerator.EXIT: 'bright_red'
        }
        
        return chars, colors
    
    @classmethod
    def _get_city_tile_mapping(cls):
        """Get tile char and color mappings for cities"""
        chars = {
            CityGenerator.EMPTY: '.',
            CityGenerator.ROAD: '=',
            CityGenerator.BUILDING: '▓',
            CityGenerator.WALL: '#',
            CityGenerator.DOOR: '+',
            CityGenerator.PLAZA: '□',
            CityGenerator.PARK: '♣',
            CityGenerator.WATER: '~',
            CityGenerator.MARKET: 'M',
            CityGenerator.GATE: 'Π'
        }
        
        colors = {
            CityGenerator.EMPTY: 'green',
            CityGenerator.ROAD: 'gray',
            CityGenerator.BUILDING: 'yellow',
            CityGenerator.WALL: 'brown',
            CityGenerator.DOOR: 'brown',
            CityGenerator.PLAZA: 'white',
            CityGenerator.PARK: 'green',
            CityGenerator.WATER: 'cyan',
            CityGenerator.MARKET: 'yellow',
            CityGenerator.GATE: 'bright_white'
        }
        
        return chars, colors
    
    @classmethod
    def _colorize(cls, char: str, color: str) -> str:
        """Add ANSI color code to character"""
        color_code = cls.COLORS.get(color, cls.COLORS['white'])
        return f"{color_code}{char}{cls.COLORS['reset']}"
    
    @classmethod
    def print_with_features(cls, generator: BaseGenerator,
                           tile_x: int, tile_y: int,
                           zoom_size: int = 50):
        """Print a zoomed view with colors"""
        output = cls.render_with_features(generator, tile_x, tile_y, zoom_size)
        print(output)


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================

def test_integration():
    """Test integration with RenderFeatures-style rendering"""
    import json
    from base_generator import populate_objects_by_type
    
    print("=" * 70)
    print("GENERATOR + RENDERFEATURES INTEGRATION TEST")
    print("=" * 70)
    
    # Load game objects
    try:
        with open('game_objects_wordnet.json', 'r') as f:
            game_objects = json.load(f)
        print(f"\n✅ Loaded {len(game_objects)} game objects")
    except FileNotFoundError:
        print("\n⚠️  game_objects_wordnet.json not found - skipping object population")
        game_objects = []
    
    # ========================================================================
    # DUNGEON EXAMPLE
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("DUNGEON WITH OBJECTS")
    print("=" * 70)
    
    dungeon = DungeonGenerator(60, 30, algorithm='bsp', seed=42)
    dungeon.generate()
    
    # Populate dungeon with objects
    if game_objects:
        # Add weapons to rooms
        weapons_placed = populate_objects_by_type(
            dungeon, game_objects,
            tile_type=DungeonGenerator.ROOM_FLOOR,
            object_type='weapons',
            density=0.05
        )
        print(f"Placed {weapons_placed} weapons in rooms")
        
        # Add containers to rooms
        containers_placed = populate_objects_by_type(
            dungeon, game_objects,
            tile_type=DungeonGenerator.ROOM_FLOOR,
            object_type='containers',
            density=0.08
        )
        print(f"Placed {containers_placed} containers in rooms")
    
    # Render full dungeon
    print("\nFull dungeon:")
    dungeon.print_ascii()
    
    # Render zoomed view with objects
    if game_objects and weapons_placed > 0:
        print("\n" + "-" * 70)
        print("Zoomed view (center) - showing objects:")
        print("-" * 70)
        GeneratorRenderer.print_with_features(dungeon, 30, 15, zoom_size=40)
    
    # ========================================================================
    # CITY EXAMPLE
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("CITY WITH OBJECTS")
    print("=" * 70)
    
    city = CityGenerator(80, 40, city_type='medieval', seed=42)
    city.generate()
    
    # Populate city
    if game_objects:
        # Add furniture to buildings
        furniture_placed = populate_objects_by_type(
            city, game_objects,
            tile_type=CityGenerator.BUILDING,
            object_type='furniture',
            density=0.15
        )
        print(f"Placed {furniture_placed} furniture in buildings")
        
        # Add objects to market
        market_placed = populate_objects_by_type(
            city, game_objects,
            tile_type=CityGenerator.MARKET,
            object_type='containers',
            density=0.3
        )
        print(f"Placed {market_placed} market goods")
    
    # Render city
    print("\nCity overview:")
    city.print_ascii()
    
    print("\n" + "=" * 70)
    print("INTEGRATION COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    test_integration()
