"""
Base Generator Class
Parent class for all procedural generators (terrain, dungeons, cities, buildings)
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Any
from abc import ABC, abstractmethod
import json


class BaseGenerator(ABC):
    """
    Abstract base class for all generators
    Provides common functionality: seeding, grid management, object placement
    """
    
    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        """
        Args:
            width: Grid width
            height: Grid height
            seed: Random seed for reproducibility
        """
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 999999)
        
        # Set random seeds
        random.seed(self.seed)
        np.random.seed(self.seed)
        
        # Core data structures (all generators have these)
        self.grid = np.zeros((height, width), dtype=int)  # Main tile grid
        self.metadata = [[{} for _ in range(width)] for _ in range(height)]  # Per-cell data
        self.objects = [[[] for _ in range(width)] for _ in range(height)]  # Placed objects
        
        # Generation state
        self.generated = False
    
    @abstractmethod
    def generate(self):
        """
        Main generation method - must be implemented by subclasses
        Should populate self.grid with appropriate values
        """
        pass
    
    def place_object(self, x: int, y: int, obj: Dict[str, Any]) -> bool:
        """
        Place a game object at a position
        
        Args:
            x, y: Position
            obj: Object dict (from game_objects database)
            
        Returns:
            True if placed successfully
        """
        if not self.is_valid_position(x, y):
            return False
        
        self.objects[y][x].append(obj)
        return True
    
    def get_objects_at(self, x: int, y: int) -> List[Dict]:
        """Get all objects at a position"""
        if self.is_valid_position(x, y):
            return self.objects[y][x]
        return []
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within bounds"""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_tile(self, x: int, y: int) -> int:
        """Get tile value at position"""
        if self.is_valid_position(x, y):
            return self.grid[y, x]
        return -1  # Out of bounds
    
    def set_tile(self, x: int, y: int, value: int):
        """Set tile value at position"""
        if self.is_valid_position(x, y):
            self.grid[y, x] = value
    
    def set_metadata(self, x: int, y: int, key: str, value: Any):
        """Store metadata at a position"""
        if self.is_valid_position(x, y):
            self.metadata[y][x][key] = value
    
    def get_metadata(self, x: int, y: int, key: str, default=None) -> Any:
        """Retrieve metadata from a position"""
        if self.is_valid_position(x, y):
            return self.metadata[y][x].get(key, default)
        return default
    
    def get_neighbors(self, x: int, y: int, diagonal: bool = False) -> List[Tuple[int, int]]:
        """
        Get neighboring positions
        
        Args:
            x, y: Center position
            diagonal: Include diagonal neighbors
            
        Returns:
            List of (x, y) tuples
        """
        neighbors = []
        
        # Cardinal directions
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        
        # Diagonal
        if diagonal:
            for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
                nx, ny = x + dx, y + dy
                if self.is_valid_position(nx, ny):
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def count_neighbors(self, x: int, y: int, value: int, diagonal: bool = False) -> int:
        """Count neighbors with specific tile value"""
        count = 0
        for nx, ny in self.get_neighbors(x, y, diagonal):
            if self.grid[ny, nx] == value:
                count += 1
        return count
    
    def flood_fill(self, start_x: int, start_y: int, target_value: int, 
                   replace_value: int, diagonal: bool = False):
        """
        Flood fill algorithm
        
        Args:
            start_x, start_y: Starting position
            target_value: Value to replace
            replace_value: New value
            diagonal: Allow diagonal spreading
        """
        if not self.is_valid_position(start_x, start_y):
            return
        
        if self.grid[start_y, start_x] != target_value:
            return
        
        stack = [(start_x, start_y)]
        visited = set()
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            
            if not self.is_valid_position(x, y):
                continue
            
            if self.grid[y, x] != target_value:
                continue
            
            visited.add((x, y))
            self.grid[y, x] = replace_value
            
            # Add neighbors to stack
            for nx, ny in self.get_neighbors(x, y, diagonal):
                if (nx, ny) not in visited:
                    stack.append((nx, ny))
    
    def find_positions(self, value: int) -> List[Tuple[int, int]]:
        """Find all positions with a specific tile value"""
        positions = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y, x] == value:
                    positions.append((x, y))
        return positions
    
    def random_position(self, value: Optional[int] = None) -> Tuple[int, int]:
        """
        Get a random position
        
        Args:
            value: If specified, only return positions with this tile value
            
        Returns:
            (x, y) tuple
        """
        if value is None:
            return random.randint(0, self.width - 1), random.randint(0, self.height - 1)
        else:
            positions = self.find_positions(value)
            if not positions:
                raise ValueError(f"No positions found with value {value}")
            return random.choice(positions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the generated content"""
        if not self.generated:
            return {"error": "Not yet generated"}
        
        # Count tile types
        unique, counts = np.unique(self.grid, return_counts=True)
        tile_counts = dict(zip(unique.tolist(), counts.tolist()))
        
        # Count objects
        total_objects = sum(len(cell) for row in self.objects for cell in row)
        
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "tile_counts": tile_counts,
            "total_objects": total_objects,
            "generated": self.generated
        }
    
    def render_ascii(self, tile_chars: Dict[int, str] = None, 
                    show_objects: bool = False) -> str:
        """
        Render grid as ASCII
        
        Args:
            tile_chars: Dict mapping tile values to characters
            show_objects: Show objects instead of tiles
            
        Returns:
            ASCII string representation
        """
        if tile_chars is None:
            tile_chars = {0: '.', 1: '#'}  # Default: floor/wall
        
        lines = []
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                if show_objects and self.objects[y][x]:
                    # Show first object at position
                    obj = self.objects[y][x][0]
                    line += obj.get('char', '?')
                else:
                    tile_value = self.grid[y, x]
                    line += tile_chars.get(tile_value, '?')
            lines.append(line)
        
        return '\n'.join(lines)
    
    def print_ascii(self, tile_chars: Dict[int, str] = None, 
                   show_objects: bool = False):
        """Print ASCII representation to console"""
        print(self.render_ascii(tile_chars, show_objects))
    
    def save_to_file(self, filename: str):
        """Save grid and metadata to file"""
        data = {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "grid": self.grid.tolist(),
            "metadata": self.metadata,
            "objects": self.objects,
            "generator_type": self.__class__.__name__
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved to {filename}")
    
    @classmethod
    def load_from_file(cls, filename: str):
        """Load grid and metadata from file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Create instance
        instance = cls(data['width'], data['height'], seed=data['seed'])
        instance.grid = np.array(data['grid'])
        instance.metadata = data['metadata']
        instance.objects = data['objects']
        instance.generated = True
        
        return instance
    
    def __repr__(self):
        return f"{self.__class__.__name__}(width={self.width}, height={self.height}, seed={self.seed})"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def populate_objects_by_type(generator: BaseGenerator, 
                            game_objects: List[Dict],
                            tile_type: int,
                            object_type: str,
                            density: float = 0.1) -> int:
    """
    Populate a generator with objects of a specific type
    
    Args:
        generator: Any BaseGenerator subclass
        game_objects: List of game objects from database
        tile_type: Which tile value to place objects on
        object_type: Object type to filter (e.g., 'weapons', 'furniture')
        density: Probability of placing object (0.0-1.0)
        
    Returns:
        Number of objects placed
    """
    # Filter objects by type
    filtered = [obj for obj in game_objects if obj.get('type') == object_type]
    
    if not filtered:
        return 0
    
    placed = 0
    positions = generator.find_positions(tile_type)
    
    for x, y in positions:
        if random.random() < density:
            obj = random.choice(filtered)
            if generator.place_object(x, y, obj):
                placed += 1
    
    return placed


def populate_objects_by_material(generator: BaseGenerator,
                                game_objects: List[Dict],
                                tile_type: int,
                                material: str,
                                density: float = 0.1) -> int:
    """
    Populate with objects of a specific material
    
    Args:
        generator: Any BaseGenerator subclass
        game_objects: List of game objects from database
        tile_type: Which tile value to place objects on
        material: Material type (e.g., 'wood', 'stone', 'metal')
        density: Probability of placing object
        
    Returns:
        Number of objects placed
    """
    # Filter by material
    filtered = [obj for obj in game_objects if obj.get('material') == material]
    
    if not filtered:
        return 0
    
    placed = 0
    positions = generator.find_positions(tile_type)
    
    for x, y in positions:
        if random.random() < density:
            obj = random.choice(filtered)
            if generator.place_object(x, y, obj):
                placed += 1
    
    return placed


if __name__ == "__main__":
    print("BaseGenerator is an abstract class")
    print("Create subclasses: DungeonGenerator, CityGenerator, BuildingGenerator")
    print("\nAll subclasses get:")
    print("  - Grid management")
    print("  - Object placement")
    print("  - Metadata storage")
    print("  - ASCII rendering")
    print("  - Save/load functionality")
