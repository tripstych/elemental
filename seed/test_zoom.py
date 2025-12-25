"""
Test script for zoom view system
Demonstrates creating detailed views from world tiles
"""

from seed_world_generator import SeedWorldGenerator
from growth_patterns import GrowthPatterns
from render_features import RenderFeatures, create_zoom_views
from paths import SEED_CONFIG
import json

print("="*70)
print("ZOOM VIEW SYSTEM TEST")
print("="*70)

# Load seed config
with open(SEED_CONFIG, 'r') as f:
    seed_defs = json.load(f)

# Convert function names to actual functions
for name, config in seed_defs.items():
    if 'growth_function' in config:
        func_name = config['growth_function']
        if hasattr(GrowthPatterns, func_name):
            config['growth_function'] = getattr(GrowthPatterns, func_name)

# Create small world
print("\n1. Generating world...")
world = SeedWorldGenerator(100, 100, seed_definitions=seed_defs, world_seed=42)

# Place some seeds manually to ensure variety
world.add_seed(20, 20, 'desert')
world.add_seed(50, 50, 'forest')
world.add_seed(80, 80, 'grassland')
world.add_seed(30, 70, 'mountain')

world.grow_seeds(iterations=40)

print("\n2. Creating zoom views...")

# Create zoom view for desert tile
print("\n" + "="*70)
print("DESERT ZOOM VIEW")
print("="*70)
desert_view = RenderFeatures(world, tile_x=20, tile_y=20, zoom_size=40)
desert_view.render_ascii(show_coords=True)

print("\nDesert statistics:")
stats = desert_view.get_statistics()
for key, value in stats.items():
    print(f"  {key}: {value}")

# Create zoom view for forest tile
print("\n" + "="*70)
print("FOREST ZOOM VIEW")
print("="*70)
forest_view = RenderFeatures(world, tile_x=50, tile_y=50, zoom_size=40)
forest_view.render_ascii(show_coords=True)

print("\nForest statistics:")
stats = forest_view.get_statistics()
for key, value in stats.items():
    print(f"  {key}: {value}")

# Create multiple views
print("\n" + "="*70)
print("SAMPLING DIFFERENT TERRAINS")
print("="*70)
views = create_zoom_views(world, num_samples=4)

for terrain, view in views.items():
    print(f"\n{terrain.upper()}:")
    print("-" * 40)
    view.render_ascii(show_coords=False)
    stats = view.get_statistics()
    print(f"Features: {stats['total_features']}, Empty: {stats['empty_cells']}")

print("\n" + "="*70)
print("DONE!")
print("\nTo edit features:")
print("  python feature_editor.py")
print("\nTo use in your code:")
print("  from render_features import RenderFeatures")
print("  view = RenderFeatures(world, x, y)")
print("  view.render_ascii()")
print("="*70)
