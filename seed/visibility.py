"""
Visibility System - Line of Sight and Field of View calculations

Provides:
- Line-of-sight checking between two points
- Field-of-view calculation from any point
- Symmetric shadowcasting for accurate FOV
"""

import numpy as np
from typing import Set, Tuple, Callable, Optional


class Visibility:
    """
    Handles visibility calculations for a 2D grid.
    
    Uses Bresenham's line algorithm for LOS checks and
    recursive shadowcasting for FOV calculation.
    """
    
    def __init__(self, grid: np.ndarray, blocking_tiles: Set[int] = None):
        """
        Initialize visibility system.
        
        Args:
            grid: 2D numpy array representing the map
            blocking_tiles: Set of tile values that block sight (walls, etc.)
        """
        self.grid = grid
        self.height, self.width = grid.shape
        
        # Default: tile value 0 blocks sight (typically walls)
        self.blocking_tiles = blocking_tiles if blocking_tiles is not None else {0}
    
    def is_blocking(self, x: int, y: int) -> bool:
        """Check if a tile blocks visibility"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True  # Out of bounds blocks sight
        return self.grid[y, x] in self.blocking_tiles
    
    def is_transparent(self, x: int, y: int) -> bool:
        """Check if a tile allows sight through"""
        return not self.is_blocking(x, y)
    
    # =========================================================================
    # LINE OF SIGHT
    # =========================================================================
    
    def has_line_of_sight(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """
        Check if there's a clear line of sight between two points.
        Uses Bresenham's line algorithm.
        
        Args:
            x1, y1: Starting point
            x2, y2: Ending point
            
        Returns:
            True if line of sight exists, False if blocked
        """
        # Same point is always visible
        if x1 == x2 and y1 == y2:
            return True
        
        # Get all points on the line
        points = self._bresenham_line(x1, y1, x2, y2)
        
        # Check each point except start and end
        for x, y in points[1:-1]:
            if self.is_blocking(x, y):
                return False
        
        return True
    
    def _bresenham_line(self, x1: int, y1: int, x2: int, y2: int) -> list:
        """
        Generate points on a line using Bresenham's algorithm.
        
        Returns:
            List of (x, y) tuples from start to end
        """
        points = []
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            points.append((x, y))
            
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            
            if e2 > -dy:
                err -= dy
                x += sx
            
            if e2 < dx:
                err += dx
                y += sy
        
        return points
    
    def get_line(self, x1: int, y1: int, x2: int, y2: int) -> list:
        """Get all points on a line between two points"""
        return self._bresenham_line(x1, y1, x2, y2)
    
    # =========================================================================
    # FIELD OF VIEW - Recursive Shadowcasting
    # =========================================================================
    
    def compute_fov(self, origin_x: int, origin_y: int, radius: int = 10) -> Set[Tuple[int, int]]:
        """
        Compute field of view from a point using recursive shadowcasting.
        
        Args:
            origin_x, origin_y: The viewer's position
            radius: Maximum sight radius
            
        Returns:
            Set of (x, y) tuples that are visible from origin
        """
        visible = set()
        visible.add((origin_x, origin_y))
        
        # Cast light in all 8 octants
        for octant in range(8):
            self._cast_light(
                visible, origin_x, origin_y, radius,
                1, 1.0, 0.0, octant
            )
        
        return visible
    
    def _cast_light(self, visible: set, ox: int, oy: int, radius: int,
                    row: int, start_slope: float, end_slope: float, octant: int):
        """
        Recursive shadowcasting for one octant.
        
        This uses the standard recursive shadowcasting algorithm which provides
        symmetric, accurate field of view calculation.
        """
        if start_slope < end_slope:
            return
        
        # Multipliers for transforming coordinates based on octant
        # Format: (xx, xy, yx, yy)
        OCTANT_TRANSFORMS = [
            (1, 0, 0, 1),    # Octant 0: E-NE
            (0, 1, 1, 0),    # Octant 1: NE-N
            (0, -1, 1, 0),   # Octant 2: N-NW
            (-1, 0, 0, 1),   # Octant 3: NW-W
            (-1, 0, 0, -1),  # Octant 4: W-SW
            (0, -1, -1, 0),  # Octant 5: SW-S
            (0, 1, -1, 0),   # Octant 6: S-SE
            (1, 0, 0, -1),   # Octant 7: SE-E
        ]
        
        xx, xy, yx, yy = OCTANT_TRANSFORMS[octant]
        
        for distance in range(row, radius + 1):
            dx = -distance - 1
            dy = -distance
            blocked = False
            new_start_slope = start_slope
            
            while dx <= 0:
                dx += 1
                
                # Transform coordinates based on octant
                map_x = ox + dx * xx + dy * xy
                map_y = oy + dx * yx + dy * yy
                
                # Calculate slopes
                left_slope = (dx - 0.5) / (dy + 0.5)
                right_slope = (dx + 0.5) / (dy - 0.5)
                
                if start_slope < right_slope:
                    continue
                elif end_slope > left_slope:
                    break
                
                # Check if within radius (circular FOV)
                if dx * dx + dy * dy <= radius * radius:
                    visible.add((map_x, map_y))
                
                # Handle blocking
                if blocked:
                    if self.is_blocking(map_x, map_y):
                        new_start_slope = right_slope
                    else:
                        blocked = False
                        start_slope = new_start_slope
                else:
                    if self.is_blocking(map_x, map_y) and distance < radius:
                        blocked = True
                        self._cast_light(
                            visible, ox, oy, radius,
                            distance + 1, start_slope, left_slope, octant
                        )
                        new_start_slope = right_slope
            
            if blocked:
                break
    
    def get_visible_tiles(self, origin_x: int, origin_y: int, radius: int = 10) -> np.ndarray:
        """
        Get a boolean mask of visible tiles from a point.
        
        Args:
            origin_x, origin_y: The viewer's position
            radius: Maximum sight radius
            
        Returns:
            2D numpy boolean array where True = visible
        """
        visible_set = self.compute_fov(origin_x, origin_y, radius)
        
        mask = np.zeros((self.height, self.width), dtype=bool)
        for x, y in visible_set:
            if 0 <= x < self.width and 0 <= y < self.height:
                mask[y, x] = True
        
        return mask
    
    def get_visible_in_radius(self, origin_x: int, origin_y: int, radius: int = 10) -> dict:
        """
        Get visibility information around a point.
        
        Returns:
            Dictionary with:
            - visible_tiles: set of (x, y) that are visible
            - visible_count: number of visible tiles
            - blocked_by: list of (x, y) blocking tiles at edge of vision
        """
        visible = self.compute_fov(origin_x, origin_y, radius)
        
        # Find blocking tiles at the edge of vision
        blocked_by = []
        for x, y in visible:
            if self.is_blocking(x, y):
                blocked_by.append((x, y))
        
        return {
            'visible_tiles': visible,
            'visible_count': len(visible),
            'blocked_by': blocked_by,
            'origin': (origin_x, origin_y),
            'radius': radius
        }
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Euclidean distance between two points"""
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def can_see_entity(self, viewer_x: int, viewer_y: int, 
                       target_x: int, target_y: int, 
                       max_range: float = None) -> bool:
        """
        Check if viewer can see target entity.
        
        Args:
            viewer_x, viewer_y: Viewer position
            target_x, target_y: Target position
            max_range: Optional maximum sight range
            
        Returns:
            True if target is visible to viewer
        """
        # Check range first if specified
        if max_range is not None:
            dist = self.distance(viewer_x, viewer_y, target_x, target_y)
            if dist > max_range:
                return False
        
        # Check line of sight
        return self.has_line_of_sight(viewer_x, viewer_y, target_x, target_y)
    
    def render_fov(self, origin_x: int, origin_y: int, radius: int = 10,
                   visible_char: str = '.', hidden_char: str = '#',
                   origin_char: str = '@') -> str:
        """
        Render FOV as ASCII for debugging.
        
        Returns:
            String representation of the FOV
        """
        visible = self.compute_fov(origin_x, origin_y, radius)
        
        lines = []
        min_x = max(0, origin_x - radius)
        max_x = min(self.width, origin_x + radius + 1)
        min_y = max(0, origin_y - radius)
        max_y = min(self.height, origin_y + radius + 1)
        
        for y in range(min_y, max_y):
            line = ""
            for x in range(min_x, max_x):
                if x == origin_x and y == origin_y:
                    line += origin_char
                elif (x, y) in visible:
                    if self.is_blocking(x, y):
                        line += '#'
                    else:
                        line += visible_char
                else:
                    line += ' '
            lines.append(line)
        
        return '\n'.join(lines)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    print("=== Visibility System Test ===\n")
    
    # Create a test grid (0 = wall, 1 = floor)
    grid = np.array([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    
    vis = Visibility(grid, blocking_tiles={0})
    
    # Test from center of left room
    origin = (3, 4)
    print(f"FOV from {origin} with radius 8:")
    print(vis.render_fov(origin[0], origin[1], radius=8))
    
    print("\n" + "=" * 40)
    
    # Test line of sight
    tests = [
        ((3, 4), (3, 2), "Same room"),
        ((3, 4), (10, 4), "Through door"),
        ((3, 4), (10, 2), "Blocked by wall"),
    ]
    
    print("\nLine of Sight tests:")
    for (x1, y1), (x2, y2), desc in tests:
        los = vis.has_line_of_sight(x1, y1, x2, y2)
        print(f"  {desc}: ({x1},{y1}) -> ({x2},{y2}) = {los}")
    
    # Test visible tiles info
    print("\n" + "=" * 40)
    info = vis.get_visible_in_radius(3, 4, radius=6)
    print(f"\nVisible tiles from (3,4) radius 6: {info['visible_count']} tiles")
    print(f"Blocked by {len(info['blocked_by'])} wall tiles")
