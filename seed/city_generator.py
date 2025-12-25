"""
City Generator
Procedural city generation with districts, roads, and buildings
Inherits from BaseGenerator
"""

import numpy as np
import random
from typing import Dict, List, Tuple, Optional, Set
from base_generator import BaseGenerator


class CityGenerator(BaseGenerator):
    """
    Generates cities with districts, roads, and buildings
    
    Tile values:
        0 = Empty/Grass
        1 = Road
        2 = Building
        3 = Wall
        4 = Door
        5 = Plaza/Square
        6 = Park
        7 = Water (fountain, canal)
        8 = Market
        9 = Gate (city entrance)
    """
    
    # Tile type constants
    EMPTY = 0
    ROAD = 1
    BUILDING = 2
    WALL = 3
    DOOR = 4
    PLAZA = 5
    PARK = 6
    WATER = 7
    MARKET = 8
    GATE = 9
    
    def __init__(self, width: int, height: int, seed: Optional[int] = None,
                 city_type: str = 'medieval'):
        """
        Args:
            width, height: City dimensions
            seed: Random seed
            city_type: 'medieval', 'grid', 'organic', 'walled'
        """
        super().__init__(width, height, seed)
        
        self.city_type = city_type
        self.districts = []  # List of district regions
        self.buildings = []  # List of building rectangles (x, y, w, h, type)
        self.roads = []  # List of road segments
        self.plazas = []  # List of plaza positions
        
        # City parameters
        self.params = {
            'medieval': {
                'has_walls': True,
                'wall_thickness': 2,
                'num_gates': 4,
                'road_width': 2,
                'min_building_size': 3,
                'max_building_size': 8,
                'plaza_density': 0.02,
                'park_density': 0.05
            },
            'grid': {
                'has_walls': False,
                'block_size': 15,
                'road_width': 3,
                'min_building_size': 4,
                'max_building_size': 10,
                'plaza_density': 0.03,
                'park_density': 0.08
            },
            'organic': {
                'has_walls': False,
                'num_main_roads': 5,
                'road_width': 2,
                'min_building_size': 3,
                'max_building_size': 7,
                'plaza_density': 0.04,
                'park_density': 0.06
            },
            'walled': {
                'has_walls': True,
                'wall_thickness': 3,
                'num_gates': 6,
                'num_districts': 4,
                'road_width': 2,
                'min_building_size': 4,
                'max_building_size': 9,
                'plaza_density': 0.03,
                'park_density': 0.04
            }
        }
    
    def generate(self):
        """Generate city using selected type"""
        # Start with empty ground
        self.grid.fill(self.EMPTY)
        
        # Run generation algorithm
        if self.city_type == 'medieval':
            self._generate_medieval()
        elif self.city_type == 'grid':
            self._generate_grid()
        elif self.city_type == 'organic':
            self._generate_organic()
        elif self.city_type == 'walled':
            self._generate_walled()
        else:
            raise ValueError(f"Unknown city type: {self.city_type}")
        
        self.generated = True
        return self
    
    # ========================================================================
    # MEDIEVAL CITY (Radial roads from center, city walls)
    # ========================================================================
    
    def _generate_medieval(self):
        """Generate medieval-style city"""
        params = self.params['medieval']
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        # Add outer walls
        if params['has_walls']:
            self._add_city_walls(params)
        
        # Add central plaza
        plaza_size = 6
        self._add_plaza(center_x - plaza_size//2, center_y - plaza_size//2, 
                       plaza_size, plaza_size)
        
        # Add radial roads from center
        num_roads = 8
        for i in range(num_roads):
            angle = (2 * np.pi * i) / num_roads
            self._add_radial_road(center_x, center_y, angle, params)
        
        # Add concentric ring roads
        for radius in [15, 30, 45]:
            if radius < min(self.width, self.height) // 2:
                self._add_ring_road(center_x, center_y, radius, params)
        
        # Fill with buildings
        self._fill_with_buildings(params)
        
        # Add parks
        self._add_parks(params)
    
    def _add_city_walls(self, params: Dict):
        """Add walls around the city perimeter"""
        thickness = params['wall_thickness']
        
        # Top and bottom walls
        for t in range(thickness):
            self.grid[t, :] = self.WALL
            self.grid[-(t+1), :] = self.WALL
        
        # Left and right walls
        for t in range(thickness):
            self.grid[:, t] = self.WALL
            self.grid[:, -(t+1)] = self.WALL
        
        # Add gates
        num_gates = params.get('num_gates', 4)
        gate_positions = [
            (self.width // 2, thickness),  # North
            (self.width // 2, self.height - thickness - 1),  # South
            (thickness, self.height // 2),  # West
            (self.width - thickness - 1, self.height // 2),  # East
        ]
        
        for i, (gx, gy) in enumerate(gate_positions[:num_gates]):
            self.grid[gy, gx] = self.GATE
            self.set_metadata(gx, gy, 'gate_id', i)
    
    def _add_radial_road(self, cx: int, cy: int, angle: float, params: Dict):
        """Add a road radiating from center"""
        width = params['road_width']
        max_dist = min(self.width, self.height) // 2
        
        for dist in range(0, max_dist):
            x = int(cx + dist * np.cos(angle))
            y = int(cy + dist * np.sin(angle))
            
            if not self.is_valid_position(x, y):
                break
            
            # Don't overwrite walls
            if self.grid[y, x] == self.WALL:
                break
            
            # Draw road with width
            for dx in range(-width//2, width//2 + 1):
                for dy in range(-width//2, width//2 + 1):
                    rx, ry = x + dx, y + dy
                    if self.is_valid_position(rx, ry) and self.grid[ry, rx] not in [self.WALL, self.PLAZA]:
                        self.grid[ry, rx] = self.ROAD
    
    def _add_ring_road(self, cx: int, cy: int, radius: int, params: Dict):
        """Add a circular road around center"""
        width = params['road_width']
        
        # Sample points on circle
        num_points = int(2 * np.pi * radius)
        for i in range(num_points):
            angle = (2 * np.pi * i) / num_points
            x = int(cx + radius * np.cos(angle))
            y = int(cy + radius * np.sin(angle))
            
            if not self.is_valid_position(x, y):
                continue
            
            # Draw road
            for dx in range(-width//2, width//2 + 1):
                for dy in range(-width//2, width//2 + 1):
                    rx, ry = x + dx, y + dy
                    if self.is_valid_position(rx, ry) and self.grid[ry, rx] not in [self.WALL, self.PLAZA]:
                        self.grid[ry, rx] = self.ROAD
    
    # ========================================================================
    # GRID CITY (Manhattan-style grid)
    # ========================================================================
    
    def _generate_grid(self):
        """Generate grid-based city"""
        params = self.params['grid']
        
        block_size = params['block_size']
        road_width = params['road_width']
        
        # Add horizontal roads
        y = 0
        while y < self.height:
            for ry in range(road_width):
                if y + ry < self.height:
                    self.grid[y + ry, :] = self.ROAD
            y += block_size + road_width
        
        # Add vertical roads
        x = 0
        while x < self.width:
            for rx in range(road_width):
                if x + rx < self.width:
                    self.grid[:, x + rx] = self.ROAD
            x += block_size + road_width
        
        # Fill blocks with buildings
        y = road_width
        while y < self.height:
            x = road_width
            while x < self.width:
                # Define block bounds
                bx = x
                by = y
                bw = min(block_size, self.width - x)
                bh = min(block_size, self.height - y)
                
                # Decide block type
                rand = random.random()
                if rand < params['park_density']:
                    self._add_park_block(bx, by, bw, bh)
                elif rand < params['park_density'] + params['plaza_density']:
                    self._add_plaza(bx, by, bw, bh)
                else:
                    self._fill_block_with_buildings(bx, by, bw, bh, params)
                
                x += block_size + road_width
            y += block_size + road_width
    
    def _fill_block_with_buildings(self, bx: int, by: int, bw: int, bh: int, params: Dict):
        """Fill a city block with buildings"""
        # Try to place multiple buildings in block
        attempts = 20
        
        for _ in range(attempts):
            # Random building size (ensure min <= max)
            max_w = min(params['max_building_size'], bw - 2)
            max_h = min(params['max_building_size'], bh - 2)
            
            if max_w < params['min_building_size'] or max_h < params['min_building_size']:
                continue  # Block too small
            
            w = random.randint(params['min_building_size'], max_w)
            h = random.randint(params['min_building_size'], max_h)
            
            # Random position within block
            x = random.randint(bx, bx + bw - w - 1)
            y = random.randint(by, by + bh - h - 1)
            
            # Check if area is empty
            can_place = True
            for dy in range(-1, h + 1):
                for dx in range(-1, w + 1):
                    cx, cy = x + dx, y + dy
                    if self.is_valid_position(cx, cy):
                        if self.grid[cy, cx] != self.EMPTY:
                            can_place = False
                            break
                if not can_place:
                    break
            
            if can_place:
                self._add_building(x, y, w, h)
    
    # ========================================================================
    # ORGANIC CITY (Irregular roads, natural growth)
    # ========================================================================
    
    def _generate_organic(self):
        """Generate organic-style city with irregular layout"""
        params = self.params['organic']
        
        # Add main roads from random points
        num_main_roads = params['num_main_roads']
        
        for _ in range(num_main_roads):
            # Random start point
            sx = random.randint(0, self.width - 1)
            sy = random.randint(0, self.height - 1)
            
            # Random end point
            ex = random.randint(0, self.width - 1)
            ey = random.randint(0, self.height - 1)
            
            # Draw winding road
            self._add_winding_road(sx, sy, ex, ey, params)
        
        # Add some secondary roads
        for _ in range(num_main_roads * 2):
            # Find random road tile
            roads = self.find_positions(self.ROAD)
            if roads:
                sx, sy = random.choice(roads)
                
                # Random direction
                angle = random.random() * 2 * np.pi
                length = random.randint(10, 30)
                
                ex = int(sx + length * np.cos(angle))
                ey = int(sy + length * np.sin(angle))
                
                self._add_winding_road(sx, sy, ex, ey, params)
        
        # Add central plaza
        cx, cy = self.width // 2, self.height // 2
        self._add_plaza(cx - 4, cy - 4, 8, 8)
        
        # Fill with buildings
        self._fill_with_buildings(params)
        
        # Add parks
        self._add_parks(params)
    
    def _add_winding_road(self, sx: int, sy: int, ex: int, ey: int, params: Dict):
        """Add a winding road between two points"""
        width = params['road_width']
        
        # Use simple line with some randomness
        steps = int(np.sqrt((ex - sx)**2 + (ey - sy)**2))
        
        for i in range(steps):
            t = i / max(steps, 1)
            
            # Linear interpolation with random offset
            x = int(sx + (ex - sx) * t + random.randint(-2, 2))
            y = int(sy + (ey - sy) * t + random.randint(-2, 2))
            
            # Draw road
            for dx in range(-width//2, width//2 + 1):
                for dy in range(-width//2, width//2 + 1):
                    rx, ry = x + dx, y + dy
                    if self.is_valid_position(rx, ry) and self.grid[ry, rx] == self.EMPTY:
                        self.grid[ry, rx] = self.ROAD
    
    # ========================================================================
    # WALLED CITY (Districts separated by walls)
    # ========================================================================
    
    def _generate_walled(self):
        """Generate walled city with distinct districts"""
        params = self.params['walled']
        
        # Outer walls
        self._add_city_walls(params)
        
        # Divide into districts
        num_districts = params.get('num_districts', 4)
        
        # Create districts using quadrants
        mid_x = self.width // 2
        mid_y = self.height // 2
        wall_t = params['wall_thickness']
        
        districts = [
            (wall_t, wall_t, mid_x - wall_t, mid_y - wall_t),  # NW
            (mid_x, wall_t, self.width - mid_x - wall_t, mid_y - wall_t),  # NE
            (wall_t, mid_y, mid_x - wall_t, self.height - mid_y - wall_t),  # SW
            (mid_x, mid_y, self.width - mid_x - wall_t, self.height - mid_y - wall_t),  # SE
        ]
        
        # Add main cross roads
        for x in range(self.width):
            for dy in range(-1, 2):
                y = mid_y + dy
                if self.is_valid_position(x, y):
                    self.grid[y, x] = self.ROAD
        
        for y in range(self.height):
            for dx in range(-1, 2):
                x = mid_x + dx
                if self.is_valid_position(x, y):
                    self.grid[y, x] = self.ROAD
        
        # Fill each district
        for i, (dx, dy, dw, dh) in enumerate(districts[:num_districts]):
            # Add district walls (optional)
            if random.random() < 0.3:
                self._add_district_walls(dx, dy, dw, dh)
            
            # District type
            district_types = ['residential', 'market', 'noble', 'craftsman']
            dtype = district_types[i % len(district_types)]
            
            self._fill_district(dx, dy, dw, dh, dtype, params)
    
    def _add_district_walls(self, x: int, y: int, w: int, h: int):
        """Add walls around a district"""
        for wx in range(x, x + w):
            if self.is_valid_position(wx, y):
                self.grid[y, wx] = self.WALL
            if self.is_valid_position(wx, y + h - 1):
                self.grid[y + h - 1, wx] = self.WALL
        
        for wy in range(y, y + h):
            if self.is_valid_position(x, wy):
                self.grid[wy, x] = self.WALL
            if self.is_valid_position(x + w - 1, wy):
                self.grid[wy, x + w - 1] = self.WALL
    
    def _fill_district(self, dx: int, dy: int, dw: int, dh: int, 
                      dtype: str, params: Dict):
        """Fill a district based on its type"""
        if dtype == 'market':
            # Large central market
            mx = dx + dw // 2 - 6
            my = dy + dh // 2 - 6
            for y in range(my, my + 12):
                for x in range(mx, mx + 12):
                    if self.is_valid_position(x, y):
                        self.grid[y, x] = self.MARKET
        elif dtype == 'noble':
            # Fewer, larger buildings
            params_copy = params.copy()
            params_copy['min_building_size'] = 6
            params_copy['max_building_size'] = 12
            self._fill_region_with_buildings(dx, dy, dw, dh, params_copy)
        else:
            # Standard buildings
            self._fill_region_with_buildings(dx, dy, dw, dh, params)
    
    # ========================================================================
    # BUILDING PLACEMENT
    # ========================================================================
    
    def _fill_with_buildings(self, params: Dict):
        """Fill empty spaces with buildings"""
        self._fill_region_with_buildings(0, 0, self.width, self.height, params)
    
    def _fill_region_with_buildings(self, rx: int, ry: int, rw: int, rh: int, params: Dict):
        """Fill a region with buildings"""
        attempts = (rw * rh) // 10  # Scale attempts with area
        
        for _ in range(attempts):
            # Random building size
            w = random.randint(params['min_building_size'], params['max_building_size'])
            h = random.randint(params['min_building_size'], params['max_building_size'])
            
            # Random position in region
            x = random.randint(rx, rx + rw - w - 1)
            y = random.randint(ry, ry + rh - h - 1)
            
            # Check if we can place it
            can_place = True
            for dy in range(-1, h + 1):
                for dx in range(-1, w + 1):
                    cx, cy = x + dx, y + dy
                    if self.is_valid_position(cx, cy):
                        tile = self.grid[cy, cx]
                        if tile != self.EMPTY:
                            can_place = False
                            break
                if not can_place:
                    break
            
            if can_place:
                self._add_building(x, y, w, h)
    
    def _add_building(self, x: int, y: int, w: int, h: int):
        """Add a single building"""
        # Fill interior
        for by in range(y + 1, y + h - 1):
            for bx in range(x + 1, x + w - 1):
                self.grid[by, bx] = self.BUILDING
        
        # Add walls
        for bx in range(x, x + w):
            self.grid[y, bx] = self.WALL
            self.grid[y + h - 1, bx] = self.WALL
        
        for by in range(y, y + h):
            self.grid[by, x] = self.WALL
            self.grid[by, x + w - 1] = self.WALL
        
        # Add door (random side)
        side = random.randint(0, 3)
        if side == 0:  # Top
            door_x = x + w // 2
            self.grid[y, door_x] = self.DOOR
        elif side == 1:  # Right
            door_y = y + h // 2
            self.grid[door_y, x + w - 1] = self.DOOR
        elif side == 2:  # Bottom
            door_x = x + w // 2
            self.grid[y + h - 1, door_x] = self.DOOR
        else:  # Left
            door_y = y + h // 2
            self.grid[door_y, x] = self.DOOR
        
        self.buildings.append((x, y, w, h, 'building'))
    
    def _add_plaza(self, x: int, y: int, w: int, h: int):
        """Add a plaza/square"""
        for py in range(y, min(y + h, self.height)):
            for px in range(x, min(x + w, self.width)):
                if self.is_valid_position(px, py):
                    self.grid[py, px] = self.PLAZA
        
        self.plazas.append((x, y, w, h))
    
    def _add_parks(self, params: Dict):
        """Add parks to empty areas"""
        park_density = params.get('park_density', 0.05)
        
        # Find large empty areas
        for _ in range(20):
            x = random.randint(5, self.width - 15)
            y = random.randint(5, self.height - 15)
            w = random.randint(8, 12)
            h = random.randint(8, 12)
            
            if random.random() < park_density:
                # Check if area is mostly empty
                empty_count = 0
                total = w * h
                
                for py in range(y, y + h):
                    for px in range(x, x + w):
                        if self.is_valid_position(px, py) and self.grid[py, px] == self.EMPTY:
                            empty_count += 1
                
                if empty_count > total * 0.8:
                    self._add_park_block(x, y, w, h)
    
    def _add_park_block(self, x: int, y: int, w: int, h: int):
        """Add a park block"""
        for py in range(y, min(y + h, self.height)):
            for px in range(x, min(x + w, self.width)):
                if self.is_valid_position(px, py):
                    self.grid[py, px] = self.PARK
    
    # ========================================================================
    # RENDERING
    # ========================================================================
    
    def render_ascii(self, tile_chars: Dict[int, str] = None, show_objects: bool = False) -> str:
        """Render city as ASCII"""
        if tile_chars is None:
            tile_chars = {
                self.EMPTY: '.',
                self.ROAD: '=',
                self.BUILDING: '▓',
                self.WALL: '#',
                self.DOOR: '+',
                self.PLAZA: '□',
                self.PARK: '♣',
                self.WATER: '~',
                self.MARKET: 'M',
                self.GATE: 'Π'
            }
        
        return super().render_ascii(tile_chars, show_objects)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CITY GENERATOR TEST")
    print("=" * 70)
    
    city_types = ['medieval', 'grid', 'organic', 'walled']
    
    for ctype in city_types:
        print(f"\n{'=' * 70}")
        print(f"{ctype.upper()} CITY")
        print(f"{'=' * 70}\n")
        
        city = CityGenerator(80, 40, city_type=ctype, seed=42)
        city.generate()
        
        city.print_ascii()
        
        stats = city.get_statistics()
        print(f"\nBuildings: {len(city.buildings)}")
        print(f"Plazas: {len(city.plazas)}")
        print(f"Tile counts: {stats['tile_counts']}")
    
    print("\n" + "=" * 70)
    print("DONE!")
    print("=" * 70)
