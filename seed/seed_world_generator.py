import random
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from typing import Dict
from game_object import GameObject

class SeedWorldGenerator(GameObject):
    """
    Data-driven world generator using dict-based seed definitions
    """
    
    def __init__(self, width, height, seed_definitions=None, world_seed=None):
        self.width = width
        self.height = height
        self.world_seed = world_seed if world_seed else random.randint(0, 999999)
        
        random.seed(self.world_seed)
        np.random.seed(self.world_seed)
        
        # World data
        self.terrain_type = np.full((height, width), '', dtype=object)
        self.terrain_strength = np.zeros((height, width))
        self.elevation = np.zeros((height, width))
        self.resources = [[[] for _ in range(width)] for _ in range(height)]
        self.metadata = [[{} for _ in range(width)] for _ in range(height)]
        
        self.seeds = []
        
        self.seed_definitions = seed_definitions if seed_definitions else {}
    
    
    def add_seed(self, x: int, y: int, seed_type: str, strength_multiplier: float = 1.0, **custom_params):
        """
        Add a seed to the world
        
        Args:
            x, y: Position
            seed_type: Name of seed type from definitions
            strength_multiplier: Modify base strength
            **custom_params: Override any config parameters for this specific seed
        """
        if seed_type not in self.seed_definitions:
            print(f"Unknown seed type: {seed_type}")
            return
        
        config = self.seed_definitions[seed_type].copy()
        
        # Apply custom parameters
        if custom_params:
            config.update(custom_params)
        
        seed = {
            'x': x,
            'y': y,
            'type': seed_type,
            'strength': config['strength'] * strength_multiplier,
            'age': 0,
            'config': config
        }
        
        self.seeds.append(seed)
        print(f"Placed {seed_type} seed at ({x}, {y})")
    
    def random_seeds(self, distribution: Dict[str, int] = None):
        """
        Place random seeds
        
        Args:
            distribution: Dict of {seed_type: count}
        """
        if distribution is None:
            distribution = {
                'ocean': 3,
                'mountain': 4,
                'forest': 6,
                'desert': 3,
                'grassland': 8,
                'swamp': 2,
                'volcano': 1,
                'crystal_field': 2
            }
        
        for seed_type, count in distribution.items():
            if seed_type not in self.seed_definitions:
                print(f"Warning: Unknown seed type '{seed_type}' in distribution")
                continue
            
            for _ in range(count):
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                strength_var = random.uniform(0.8, 1.2)
                self.add_seed(x, y, seed_type, strength_var)
    
    def grow_seeds(self, iterations: int = 80):
        """Grow all seeds over multiple iterations"""
        print(f"\nGrowing {len(self.seeds)} seeds over {iterations} iterations...")
        
        for iteration in range(iterations):
            if iteration % 20 == 0:
                print(f"  Iteration {iteration}/{iterations}...")
            
            for seed in self.seeds:
                self._grow_seed(seed, iteration)
                seed['age'] += 1
        
        print("Growth complete!")
        self._finalize_terrain()
    
    def _grow_seed(self, seed: Dict, iteration: int):
        """Grow a single seed"""
        config = seed['config']
        
        # Calculate growth radius
        max_growth = min(
            config['max_radius'],
            int(config['growth_rate'] * seed['age'])
        )
        
        # Call the growth function
        growth_function = config['growth_function']
        growth_function(self, seed, config, max_growth)
    
    def _claim_cell(self, x: int, y: int, seed: Dict, strength: float, config: Dict):
        """Try to claim a cell for a seed"""
        if strength > self.terrain_strength[y, x]:
            self.terrain_type[y, x] = seed['type']
            self.terrain_strength[y, x] = strength
            self.elevation[y, x] = config['elevation']
            
            # Add resources
            if random.random() < strength * 0.3:
                self.resources[y][x] = config['resources'].copy()
            
            # Store metadata
            self.metadata[y][x] = {
                'seed_id': id(seed),
                'distance_from_seed': np.sqrt((x - seed['x'])**2 + (y - seed['y'])**2)
            }
    
    def _finalize_terrain(self):
        """Post-processing"""
        # Fill empty cells
        for y in range(self.height):
            for x in range(self.width):
                if self.terrain_type[y, x] == '':
                    self.terrain_type[y, x] = 'grassland'
                    self.terrain_strength[y, x] = 0.1
                    self.elevation[y, x] = 0.15
        
        # Smooth elevation
        self.elevation = self._smooth_elevation(self.elevation, iterations=2)
    
    def _smooth_elevation(self, elev, iterations=2):
        """Light smoothing"""
        result = elev.copy()
        for _ in range(iterations):
            smoothed = result.copy()
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    neighbors = [
                        result[y-1, x], result[y+1, x],
                        result[y, x-1], result[y, x+1]
                    ]
                    smoothed[y, x] = result[y, x] * 0.6 + np.mean(neighbors) * 0.4
            result = smoothed
        return result
    
    def save_config(self, filename: str):
        """Save seed definitions to JSON file"""
        # Convert functions to names
        serializable = {}
        for name, config in self.seed_definitions.items():
            config_copy = config.copy()
            if 'growth_function' in config_copy:
                config_copy['growth_function'] = config_copy['growth_function'].__name__
            serializable[name] = config_copy
        
        with open(filename, 'w') as f:
            json.dump(serializable, f, indent=2)
        print(f"Saved configuration to {filename}")
    
    def visualize(self, filename='seed_world.png'):
        """Create visualization"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 16))
        fig.suptitle(f'Seed-Based World (Seed: {self.world_seed})', fontsize=16, fontweight='bold')
        
        # Terrain types
        ax = axes[0, 0]
        terrain_colors = np.zeros((self.height, self.width, 3))
        
        for y in range(self.height):
            for x in range(self.width):
                terrain = self.terrain_type[y, x]
                if terrain in self.seed_definitions:
                    color_hex = self.seed_definitions[terrain]['color']
                    color_hex = color_hex.lstrip('#')
                    rgb = tuple(int(color_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                    terrain_colors[y, x] = rgb
        
        ax.imshow(terrain_colors, interpolation='nearest')
        ax.set_title('Terrain Types', fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # Mark seeds
        for seed in self.seeds:
            ax.scatter(seed['x'], seed['y'], c='red', s=100, marker='*',
                      edgecolors='white', linewidths=2, zorder=10)
        
        # Elevation
        ax = axes[0, 1]
        im = ax.imshow(self.elevation, cmap='terrain', interpolation='bilinear')
        ax.set_title('Elevation', fontsize=14, fontweight='bold')
        ax.axis('off')
        plt.colorbar(im, ax=ax, fraction=0.046)
        
        # Strength
        ax = axes[1, 0]
        im = ax.imshow(self.terrain_strength, cmap='hot', interpolation='bilinear')
        ax.set_title('Terrain Strength', fontsize=14, fontweight='bold')
        ax.axis('off')
        plt.colorbar(im, ax=ax, fraction=0.046)
        
        # Resources
        ax = axes[1, 1]
        resource_density = np.zeros((self.height, self.width))
        for y in range(self.height):
            for x in range(self.width):
                resource_density[y, x] = len(self.resources[y][x])
        
        im = ax.imshow(resource_density, cmap='YlOrRd', interpolation='nearest')
        ax.set_title('Resource Density', fontsize=14, fontweight='bold')
        ax.axis('off')
        plt.colorbar(im, ax=ax, fraction=0.046)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to {filename}")
        plt.close()
    
    def get_statistics(self):
        """Print statistics"""
        terrain_counts = {}
        for y in range(self.height):
            for x in range(self.width):
                terrain = self.terrain_type[y, x]
                terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
        
        total = self.width * self.height
        
        print(f"\n{'='*60}")
        print("WORLD STATISTICS")
        print(f"{'='*60}")
        print(f"Size: {self.width}x{self.height} ({total:,} cells)")
        print(f"Seeds: {len(self.seeds)}")
        print(f"\nTerrain distribution:")
        
        for terrain, count in sorted(terrain_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            desc = self.seed_definitions.get(terrain, {}).get('description', 'Unknown')
            print(f"  {terrain:15s}: {count:6,} cells ({pct:5.1f}%) - {desc}")

