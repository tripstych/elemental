"""
Intelligent Object Population
Populates generators with contextually appropriate objects from the WordNet database
"""

import json
import random
from typing import List, Dict
from base_generator import BaseGenerator


class ObjectPopulator:
    """
    Smart object population that places appropriate items in appropriate locations
    """
    
    def __init__(self, objects_file: str = 'game_objects_wordnet.json'):
        """Load game objects database"""
        with open(objects_file, 'r') as f:
            self.all_objects = json.load(f)
        
        # Index by type and material for fast lookup
        self.by_type = {}
        self.by_material = {}
        
        for obj in self.all_objects:
            obj_type = obj.get('type', 'unknown')
            material = obj.get('material', 'unknown')
            
            if obj_type not in self.by_type:
                self.by_type[obj_type] = []
            self.by_type[obj_type].append(obj)
            
            if material not in self.by_material:
                self.by_material[material] = []
            self.by_material[material].append(obj)
        
        print(f"Loaded {len(self.all_objects)} objects")
        print(f"  {len(self.by_type)} types, {len(self.by_material)} materials")
    
    # ========================================================================
    # DUNGEON POPULATION
    # ========================================================================
    
    def populate_dungeon(self, dungeon, density: str = 'medium') -> Dict[str, int]:
        """
        Intelligently populate a dungeon with appropriate objects
        
        Args:
            dungeon: DungeonGenerator instance
            density: 'sparse', 'medium', 'dense'
            
        Returns:
            Dict of placement counts
        """
        from dungeon_generator import DungeonGenerator
        
        densities = {
            'sparse': {'weapons': 0.03, 'containers': 0.05, 'furniture': 0.04},
            'medium': {'weapons': 0.05, 'containers': 0.08, 'furniture': 0.07},
            'dense': {'weapons': 0.08, 'containers': 0.12, 'furniture': 0.10}
        }
        
        rates = densities.get(density, densities['medium'])
        counts = {}
        
        # Weapons in rooms and corridors
        counts['weapons'] = self._place_objects(
            dungeon, 
            self.by_type.get('weapons', []),
            [DungeonGenerator.ROOM_FLOOR, DungeonGenerator.FLOOR],
            rates['weapons']
        )
        
        # Containers (chests, barrels, etc) in rooms
        counts['containers'] = self._place_objects(
            dungeon,
            self.by_type.get('containers', []),
            [DungeonGenerator.ROOM_FLOOR],
            rates['containers']
        )
        
        # Furniture in rooms only
        counts['furniture'] = self._place_objects(
            dungeon,
            self.by_type.get('furniture', []),
            [DungeonGenerator.ROOM_FLOOR],
            rates['furniture']
        )
        
        # Add some tools/equipment
        counts['tools'] = self._place_objects(
            dungeon,
            self.by_type.get('tools', []),
            [DungeonGenerator.ROOM_FLOOR, DungeonGenerator.CORRIDOR],
            rates['weapons'] * 0.5
        )
        
        return counts
    
    # ========================================================================
    # CITY POPULATION
    # ========================================================================
    
    def populate_city(self, city, density: str = 'medium') -> Dict[str, int]:
        """
        Intelligently populate a city with appropriate objects
        
        Args:
            city: CityGenerator instance
            density: 'sparse', 'medium', 'dense'
            
        Returns:
            Dict of placement counts
        """
        from city_generator import CityGenerator
        
        densities = {
            'sparse': 0.1,
            'medium': 0.15,
            'dense': 0.25
        }
        
        base_rate = densities.get(density, densities['medium'])
        counts = {}
        
        # Buildings: furniture, tools, containers
        counts['furniture_building'] = self._place_objects(
            city,
            self.by_type.get('furniture', []),
            [CityGenerator.BUILDING],
            base_rate
        )
        
        counts['containers_building'] = self._place_objects(
            city,
            self.by_type.get('containers', []),
            [CityGenerator.BUILDING],
            base_rate * 0.6
        )
        
        counts['tools_building'] = self._place_objects(
            city,
            self.by_type.get('tools', []),
            [CityGenerator.BUILDING],
            base_rate * 0.3
        )
        
        # Markets: containers, food, fabrics
        counts['containers_market'] = self._place_objects(
            city,
            self.by_type.get('containers', []),
            [CityGenerator.MARKET],
            base_rate * 2.0
        )
        
        counts['food_market'] = self._place_objects(
            city,
            self.by_type.get('food', []),
            [CityGenerator.MARKET],
            base_rate * 1.5
        )
        
        counts['fabrics_market'] = self._place_objects(
            city,
            self.by_type.get('fabrics', []),
            [CityGenerator.MARKET],
            base_rate * 0.8
        )
        
        # Parks: plants, trees
        counts['plants_park'] = self._place_objects(
            city,
            self.by_type.get('plants', []),
            [CityGenerator.PARK],
            base_rate * 3.0
        )
        
        counts['trees_park'] = self._place_objects(
            city,
            self.by_type.get('trees', []),
            [CityGenerator.PARK],
            base_rate * 0.5
        )
        
        return counts
    
    # ========================================================================
    # THEMED POPULATION
    # ========================================================================
    
    def populate_themed(self, generator, theme: str) -> Dict[str, int]:
        """
        Populate based on theme
        
        Themes:
            - 'treasure': gems, gold, valuable containers
            - 'armory': weapons, armor
            - 'library': furniture (desks, shelves), containers
            - 'kitchen': food, containers, tools
            - 'garden': plants, trees, flowers
            - 'forge': metal objects, tools
            - 'alchemist': containers, liquids, gems
        """
        from dungeon_generator import DungeonGenerator
        from city_generator import CityGenerator
        
        counts = {}
        
        if theme == 'treasure':
            # Gems everywhere
            counts['gems'] = self._place_objects(
                generator,
                self.by_type.get('gems', []),
                self._get_floor_tiles(generator),
                0.15
            )
            
            # Gold containers
            gold_containers = [o for o in self.by_material.get('gold', []) 
                             if o['type'] == 'containers']
            counts['gold_containers'] = self._place_objects(
                generator, gold_containers,
                self._get_floor_tiles(generator),
                0.08
            )
        
        elif theme == 'armory':
            counts['weapons'] = self._place_objects(
                generator,
                self.by_type.get('weapons', []),
                self._get_floor_tiles(generator),
                0.20
            )
        
        elif theme == 'library':
            counts['furniture'] = self._place_objects(
                generator,
                self.by_type.get('furniture', []),
                self._get_floor_tiles(generator),
                0.15
            )
            
            # Containers (for storing books/scrolls)
            counts['containers'] = self._place_objects(
                generator,
                self.by_type.get('containers', []),
                self._get_floor_tiles(generator),
                0.10
            )
        
        elif theme == 'kitchen':
            counts['food'] = self._place_objects(
                generator,
                self.by_type.get('food', []),
                self._get_floor_tiles(generator),
                0.12
            )
            
            counts['containers'] = self._place_objects(
                generator,
                self.by_type.get('containers', []),
                self._get_floor_tiles(generator),
                0.15
            )
            
            counts['tools'] = self._place_objects(
                generator,
                self.by_type.get('tools', []),
                self._get_floor_tiles(generator),
                0.08
            )
        
        elif theme == 'garden':
            counts['plants'] = self._place_objects(
                generator,
                self.by_type.get('plants', []),
                self._get_floor_tiles(generator),
                0.25
            )
            
            counts['trees'] = self._place_objects(
                generator,
                self.by_type.get('trees', []),
                self._get_floor_tiles(generator),
                0.10
            )
        
        elif theme == 'forge':
            # Metal objects
            metal_objects = self.by_material.get('metal', [])
            counts['metal_objects'] = self._place_objects(
                generator, metal_objects,
                self._get_floor_tiles(generator),
                0.15
            )
            
            counts['tools'] = self._place_objects(
                generator,
                self.by_type.get('tools', []),
                self._get_floor_tiles(generator),
                0.12
            )
        
        elif theme == 'alchemist':
            counts['containers'] = self._place_objects(
                generator,
                self.by_type.get('containers', []),
                self._get_floor_tiles(generator),
                0.18
            )
            
            counts['liquids'] = self._place_objects(
                generator,
                self.by_material.get('liquid', []),
                self._get_floor_tiles(generator),
                0.10
            )
            
            counts['gems'] = self._place_objects(
                generator,
                self.by_type.get('gems', []),
                self._get_floor_tiles(generator),
                0.08
            )
        
        return counts
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _place_objects(self, generator: BaseGenerator, 
                      objects: List[Dict],
                      tile_types: List[int],
                      density: float) -> int:
        """Place objects on specified tile types"""
        if not objects:
            return 0
        
        placed = 0
        
        for tile_type in tile_types:
            positions = generator.find_positions(tile_type)
            
            for x, y in positions:
                if random.random() < density:
                    obj = random.choice(objects)
                    if generator.place_object(x, y, obj):
                        placed += 1
        
        return placed
    
    def _get_floor_tiles(self, generator) -> List[int]:
        """Get appropriate floor tile types for a generator"""
        from dungeon_generator import DungeonGenerator
        from city_generator import CityGenerator
        
        if isinstance(generator, DungeonGenerator):
            return [DungeonGenerator.FLOOR, DungeonGenerator.ROOM_FLOOR]
        elif isinstance(generator, CityGenerator):
            return [CityGenerator.BUILDING, CityGenerator.MARKET, 
                   CityGenerator.PLAZA, CityGenerator.PARK]
        else:
            return [0]  # Generic floor tile


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    from dungeon_generator import DungeonGenerator
    from city_generator import CityGenerator
    
    print("=" * 70)
    print("INTELLIGENT OBJECT POPULATION")
    print("=" * 70)
    
    # Load populator
    populator = ObjectPopulator('game_objects_wordnet.json')
    
    # Example 1: Standard dungeon population
    print("\n" + "=" * 70)
    print("DUNGEON - MEDIUM DENSITY")
    print("=" * 70)
    
    dungeon = DungeonGenerator(60, 30, algorithm='bsp', seed=42)
    dungeon.generate()
    
    counts = populator.populate_dungeon(dungeon, density='medium')
    
    print("\nPlaced objects:")
    for obj_type, count in counts.items():
        print(f"  {obj_type:20s}: {count:4d}")
    
    # Example 2: Themed dungeon (treasure room)
    print("\n" + "=" * 70)
    print("DUNGEON - TREASURE THEME")
    print("=" * 70)
    
    treasure_dungeon = DungeonGenerator(40, 20, algorithm='rooms_corridors', seed=123)
    treasure_dungeon.generate()
    
    counts = populator.populate_themed(treasure_dungeon, 'treasure')
    
    print("\nPlaced objects:")
    for obj_type, count in counts.items():
        print(f"  {obj_type:20s}: {count:4d}")
    
    # Example 3: City population
    print("\n" + "=" * 70)
    print("CITY - MEDIUM DENSITY")
    print("=" * 70)
    
    city = CityGenerator(80, 40, city_type='medieval', seed=42)
    city.generate()
    
    counts = populator.populate_city(city, density='medium')
    
    print("\nPlaced objects:")
    total = 0
    for obj_type, count in sorted(counts.items()):
        print(f"  {obj_type:25s}: {count:4d}")
        total += count
    
    print(f"\n  {'TOTAL':25s}: {total:4d}")
    
    # Example 4: Themed city area (market focus)
    print("\n" + "=" * 70)
    print("CITY DISTRICT - GARDEN THEME")
    print("=" * 70)
    
    garden_city = CityGenerator(50, 25, city_type='grid', seed=456)
    garden_city.generate()
    
    counts = populator.populate_themed(garden_city, 'garden')
    
    print("\nPlaced objects:")
    for obj_type, count in counts.items():
        print(f"  {obj_type:20s}: {count:4d}")
    
    print("\n" + "=" * 70)
    print("DONE! Your world is now filled with thousands of objects!")
    print("=" * 70)
