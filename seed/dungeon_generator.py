"""
Dungeon Generator
Procedural dungeon generation with multiple algorithms
Inherits from BaseGenerator
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from base_generator import BaseGenerator


class DungeonGenerator(BaseGenerator):
    """
    Generates dungeons using various algorithms
    
    Tile values:
        0 = Floor
        1 = Wall
        2 = Door
        3 = Corridor
        4 = Room (special floor)
        5 = Entrance
        6 = Exit/Stairs
    """
    
    # Tile type constants
    FLOOR = 0
    WALL = 1
    DOOR = 2
    CORRIDOR = 3
    ROOM_FLOOR = 4
    ENTRANCE = 5
    EXIT = 6
    
    def __init__(self, width: int, height: int, seed: Optional[int] = None,
                 algorithm: str = 'bsp'):
        """
        Args:
            width, height: Dungeon dimensions
            seed: Random seed
            algorithm: 'bsp', 'cellular', 'drunkard', 'rooms_corridors'
        """
        super().__init__(width, height, seed)
        
        self.algorithm = algorithm
        self.rooms = []  # List of room rectangles (x, y, w, h)
        self.corridors = []  # List of corridor paths
        
        # Algorithm parameters
        self.params = {
            'bsp': {
                'min_room_size': 5,
                'max_room_size': 15,
                'min_split_size': 10
            },
            'cellular': {
                'wall_probability': 0.45,
                'birth_limit': 4,
                'death_limit': 3,
                'iterations': 5
            },
            'drunkard': {
                'target_floor_pct': 0.4,
                'drunk_lifetime': 500,
                'turn_probability': 0.3
            },
            'rooms_corridors': {
                'num_rooms': 10,
                'min_room_size': 4,
                'max_room_size': 10,
                'max_attempts': 100
            }
        }
    
    def generate(self):
        """Generate dungeon using selected algorithm"""
        # Start with all walls
        self.grid.fill(self.WALL)
        
        # Run algorithm
        if self.algorithm == 'bsp':
            self._generate_bsp()
        elif self.algorithm == 'cellular':
            self._generate_cellular()
        elif self.algorithm == 'drunkard':
            self._generate_drunkard()
        elif self.algorithm == 'rooms_corridors':
            self._generate_rooms_corridors()
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        # Add entrance and exit
        self._add_entrance_exit()
        
        self.generated = True
        return self
    
    # ========================================================================
    # BSP (Binary Space Partitioning) Algorithm
    # ========================================================================
    
    def _generate_bsp(self):
        """Generate dungeon using BSP tree"""
        params = self.params['bsp']
        
        # Create root container (entire dungeon)
        root = {
            'x': 1,
            'y': 1,
            'w': self.width - 2,
            'h': self.height - 2,
            'children': []
        }
        
        # Recursively split
        self._bsp_split(root, params)
        
        # Create rooms in leaf nodes
        self._bsp_create_rooms(root, params)
        
        # Connect rooms
        self._bsp_connect_rooms(root)
    
    def _bsp_split(self, container: Dict, params: Dict, depth: int = 0):
        """Recursively split container"""
        if depth > 5:  # Max depth
            return
        
        # Check if container is large enough to split
        can_split_h = container['w'] >= params['min_split_size'] * 2
        can_split_v = container['h'] >= params['min_split_size'] * 2
        
        if not (can_split_h or can_split_v):
            return
        
        # Choose split direction
        if can_split_h and can_split_v:
            split_horizontal = random.choice([True, False])
        elif can_split_h:
            split_horizontal = True
        else:
            split_horizontal = False
        
        if split_horizontal:
            # Split into left and right
            split_pos = random.randint(params['min_split_size'], 
                                      container['w'] - params['min_split_size'])
            
            child1 = {
                'x': container['x'],
                'y': container['y'],
                'w': split_pos,
                'h': container['h'],
                'children': []
            }
            
            child2 = {
                'x': container['x'] + split_pos,
                'y': container['y'],
                'w': container['w'] - split_pos,
                'h': container['h'],
                'children': []
            }
        else:
            # Split into top and bottom
            split_pos = random.randint(params['min_split_size'],
                                      container['h'] - params['min_split_size'])
            
            child1 = {
                'x': container['x'],
                'y': container['y'],
                'w': container['w'],
                'h': split_pos,
                'children': []
            }
            
            child2 = {
                'x': container['x'],
                'y': container['y'] + split_pos,
                'w': container['w'],
                'h': container['h'] - split_pos,
                'children': []
            }
        
        container['children'] = [child1, child2]
        
        # Recurse
        self._bsp_split(child1, params, depth + 1)
        self._bsp_split(child2, params, depth + 1)
    
    def _bsp_create_rooms(self, container: Dict, params: Dict):
        """Create rooms in leaf nodes"""
        if not container['children']:
            # Leaf node - create room
            room_w = random.randint(params['min_room_size'], 
                                   min(params['max_room_size'], container['w'] - 2))
            room_h = random.randint(params['min_room_size'],
                                   min(params['max_room_size'], container['h'] - 2))
            
            # Random position within container
            room_x = container['x'] + random.randint(1, container['w'] - room_w - 1)
            room_y = container['y'] + random.randint(1, container['h'] - room_h - 1)
            
            # Carve room
            for y in range(room_y, room_y + room_h):
                for x in range(room_x, room_x + room_w):
                    self.grid[y, x] = self.ROOM_FLOOR
            
            # Store room
            room = (room_x, room_y, room_w, room_h)
            self.rooms.append(room)
            container['room'] = room
        else:
            # Recurse into children
            for child in container['children']:
                self._bsp_create_rooms(child, params)
    
    def _bsp_connect_rooms(self, container: Dict):
        """Connect rooms with corridors"""
        if not container['children']:
            return
        
        # Get rooms from children
        child1, child2 = container['children']
        self._bsp_connect_rooms(child1)
        self._bsp_connect_rooms(child2)
        
        # Get room centers
        room1 = self._bsp_get_room(child1)
        room2 = self._bsp_get_room(child2)
        
        if room1 and room2:
            x1, y1, w1, h1 = room1
            x2, y2, w2, h2 = room2
            
            center1 = (x1 + w1 // 2, y1 + h1 // 2)
            center2 = (x2 + w2 // 2, y2 + h2 // 2)
            
            # Create L-shaped corridor
            self._create_corridor(center1[0], center1[1], center2[0], center2[1])
    
    def _bsp_get_room(self, container: Dict):
        """Get a room from container or its descendants"""
        if 'room' in container:
            return container['room']
        
        if container['children']:
            for child in container['children']:
                room = self._bsp_get_room(child)
                if room:
                    return room
        
        return None
    
    # ========================================================================
    # Cellular Automata Algorithm
    # ========================================================================
    
    def _generate_cellular(self):
        """Generate cave-like dungeon using cellular automata"""
        params = self.params['cellular']
        
        # Initialize with random walls/floors
        for y in range(self.height):
            for x in range(self.width):
                if random.random() < params['wall_probability']:
                    self.grid[y, x] = self.WALL
                else:
                    self.grid[y, x] = self.FLOOR
        
        # Run cellular automata iterations
        for _ in range(params['iterations']):
            self._cellular_step(params)
        
        # Ensure borders are walls
        self.grid[0, :] = self.WALL
        self.grid[-1, :] = self.WALL
        self.grid[:, 0] = self.WALL
        self.grid[:, -1] = self.WALL
        
        # Find largest connected region and keep only that
        self._cellular_keep_largest_region()
    
    def _cellular_step(self, params: Dict):
        """One step of cellular automata"""
        new_grid = self.grid.copy()
        
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                wall_count = self.count_neighbors(x, y, self.WALL, diagonal=True)
                
                if self.grid[y, x] == self.WALL:
                    # Death rule
                    if wall_count < params['death_limit']:
                        new_grid[y, x] = self.FLOOR
                else:
                    # Birth rule
                    if wall_count > params['birth_limit']:
                        new_grid[y, x] = self.WALL
        
        self.grid = new_grid
    
    def _cellular_keep_largest_region(self):
        """Keep only the largest connected floor region"""
        # Find all floor positions
        floor_positions = self.find_positions(self.FLOOR)
        
        if not floor_positions:
            return
        
        # Find connected regions
        visited = set()
        regions = []
        
        for pos in floor_positions:
            if pos in visited:
                continue
            
            # Flood fill to find region
            region = []
            stack = [pos]
            
            while stack:
                x, y = stack.pop()
                if (x, y) in visited:
                    continue
                
                if self.grid[y, x] != self.FLOOR:
                    continue
                
                visited.add((x, y))
                region.append((x, y))
                
                for nx, ny in self.get_neighbors(x, y):
                    if (nx, ny) not in visited:
                        stack.append((nx, ny))
            
            regions.append(region)
        
        # Keep largest region
        if regions:
            largest = max(regions, key=len)
            largest_set = set(largest)
            
            # Fill all other regions with walls
            for y in range(self.height):
                for x in range(self.width):
                    if self.grid[y, x] == self.FLOOR and (x, y) not in largest_set:
                        self.grid[y, x] = self.WALL
    
    # ========================================================================
    # Drunkard's Walk Algorithm
    # ========================================================================
    
    def _generate_drunkard(self):
        """Generate dungeon using drunkard's walk"""
        params = self.params['drunkard']
        
        target_floors = int(self.width * self.height * params['target_floor_pct'])
        floor_count = 0
        
        # Start in center
        x = self.width // 2
        y = self.height // 2
        
        # Walk until target reached
        lifetime = 0
        while floor_count < target_floors and lifetime < params['drunk_lifetime'] * 10:
            # Carve floor
            if self.grid[y, x] == self.WALL:
                self.grid[y, x] = self.FLOOR
                floor_count += 1
            
            # Random direction
            if random.random() < params['turn_probability']:
                direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
            
            # Move
            dx, dy = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
            nx, ny = x + dx, y + dy
            
            # Stay in bounds
            if 1 <= nx < self.width - 1 and 1 <= ny < self.height - 1:
                x, y = nx, ny
            
            lifetime += 1
    
    # ========================================================================
    # Rooms and Corridors Algorithm
    # ========================================================================
    
    def _generate_rooms_corridors(self):
        """Generate dungeon with discrete rooms connected by corridors"""
        params = self.params['rooms_corridors']
        
        # Place rooms
        for _ in range(params['max_attempts']):
            if len(self.rooms) >= params['num_rooms']:
                break
            
            # Random room size
            w = random.randint(params['min_room_size'], params['max_room_size'])
            h = random.randint(params['min_room_size'], params['max_room_size'])
            
            # Random position
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)
            
            # Check overlap with existing rooms
            room = (x, y, w, h)
            if not self._rooms_overlap(room):
                self._carve_room(room)
                self.rooms.append(room)
        
        # Connect rooms
        for i in range(len(self.rooms) - 1):
            room1 = self.rooms[i]
            room2 = self.rooms[i + 1]
            
            x1, y1, w1, h1 = room1
            x2, y2, w2, h2 = room2
            
            center1 = (x1 + w1 // 2, y1 + h1 // 2)
            center2 = (x2 + w2 // 2, y2 + h2 // 2)
            
            self._create_corridor(center1[0], center1[1], center2[0], center2[1])
    
    def _rooms_overlap(self, new_room: Tuple[int, int, int, int]) -> bool:
        """Check if new room overlaps with existing rooms"""
        x1, y1, w1, h1 = new_room
        
        for room in self.rooms:
            x2, y2, w2, h2 = room
            
            # Check overlap (with 1 tile padding)
            if (x1 - 1 < x2 + w2 and x1 + w1 + 1 > x2 and
                y1 - 1 < y2 + h2 and y1 + h1 + 1 > y2):
                return True
        
        return False
    
    def _carve_room(self, room: Tuple[int, int, int, int]):
        """Carve out a room"""
        x, y, w, h = room
        
        for ry in range(y, y + h):
            for rx in range(x, x + w):
                self.grid[ry, rx] = self.ROOM_FLOOR
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _create_corridor(self, x1: int, y1: int, x2: int, y2: int):
        """Create L-shaped corridor between two points"""
        # Horizontal then vertical
        if random.choice([True, False]):
            # Horizontal first
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if self.grid[y1, x] == self.WALL:
                    self.grid[y1, x] = self.CORRIDOR
            
            # Vertical
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if self.grid[y, x2] == self.WALL:
                    self.grid[y, x2] = self.CORRIDOR
        else:
            # Vertical first
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if self.grid[y, x1] == self.WALL:
                    self.grid[y, x1] = self.CORRIDOR
            
            # Horizontal
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if self.grid[y2, x] == self.WALL:
                    self.grid[y2, x] = self.CORRIDOR
    
    def _add_entrance_exit(self):
        """Add entrance and exit to dungeon"""
        # Find floor tiles
        floors = self.find_positions(self.FLOOR) + self.find_positions(self.ROOM_FLOOR)
        
        if len(floors) < 2:
            return
        
        # Entrance at first floor
        x, y = floors[0]
        self.grid[y, x] = self.ENTRANCE
        
        # Exit at last floor
        x, y = floors[-1]
        self.grid[y, x] = self.EXIT
    
    def render_ascii(self, tile_chars: Dict[int, str] = None, show_objects: bool = False) -> str:
        """Render dungeon as ASCII"""
        if tile_chars is None:
            tile_chars = {
                self.FLOOR: '.',
                self.WALL: '#',
                self.DOOR: '+',
                self.CORRIDOR: ',',
                self.ROOM_FLOOR: '·',
                self.ENTRANCE: '<',
                self.EXIT: '>'
            }
        
        return super().render_ascii(tile_chars, show_objects)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DUNGEON GENERATOR TEST")
    print("=" * 70)
    
    algorithms = ['bsp', 'cellular', 'drunkard', 'rooms_corridors']
    
    for algo in algorithms:
        print(f"\n{'=' * 70}")
        print(f"{algo.upper()} ALGORITHM")
        print(f"{'=' * 70}\n")
        
        dungeon = DungeonGenerator(60, 30, algorithm=algo, seed=42)
        dungeon.generate()
        
        dungeon.print_ascii()
        
        stats = dungeon.get_statistics()
        print(f"\nStats: {stats['tile_counts']}")
        print(f"Rooms: {len(dungeon.rooms)}")
    
    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)
