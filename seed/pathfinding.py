"""
Pathfinding Algorithms
A*, Dijkstra, BFS, DFS, and Greedy Best-First Search
Works with any grid-based generator (dungeons, cities, terrain)
"""

import heapq
from typing import List, Tuple, Set, Dict, Optional, Callable
from dataclasses import dataclass, field
import numpy as np


@dataclass(order=True)
class Node:
    """Node for pathfinding with priority"""
    priority: float
    position: Tuple[int, int] = field(compare=False)
    g_cost: float = field(default=0, compare=False)
    h_cost: float = field(default=0, compare=False)
    parent: Optional[Tuple[int, int]] = field(default=None, compare=False)


class Pathfinder:
    """
    Unified pathfinding system
    Works with any BaseGenerator or numpy grid
    """
    
    def __init__(self, grid: np.ndarray, walkable_tiles: Set[int] = None):
        """
        Args:
            grid: 2D numpy array
            walkable_tiles: Set of tile values that are walkable
                           If None, assumes 0 = walkable, non-0 = wall
        """
        self.grid = grid
        self.height, self.width = grid.shape
        
        if walkable_tiles is None:
            # Default: treat specific values as walkable
            # This is a sensible default for most generators
            self.is_walkable = lambda tile: tile in {0, 1, 2, 3, 4, 5, 6}
        else:
            self.is_walkable = lambda tile: tile in walkable_tiles
    
    # ========================================================================
    # HEURISTICS
    # ========================================================================
    
    @staticmethod
    def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Manhattan distance (|dx| + |dy|)"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    
    @staticmethod
    def euclidean_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Euclidean distance (straight line)"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
    
    @staticmethod
    def chebyshev_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Chebyshev distance (max of |dx|, |dy|) - allows diagonal"""
        return max(abs(pos1[0] - pos2[0]), abs(pos1[1] - pos2[1]))
    
    # ========================================================================
    # NEIGHBOR GENERATION
    # ========================================================================
    
    def get_neighbors(self, pos: Tuple[int, int], allow_diagonal: bool = False) -> List[Tuple[int, int]]:
        """Get valid neighboring positions"""
        x, y = pos
        neighbors = []
        
        # Cardinal directions
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        
        # Diagonal directions
        if allow_diagonal:
            for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if self.is_valid_position(nx, ny):
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is valid and walkable"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.is_walkable(self.grid[y, x])
    
    def get_move_cost(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> float:
        """Get cost of moving from one position to another"""
        # Diagonal moves cost more
        if abs(from_pos[0] - to_pos[0]) + abs(from_pos[1] - to_pos[1]) == 2:
            return 1.414  # sqrt(2)
        return 1.0
    
    # ========================================================================
    # A* PATHFINDING (Best for most cases)
    # ========================================================================
    
    def astar(self, 
              start: Tuple[int, int], 
              goal: Tuple[int, int],
              allow_diagonal: bool = False,
              heuristic: Callable = None) -> Optional[List[Tuple[int, int]]]:
        """
        A* pathfinding - optimal and efficient
        
        Args:
            start: Starting position (x, y)
            goal: Goal position (x, y)
            allow_diagonal: Allow diagonal movement
            heuristic: Distance function (default: manhattan)
        
        Returns:
            List of positions from start to goal, or None if no path
        """
        if heuristic is None:
            heuristic = self.manhattan_distance
        
        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return None
        
        # Priority queue: (f_cost, position)
        open_set = []
        heapq.heappush(open_set, Node(
            priority=0,
            position=start,
            g_cost=0,
            h_cost=heuristic(start, goal)
        ))
        
        # Track best g_cost to each position
        g_costs = {start: 0}
        came_from = {}
        
        while open_set:
            current_node = heapq.heappop(open_set)
            current = current_node.position
            
            # Found goal!
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            # Check neighbors
            for neighbor in self.get_neighbors(current, allow_diagonal):
                move_cost = self.get_move_cost(current, neighbor)
                tentative_g = g_costs[current] + move_cost
                
                if neighbor not in g_costs or tentative_g < g_costs[neighbor]:
                    g_costs[neighbor] = tentative_g
                    h_cost = heuristic(neighbor, goal)
                    f_cost = tentative_g + h_cost
                    
                    came_from[neighbor] = current
                    heapq.heappush(open_set, Node(
                        priority=f_cost,
                        position=neighbor,
                        g_cost=tentative_g,
                        h_cost=h_cost
                    ))
        
        return None  # No path found
    
    # ========================================================================
    # DIJKSTRA (Finds shortest path, slower than A*)
    # ========================================================================
    
    def dijkstra(self,
                 start: Tuple[int, int],
                 goal: Tuple[int, int],
                 allow_diagonal: bool = False) -> Optional[List[Tuple[int, int]]]:
        """
        Dijkstra's algorithm - guaranteed shortest path
        Slower than A* but doesn't need a heuristic
        """
        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return None
        
        # Priority queue: (cost, position)
        open_set = []
        heapq.heappush(open_set, Node(priority=0, position=start))
        
        costs = {start: 0}
        came_from = {}
        
        while open_set:
            current_node = heapq.heappop(open_set)
            current = current_node.position
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                move_cost = self.get_move_cost(current, neighbor)
                new_cost = costs[current] + move_cost
                
                if neighbor not in costs or new_cost < costs[neighbor]:
                    costs[neighbor] = new_cost
                    came_from[neighbor] = current
                    heapq.heappush(open_set, Node(priority=new_cost, position=neighbor))
        
        return None
    
    # ========================================================================
    # BREADTH-FIRST SEARCH (Unweighted shortest path)
    # ========================================================================
    
    def bfs(self,
            start: Tuple[int, int],
            goal: Tuple[int, int],
            allow_diagonal: bool = False) -> Optional[List[Tuple[int, int]]]:
        """
        Breadth-First Search - simple, good for unweighted grids
        """
        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return None
        
        from collections import deque
        
        queue = deque([start])
        visited = {start}
        came_from = {}
        
        while queue:
            current = queue.popleft()
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)
        
        return None
    
    # ========================================================================
    # DEPTH-FIRST SEARCH (Not optimal, but fast and simple)
    # ========================================================================
    
    def dfs(self,
            start: Tuple[int, int],
            goal: Tuple[int, int],
            allow_diagonal: bool = False) -> Optional[List[Tuple[int, int]]]:
        """
        Depth-First Search - fast but doesn't guarantee shortest path
        """
        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return None
        
        stack = [start]
        visited = {start}
        came_from = {}
        
        while stack:
            current = stack.pop()
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    stack.append(neighbor)
        
        return None
    
    # ========================================================================
    # GREEDY BEST-FIRST (Fast but not optimal)
    # ========================================================================
    
    def greedy_best_first(self,
                          start: Tuple[int, int],
                          goal: Tuple[int, int],
                          allow_diagonal: bool = False,
                          heuristic: Callable = None) -> Optional[List[Tuple[int, int]]]:
        """
        Greedy Best-First Search - fast, follows heuristic greedily
        Not guaranteed optimal but often good enough
        """
        if heuristic is None:
            heuristic = self.manhattan_distance
        
        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return None
        
        open_set = []
        heapq.heappush(open_set, Node(
            priority=heuristic(start, goal),
            position=start
        ))
        
        visited = {start}
        came_from = {}
        
        while open_set:
            current_node = heapq.heappop(open_set)
            current = current_node.position
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    h = heuristic(neighbor, goal)
                    heapq.heappush(open_set, Node(priority=h, position=neighbor))
        
        return None
    
    # ========================================================================
    # MULTI-TARGET PATHFINDING
    # ========================================================================
    
    def find_nearest(self,
                     start: Tuple[int, int],
                     targets: List[Tuple[int, int]],
                     allow_diagonal: bool = False) -> Tuple[Optional[Tuple[int, int]], Optional[List[Tuple[int, int]]]]:
        """
        Find the nearest target and path to it
        
        Returns:
            (nearest_target, path) or (None, None)
        """
        from collections import deque
        
        if not self.is_valid_position(*start):
            return None, None
        
        queue = deque([start])
        visited = {start}
        came_from = {}
        
        while queue:
            current = queue.popleft()
            
            # Check if we reached any target
            if current in targets:
                return current, self._reconstruct_path(came_from, current)
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    queue.append(neighbor)
        
        return None, None
    
    def find_all_reachable(self,
                          start: Tuple[int, int],
                          max_distance: int = None,
                          allow_diagonal: bool = False) -> Set[Tuple[int, int]]:
        """
        Find all positions reachable from start
        
        Args:
            start: Starting position
            max_distance: Maximum distance to search (None = unlimited)
            allow_diagonal: Allow diagonal movement
        
        Returns:
            Set of all reachable positions
        """
        from collections import deque
        
        if not self.is_valid_position(*start):
            return set()
        
        queue = deque([(start, 0)])
        visited = {start}
        
        while queue:
            current, dist = queue.popleft()
            
            if max_distance is not None and dist >= max_distance:
                continue
            
            for neighbor in self.get_neighbors(current, allow_diagonal):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))
        
        return visited
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    def _reconstruct_path(self, came_from: Dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstruct path from came_from dict"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def smooth_path(self, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Smooth a path by removing unnecessary waypoints
        Uses line-of-sight to skip intermediate points
        """
        if not path or len(path) <= 2:
            return path
        
        smoothed = [path[0]]
        current_idx = 0
        
        while current_idx < len(path) - 1:
            # Try to skip as many points as possible
            farthest_idx = current_idx + 1
            
            for test_idx in range(len(path) - 1, current_idx, -1):
                if self._has_line_of_sight(path[current_idx], path[test_idx]):
                    farthest_idx = test_idx
                    break
            
            current_idx = farthest_idx
            smoothed.append(path[current_idx])
        
        return smoothed
    
    def _has_line_of_sight(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        """Check if there's a clear line of sight between two points"""
        x0, y0 = start
        x1, y1 = end
        
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy
        
        x, y = x0, y0
        
        while True:
            if not self.is_valid_position(x, y):
                return False
            
            if (x, y) == (x1, y1):
                return True
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy


# ============================================================================
# VISUALIZATION HELPERS
# ============================================================================

def visualize_path(grid: np.ndarray, 
                   path: List[Tuple[int, int]], 
                   start: Tuple[int, int],
                   goal: Tuple[int, int]) -> str:
    """
    Visualize a path on a grid
    
    Returns ASCII art with:
    - '#' for walls
    - '.' for walkable
    - 'S' for start
    - 'G' for goal
    - '*' for path
    """
    # Create visualization grid
    vis = []
    for y in range(grid.shape[0]):
        row = []
        for x in range(grid.shape[1]):
            if (x, y) == start:
                row.append('S')
            elif (x, y) == goal:
                row.append('G')
            elif (x, y) in path:
                row.append('*')
            elif grid[y, x] == 0 or grid[y, x] in {1, 2, 3, 4, 5, 6}:
                row.append('.')
            else:
                row.append('#')
        vis.append(''.join(row))
    
    return '\n'.join(vis)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("PATHFINDING ALGORITHMS")
    print("=" * 70)
    
    # Create a simple test grid
    grid = np.array([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 1, 0, 1, 1, 1, 0],
        [0, 1, 1, 0, 1, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 1, 0, 1, 0],
        [1, 0, 1, 1, 1, 0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 1, 1, 1, 1, 1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    
    # 0 = walkable, 1 = wall
    pathfinder = Pathfinder(grid, walkable_tiles={0})
    
    start = (1, 0)
    goal = (8, 9)
    
    print("\n📍 Grid with walls (1 = wall, 0 = walkable):")
    print(grid)
    
    # Test different algorithms
    algorithms = [
        ('A*', pathfinder.astar),
        ('Dijkstra', pathfinder.dijkstra),
        ('BFS', pathfinder.bfs),
        ('Greedy', pathfinder.greedy_best_first),
    ]
    
    for name, algorithm in algorithms:
        print(f"\n{'=' * 70}")
        print(f"🔍 {name} Pathfinding")
        print(f"{'=' * 70}")
        
        path = algorithm(start, goal, allow_diagonal=False)
        
        if path:
            print(f"✅ Path found! Length: {len(path)}")
            print(f"\nVisualization:")
            print(visualize_path(grid, path, start, goal))
        else:
            print("❌ No path found!")
    
    # Test path smoothing
    print(f"\n{'=' * 70}")
    print("🎨 Path Smoothing")
    print(f"{'=' * 70}")
    
    path = pathfinder.astar(start, goal, allow_diagonal=True)
    if path:
        print(f"Original path length: {len(path)}")
        smoothed = pathfinder.smooth_path(path)
        print(f"Smoothed path length: {len(smoothed)}")
        print(f"\nSmoothed path:")
        print(visualize_path(grid, smoothed, start, goal))
    
    # Test multi-target
    print(f"\n{'=' * 70}")
    print("🎯 Multi-Target Search")
    print(f"{'=' * 70}")
    
    targets = [(8, 1), (1, 8), (8, 8)]
    nearest, path = pathfinder.find_nearest(start, targets)
    
    if nearest:
        print(f"✅ Nearest target: {nearest}")
        print(f"   Path length: {len(path)}")
        print(f"\nVisualization:")
        print(visualize_path(grid, path, start, nearest))
    
    # Test reachable area
    print(f"\n{'=' * 70}")
    print("📏 Reachable Area (max distance = 5)")
    print(f"{'=' * 70}")
    
    reachable = pathfinder.find_all_reachable(start, max_distance=5)
    print(f"Positions reachable within 5 moves: {len(reachable)}")
    
    # Visualize reachable area
    vis = []
    for y in range(grid.shape[0]):
        row = []
        for x in range(grid.shape[1]):
            if (x, y) == start:
                row.append('S')
            elif (x, y) in reachable:
                row.append('·')
            elif grid[y, x] == 0:
                row.append(' ')
            else:
                row.append('#')
        vis.append(''.join(row))
    
    print('\n'.join(vis))
    
    print("\n" + "=" * 70)
    print("✅ Pathfinding system ready!")
    print("=" * 70)
    
    print("\n💡 Usage Tips:")
    print("  - A*: Best for most cases (optimal + fast)")
    print("  - Dijkstra: When you need guaranteed shortest path")
    print("  - BFS: Simple, unweighted grids")
    print("  - Greedy: When speed matters more than optimality")
    print("  - allow_diagonal=True for 8-directional movement")
    print("  - smooth_path() to remove zigzags")
