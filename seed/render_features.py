"""
Zoom View System
Generates detailed tile view from world data using landscape features
"""

import numpy as np
import random
import json
from typing import Dict, List, Optional
from paths import LANDSCAPE_FEATURES


class RenderFeatures:
    """
    Creates a detailed view of a single world tile
    Places landscape features based on terrain type
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
    
    def __init__(self, 
                 world_generator,
                 tile_x: int, 
                 tile_y: int, 
                 zoom_size: int = 50,
                 features_file: str = None):
        """
        Args:
            world_generator: The SeedWorldGenerator instance
            tile_x, tile_y: Which world tile to zoom into
            zoom_size: Size of zoomed view (NxN cells)
            features_file: JSON file with landscape feature definitions (defaults to data/landscape_features.json)
        """
        self.world = world_generator
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.zoom_size = zoom_size
        
        # Load feature definitions
        if features_file is None:
            features_file = LANDSCAPE_FEATURES
        with open(features_file, 'r') as f:
            self.feature_defs = json.load(f)
        
        # Get terrain type at this location
        self.terrain_type = self.world.terrain_type[tile_y, tile_x]
        self.elevation = self.world.elevation[tile_y, tile_x]
        
        # Generate feature map
        self.feature_map = self._generate_features()
    
    def _generate_features(self):
        """Generate feature placement for this tile"""
        # Get feature list for this terrain
        terrain_def = self.feature_defs.get(self.terrain_type, {})
        features = terrain_def.get('features', [])
        
        # Initialize empty map
        feature_map = [[None for _ in range(self.zoom_size)] 
                       for _ in range(self.zoom_size)]
        
        # Place each feature type
        for feature in features:
            if feature.get('cluster', False):
                self._place_clustered(feature_map, feature)
            else:
                self._place_random(feature_map, feature)
        
        return feature_map
    
    def _place_random(self, feature_map, feature):
        """Place features randomly based on density"""
        density = feature['density']
        
        for y in range(self.zoom_size):
            for x in range(self.zoom_size):
                if feature_map[y][x] is None and random.random() < density:
                    feature_map[y][x] = feature
    
    def _place_clustered(self, feature_map, feature):
        """Place features in clusters"""
        density = feature['density']
        cluster_size = feature.get('cluster_size', 5)
        
        # Determine number of clusters
        total_cells = self.zoom_size * self.zoom_size
        expected_features = int(total_cells * density)
        num_clusters = max(1, expected_features // cluster_size)
        
        for _ in range(num_clusters):
            # Pick random cluster center
            cx = random.randint(0, self.zoom_size - 1)
            cy = random.randint(0, self.zoom_size - 1)
            
            # Place cluster
            for _ in range(cluster_size):
                # Random offset from center
                dx = random.randint(-3, 3)
                dy = random.randint(-3, 3)
                
                x = cx + dx
                y = cy + dy
                
                if (0 <= x < self.zoom_size and 
                    0 <= y < self.zoom_size and 
                    feature_map[y][x] is None):
                    feature_map[y][x] = feature
    
    def render_ascii(self, show_coords: bool = False):
        """Render the zoom view as colored ASCII"""
        terrain_def = self.feature_defs.get(self.terrain_type, {})
        ground_char = terrain_def.get('ground_char', '.')
        ground_color = terrain_def.get('ground_color', 'white')
        
        if show_coords:
            print(f"Zoom view: World tile ({self.tile_x}, {self.tile_y}) - {self.terrain_type}")
            print(f"Elevation: {self.elevation:.2f}")
            print("-" * self.zoom_size)
        
        for y, row in enumerate(self.feature_map):
            line = ""
            for x, cell in enumerate(row):
                if cell:
                    char = cell['char']
                    color = cell.get('color', 'white')
                    line += self._colorize(char, color)
                else:
                    line += self._colorize(ground_char, ground_color)
            print(line)
        
        print(self.COLORS['reset'])  # Reset color at end
    
    def render_plain(self):
        """Render without colors (for saving to file)"""
        terrain_def = self.feature_defs.get(self.terrain_type, {})
        ground_char = terrain_def.get('ground_char', '.')
        
        lines = []
        for row in self.feature_map:
            line = ""
            for cell in row:
                if cell:
                    line += cell['char']
                else:
                    line += ground_char
            lines.append(line)
        
        return '\n'.join(lines)
    
    def _colorize(self, char: str, color: str) -> str:
        """Add ANSI color code to character"""
        color_code = self.COLORS.get(color, self.COLORS['white'])
        return f"{color_code}{char}{self.COLORS['reset']}"
    
    def get_feature_at(self, x: int, y: int) -> Optional[Dict]:
        """Get feature at specific position"""
        if 0 <= x < self.zoom_size and 0 <= y < self.zoom_size:
            return self.feature_map[y][x]
        return None
    
    def get_statistics(self):
        """Get statistics about features in this view"""
        feature_counts = {}
        
        for row in self.feature_map:
            for cell in row:
                if cell:
                    name = cell['name']
                    feature_counts[name] = feature_counts.get(name, 0) + 1
        
        return {
            'terrain': self.terrain_type,
            'elevation': self.elevation,
            'feature_counts': feature_counts,
            'total_features': sum(feature_counts.values()),
            'empty_cells': self.zoom_size * self.zoom_size - sum(feature_counts.values())
        }

    @classmethod
    def render_terrain(cls, terrain_name: str, terrain_def: dict, size: int = 35, seed: int = 42) -> str:
        """
        Render a preview for a terrain type without needing a world generator.
        Used by the feature editor.
        
        Args:
            terrain_name: Name of the terrain type
            terrain_def: Dict with 'features', 'ground_char', 'ground_color'
            size: Size of preview grid
            seed: Random seed for consistent preview
            
        Returns:
            Plain text string of the rendered preview
        """
        random.seed(seed)
        
        features = terrain_def.get('features', [])
        ground_char = terrain_def.get('ground_char', '.')
        
        # Initialize empty map
        feature_map = [[None for _ in range(size)] for _ in range(size)]
        
        # Place each feature type
        for feature in features:
            density = feature.get('density', 0.1)
            
            if feature.get('cluster', False):
                # Clustered placement
                cluster_size = feature.get('cluster_size', 5)
                total_cells = size * size
                expected_features = int(total_cells * density)
                num_clusters = max(1, expected_features // cluster_size)
                
                for _ in range(num_clusters):
                    cx = random.randint(0, size - 1)
                    cy = random.randint(0, size - 1)
                    
                    for _ in range(cluster_size):
                        dx = random.randint(-3, 3)
                        dy = random.randint(-3, 3)
                        x, y = cx + dx, cy + dy
                        
                        if 0 <= x < size and 0 <= y < size and feature_map[y][x] is None:
                            feature_map[y][x] = feature
            else:
                # Random placement
                for y in range(size):
                    for x in range(size):
                        if feature_map[y][x] is None and random.random() < density:
                            feature_map[y][x] = feature
        
        # Render to string
        lines = []
        for row in feature_map:
            line = ""
            for cell in row:
                if cell:
                    line += cell.get('char', '?')
                else:
                    line += ground_char
            lines.append(line)
        
        return '\n'.join(lines)

    @classmethod
    def render_terrain_colored(cls, terrain_name: str, terrain_def: dict, size: int = 35, seed: int = 42):
        """
        Render and print a colorized version to the console using ANSI codes.
        
        Args:
            terrain_name: Name of the terrain type
            terrain_def: Dict with 'features', 'ground_char', 'ground_color'
            size: Size of preview grid
            seed: Random seed for consistent preview
        """
        random.seed(seed)
        
        features = terrain_def.get('features', [])
        ground_char = terrain_def.get('ground_char', '.')
        ground_color = terrain_def.get('ground_color', 'white')
        
        # Initialize empty map
        feature_map = [[None for _ in range(size)] for _ in range(size)]
        
        # Place each feature type
        for feature in features:
            density = feature.get('density', 0.1)
            
            if feature.get('cluster', False):
                cluster_size = feature.get('cluster_size', 5)
                total_cells = size * size
                expected_features = int(total_cells * density)
                num_clusters = max(1, expected_features // cluster_size)
                
                for _ in range(num_clusters):
                    cx = random.randint(0, size - 1)
                    cy = random.randint(0, size - 1)
                    
                    for _ in range(cluster_size):
                        dx = random.randint(-3, 3)
                        dy = random.randint(-3, 3)
                        x, y = cx + dx, cy + dy
                        
                        if 0 <= x < size and 0 <= y < size and feature_map[y][x] is None:
                            feature_map[y][x] = feature
            else:
                for y in range(size):
                    for x in range(size):
                        if feature_map[y][x] is None and random.random() < density:
                            feature_map[y][x] = feature
        
        # Print colorized output
        print(f"\n{cls.COLORS['bright_white']}=== {terrain_name.upper()} ==={cls.COLORS['reset']}")
        
        for row in feature_map:
            line = ""
            for cell in row:
                if cell:
                    char = cell.get('char', '?')
                    color = cell.get('color', 'white')
                    color_code = cls.COLORS.get(color, cls.COLORS['white'])
                    line += f"{color_code}{char}{cls.COLORS['reset']}"
                else:
                    color_code = cls.COLORS.get(ground_color, cls.COLORS['white'])
                    line += f"{color_code}{ground_char}{cls.COLORS['reset']}"
            print(line)
        
        print(cls.COLORS['reset'])


def create_zoom_views(world_generator, num_samples: int = 3):
    """Create sample zoom views from different terrains"""
    # Find one tile of each terrain type
    terrain_samples = {}
    
    for y in range(world_generator.height):
        for x in range(world_generator.width):
            terrain = world_generator.terrain_type[y, x]
            if terrain and terrain not in terrain_samples:
                terrain_samples[terrain] = (x, y)
                if len(terrain_samples) >= num_samples:
                    break
        if len(terrain_samples) >= num_samples:
            break
    
    # Create zoom views
    views = {}
    for terrain, (x, y) in terrain_samples.items():
        views[terrain] = RenderFeatures(world_generator, x, y)
    
    return views


if __name__ == "__main__":
    print("ZoomView requires a world generator instance")
    print("Usage:")
    print("  from zoom_view import ZoomView")
    print("  view = ZoomView(world_gen, tile_x=50, tile_y=50)")
    print("  view.render_ascii(show_coords=True)")
