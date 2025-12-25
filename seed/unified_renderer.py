"""
Unified Rendering System
render(generator) - works for terrain, dungeons, cities, everything
Easy to swap ASCII → graphics later
"""

import numpy as np
from typing import Optional, Dict, Tuple
from base_generator import BaseGenerator


class Renderer:
    """
    Universal renderer for all generators
    ASCII now, easy to swap to graphics later
    """
    
    # ANSI color codes
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
    def render(cls, generator: BaseGenerator, 
               show_objects: bool = True,
               colorize: bool = True) -> str:
        """
        Main render function - works for any generator
        
        Args:
            generator: Any BaseGenerator subclass
            show_objects: Show placed objects instead of tiles
            colorize: Use ANSI colors
            
        Returns:
            Rendered string
        """
        from dungeon_generator import DungeonGenerator
        from city_generator import CityGenerator
        from synset_mapper import create_dungeon_object, create_city_object
        
        # Get tile mapping for this generator type
        if isinstance(generator, DungeonGenerator):
            tile_chars, tile_colors = cls._get_dungeon_mapping()
            object_creator = create_dungeon_object
        elif isinstance(generator, CityGenerator):
            tile_chars, tile_colors = cls._get_city_mapping()
            object_creator = create_city_object
        else:
            # Generic fallback
            tile_chars = {0: '.', 1: '#'}
            tile_colors = {0: 'green', 1: 'white'}
            object_creator = None
        
        # Render each row
        lines = []
        for y in range(generator.height):
            line = ""
            for x in range(generator.width):
                # Check for objects first
                objects = generator.get_objects_at(x, y) if show_objects else []
                
                if objects:
                    # Show first object
                    obj = objects[0]
                    char = obj.get('char', '?')
                    color = obj.get('color', 'white')
                else:
                    # Show tile
                    tile_value = generator.grid[y, x]
                    
                    if object_creator:
                        tile_obj = object_creator(tile_value)
                        char = tile_obj.get('char', '?')
                        color = tile_obj.get('color', 'white')
                    else:
                        char = tile_chars.get(tile_value, '?')
                        color = tile_colors.get(tile_value, 'white')
                
                # Add to line
                if colorize:
                    line += cls._colorize(char, color)
                else:
                    line += char
            
            lines.append(line)
        
        if colorize:
            lines.append(cls.COLORS['reset'])
        
        return '\n'.join(lines)
    
    @classmethod
    def render_zoom(cls, generator: BaseGenerator,
                   center_x: int, center_y: int,
                   zoom_size: int = 40,
                   show_objects: bool = True,
                   colorize: bool = True) -> str:
        """
        Render a zoomed portion of the generator
        
        Args:
            generator: Any BaseGenerator subclass
            center_x, center_y: Center point
            zoom_size: Size of zoom window
            show_objects: Show objects
            colorize: Use colors
            
        Returns:
            Rendered string
        """
        from dungeon_generator import DungeonGenerator
        from city_generator import CityGenerator
        from synset_mapper import create_dungeon_object, create_city_object
        
        # Get tile mapping
        if isinstance(generator, DungeonGenerator):
            tile_chars, tile_colors = cls._get_dungeon_mapping()
            object_creator = create_dungeon_object
        elif isinstance(generator, CityGenerator):
            tile_chars, tile_colors = cls._get_city_mapping()
            object_creator = create_city_object
        else:
            tile_chars = {0: '.', 1: '#'}
            tile_colors = {0: 'green', 1: 'white'}
            object_creator = None
        
        # Calculate bounds
        half_zoom = zoom_size // 2
        start_x = max(0, center_x - half_zoom)
        start_y = max(0, center_y - half_zoom)
        end_x = min(generator.width, start_x + zoom_size)
        end_y = min(generator.height, start_y + zoom_size)
        
        # Render
        lines = []
        for y in range(start_y, end_y):
            line = ""
            for x in range(start_x, end_x):
                objects = generator.get_objects_at(x, y) if show_objects else []
                
                if objects:
                    obj = objects[0]
                    char = obj.get('char', '?')
                    color = obj.get('color', 'white')
                else:
                    tile_value = generator.grid[y, x]
                    
                    if object_creator:
                        tile_obj = object_creator(tile_value)
                        char = tile_obj.get('char', '?')
                        color = tile_obj.get('color', 'white')
                    else:
                        char = tile_chars.get(tile_value, '?')
                        color = tile_colors.get(tile_value, 'white')
                
                if colorize:
                    line += cls._colorize(char, color)
                else:
                    line += char
            
            lines.append(line)
        
        if colorize:
            lines.append(cls.COLORS['reset'])
        
        return '\n'.join(lines)
    
    @classmethod
    def _get_dungeon_mapping(cls) -> Tuple[Dict, Dict]:
        """Get char and color mappings for dungeons"""
        from dungeon_generator import DungeonGenerator
        
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
    def _get_city_mapping(cls) -> Tuple[Dict, Dict]:
        """Get char and color mappings for cities"""
        from city_generator import CityGenerator
        
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
        """Add ANSI color to character"""
        color_code = cls.COLORS.get(color, cls.COLORS['white'])
        return f"{color_code}{char}{cls.COLORS['reset']}"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def render(generator: BaseGenerator, show_objects: bool = True, 
           colorize: bool = True) -> str:
    """
    Main render function - works for any generator
    
    Usage:
        print(render(dungeon))
        print(render(city))
        print(render(garden_city, show_objects=False))
    """
    return Renderer.render(generator, show_objects, colorize)


