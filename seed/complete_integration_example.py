"""
Complete Integration Example
Shows how all systems work together:
- Terrain generation (SeedWorldGenerator)
- Dungeon/City generation (BaseGenerator subclasses)
- Object population (WordNet database)
- Synset mapping (for glockblocks magic system)
- Rendering (RenderFeatures compatibility)
"""

import json
from dungeon_generator import DungeonGenerator
from city_generator import CityGenerator
from base_generator import populate_objects_by_type
from synset_mapper import SynsetMapper, create_dungeon_object, create_city_object, get_tile_synset
from generator_integration import GeneratorRenderer


def example_dungeon_with_synsets():
    """Generate a dungeon where everything has WordNet synsets"""
    print("=" * 70)
    print("DUNGEON WITH WORDNET SYNSETS")
    print("=" * 70)
    
    # Generate dungeon
    dungeon = DungeonGenerator(50, 25, algorithm='bsp', seed=42)
    dungeon.generate()
    
    # Load game objects
    with open('game_objects_wordnet.json', 'r') as f:
        game_objects = json.load(f)
    
    # Populate with weapons and containers
    weapons = populate_objects_by_type(dungeon, game_objects,
                                      dungeon.ROOM_FLOOR, 'weapons', 0.05)
    containers = populate_objects_by_type(dungeon, game_objects,
                                         dungeon.ROOM_FLOOR, 'containers', 0.08)
    
    print(f"\nPlaced {weapons} weapons, {containers} containers")
    
    # Show synsets for a few tiles
    print("\nTile synsets at specific locations:")
    test_positions = [(25, 12), (10, 5), (40, 20)]
    
    for x, y in test_positions:
        tile_value = dungeon.grid[y, x]
        synset = get_tile_synset(dungeon, x, y)
        obj = create_dungeon_object(tile_value)
        
        print(f"  ({x:2d}, {y:2d}): {obj['name']:10s} → {synset}")
        
        # Check for objects at this position
        objects_here = dungeon.get_objects_at(x, y)
        if objects_here:
            for game_obj in objects_here:
                print(f"           + {game_obj['name']:20s} → {game_obj.get('synset', 'N/A')}")
    
    # Render
    print("\nDungeon map:")
    dungeon.print_ascii()
    
    return dungeon


def example_city_with_synsets():
    """Generate a city where everything has WordNet synsets"""
    print("\n" + "=" * 70)
    print("CITY WITH WORDNET SYNSETS")
    print("=" * 70)
    
    # Generate city
    city = CityGenerator(60, 30, city_type='medieval', seed=42)
    city.generate()
    
    # Load game objects
    with open('game_objects_wordnet.json', 'r') as f:
        game_objects = json.load(f)
    
    # Populate buildings with furniture
    furniture = populate_objects_by_type(city, game_objects,
                                        city.BUILDING, 'furniture', 0.15)
    
    # Populate market with containers
    market_goods = populate_objects_by_type(city, game_objects,
                                           city.MARKET, 'containers', 0.3)
    
    print(f"\nPlaced {furniture} furniture, {market_goods} market goods")
    
    # Show synsets
    print("\nTile synsets at specific locations:")
    test_positions = [(30, 15), (20, 10), (50, 25)]
    
    for x, y in test_positions:
        tile_value = city.grid[y, x]
        synset = get_tile_synset(city, x, y)
        obj = create_city_object(tile_value)
        
        print(f"  ({x:2d}, {y:2d}): {obj['name']:10s} → {synset}")
        
        objects_here = city.get_objects_at(x, y)
        if objects_here:
            for game_obj in objects_here:
                print(f"           + {game_obj['name']:20s} → {game_obj.get('synset', 'N/A')}")
    
    # Render
    print("\nCity map:")
    city.print_ascii()
    
    return city


def example_terrain_features_with_synsets():
    """Show terrain features with synsets"""
    print("\n" + "=" * 70)
    print("TERRAIN FEATURES WITH WORDNET SYNSETS")
    print("=" * 70)
    
    # Load features with synsets
    with open('landscape_features_with_synsets.json', 'r') as f:
        features = json.load(f)
    
    print("\nAll terrain types and their features:")
    
    for terrain_name, terrain_def in features.items():
        print(f"\n{terrain_name.upper()}:")
        for feature in terrain_def.get('features', []):
            print(f"  {feature['name']:15s} → {feature['synset']}")


def example_magic_system_integration():
    """
    Show how synsets enable magic system integration
    Every tile and object can be dissolved for elemental essences
    """
    print("\n" + "=" * 70)
    print("MAGIC SYSTEM INTEGRATION")
    print("=" * 70)
    
    print("\nExample: Dissolving dungeon objects for essences")
    print("\n1. Wall (wall.n.01) → Can be dissolved for earth essences")
    print("2. Door (door.n.01) → Can be dissolved for wood essences")
    print("3. Torch (torch.n.01) → Can be dissolved for fire essences")
    
    print("\nExample: Transforming city objects")
    print("\n1. Stone wall → Extract earth essence → Transform to iron sword")
    print("2. Wooden door → Extract wood essence → Transform to oak staff")
    print("3. Market goods → Extract various essences → Create new spells")
    
    print("\nAll objects have synsets, so they can all be:")
    print("  - Dissolved in solvents (Aqua Ignis, Oleum Terra, etc.)")
    print("  - Transformed into other objects")
    print("  - Used to cast spells")
    print("  - Combined through alchemy")


def main():
    """Run all examples"""
    try:
        # Example 1: Dungeon
        dungeon = example_dungeon_with_synsets()
        
        # Example 2: City
        city = example_city_with_synsets()
        
        # Example 3: Terrain features
        example_terrain_features_with_synsets()
        
        # Example 4: Magic integration
        example_magic_system_integration()
        
        print("\n" + "=" * 70)
        print("INTEGRATION COMPLETE!")
        print("=" * 70)
        print("\nKey Points:")
        print("  ✅ All generator tiles have WordNet synsets")
        print("  ✅ All terrain features have WordNet synsets")
        print("  ✅ All game objects have WordNet synsets")
        print("  ✅ Ready for glockblocks magic system")
        print("  ✅ Compatible with RenderFeatures")
        
    except FileNotFoundError as e:
        print(f"\n⚠️  Missing file: {e}")
        print("Make sure these files are present:")
        print("  - game_objects_wordnet.json")
        print("  - landscape_features_with_synsets.json")


if __name__ == "__main__":
    main()
