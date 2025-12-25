"""
Seed-Based World Generation
Data-driven architecture with dict-based seed definitions
Now includes integrated pathfinding & fractal growth algorithms
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Callable, Any
import matplotlib.pyplot as plt
import json

# Import pathfinding if available
try:
    from pathfinding import CollisionMap, PathFinder, FractalGrowth
    PATHFINDING_AVAILABLE = True
except ImportError:
    PATHFINDING_AVAILABLE = False
    print("Warning: pathfinding.py not found. Advanced growth patterns disabled.")

from growth_patterns import GrowthPatterns
from  seed_world_generator import SeedWorldGenerator

# Test
if __name__ == "__main__":
    print("="*70)
    print("DATA-DRIVEN SEED WORLD GENERATION")
    print("="*70)
    
    world = SeedWorldGenerator(width=200, height=200, world_seed=42)
    
    # Show available seed types
    print("\nAvailable seed types:")
    for name, config in world.seed_definitions.items():
        print(f"  - {name:15s}: {config['description']}")
    
    # Place random seeds
    world.random_seeds()
    
    # Grow
    world.grow_seeds(iterations=80)
    
    # Stats
    world.get_statistics()
    
    # Save config
    world.save_config('seed_config.json')
    
    # Visualize
    world.visualize('seed_world_v2.png')
    
    print("\nDone!")