def render_zoom(generator: BaseGenerator, x: int, y: int,
               size: int = 40, show_objects: bool = True,
               colorize: bool = True) -> str:
    """
    Render a zoomed view
    
    Usage:
        print(render_zoom(dungeon, 30, 15))
        print(render_zoom(city, 50, 25, size=60))
    """
    return Renderer.render_zoom(generator, x, y, size, show_objects, colorize)


# ============================================================================
# FUTURE GRAPHICS ADAPTER
# ============================================================================

class GraphicsAdapter:
    """
    Placeholder for future graphics rendering
    When you're ready to move to graphics, implement these methods
    """
    
    @staticmethod
    def render_to_image(generator: BaseGenerator, 
                       tile_size: int = 16,
                       output_file: str = 'output.png'):
        """
        TODO: Render to PNG using PIL/matplotlib
        
        Args:
            generator: Any generator
            tile_size: Pixels per tile
            output_file: Output filename
        """
        raise NotImplementedError("Graphics rendering not yet implemented")
    
    @staticmethod
    def render_to_canvas(generator: BaseGenerator,
                        canvas_width: int = 800,
                        canvas_height: int = 600):
        """
        TODO: Render to a game canvas (pygame, tkinter, etc.)
        
        Args:
            generator: Any generator
            canvas_width: Canvas width in pixels
            canvas_height: Canvas height in pixels
        """
        raise NotImplementedError("Graphics rendering not yet implemented")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from dungeon_generator import DungeonGenerator
    from city_generator import CityGenerator
    from object_populator import ObjectPopulator
    
    print("=" * 70)
    print("UNIFIED RENDERING SYSTEM")
    print("=" * 70)
    
    # Example 1: Render dungeon
    print("\n" + "=" * 70)
    print("DUNGEON - Full Render")
    print("=" * 70)
    
    dungeon = DungeonGenerator(60, 25, algorithm='bsp', seed=42)
    dungeon.generate()
    
    # Populate with objects
    populator = ObjectPopulator('game_objects_wordnet.json')
    populator.populate_dungeon(dungeon, 'medium')
    
    # Render!
    print(render(dungeon))
    
    # Example 2: Render city
    print("\n" + "=" * 70)
    print("CITY - Full Render")
    print("=" * 70)
    
    garden_city = CityGenerator(70, 30, city_type='grid', seed=456)
    garden_city.generate()
    populator.populate_themed(garden_city, 'garden')
    
    # Render!
    print(render(garden_city))
    
    # Example 3: Zoom view
    print("\n" + "=" * 70)
    print("CITY - Zoom View (center)")
    print("=" * 70)
    
    print(render_zoom(garden_city, 35, 15, size=40))
    
    # Example 4: Plain text (no colors)
    print("\n" + "=" * 70)
    print("DUNGEON - Plain Text (no colors)")
    print("=" * 70)
    
    small_dungeon = DungeonGenerator(40, 15, algorithm='cellular', seed=999)
    small_dungeon.generate()
    
    print(render(small_dungeon, colorize=False))
    
    print("\n" + "=" * 70)
    print("USAGE EXAMPLES:")
    print("=" * 70)
    print("""
    # Simple - just render anything
    print(render(dungeon))
    print(render(city))
    print(render(garden_city))
    
    # With options
    print(render(dungeon, show_objects=False))  # Hide objects
    print(render(city, colorize=False))          # Plain text
    
    # Zoom views
    print(render_zoom(dungeon, 30, 15))
    print(render_zoom(city, 50, 25, size=60))
    
    # Future graphics (TODO)
    # GraphicsAdapter.render_to_image(dungeon, 'dungeon.png')
    # GraphicsAdapter.render_to_canvas(city)
    """)
    
    print("=" * 70)
    print("READY FOR GRAPHICS!")
    print("When you're ready, implement GraphicsAdapter methods")
    print("=" * 70)
