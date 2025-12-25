"""
Pathfinding and Growth Algorithms
- A* with Brownian motion for organic paths
- Collision detection and avoidance
- Fractal tree growth (L-systems and recursive branching)
- Useful for rivers, roads, vegetation, etc.
"""

import numpy as np
import random
from typing import List, Tuple, Set, Dict, Callable
import heapq
from collections import deque
from game_object import GameObject
from collision_map import CollisionMap

class PathFinder(GameObject):
    """
    A* pathfinding with Brownian motion for organic paths
    """
    
    def __init__(self, collision_map: CollisionMap):
        self.collision_map = collision_map
        self.width = collision_map.width
        self.height = collision_map.height
    
    def find_path(self, 
                  start: Tuple[int, int], 
                  goal: Tuple[int, int],
                  brownian_factor: float = 0.0,
                  avoid_obstacles: bool = True,
                  max_cost: float = None) -> List[Tuple[int, int]]:
        """
        A* pathfinding with optional Brownian motion
        
        Args:
            start: Starting position (x, y)
            goal: Goal position (x, y)
            brownian_factor: 0.0 = perfect A*, 1.0 = random walk, 0.3 = organic curves
            avoid_obstacles: Use collision map for avoidance
            max_cost: Stop if path cost exceeds this
            
        Returns:
            List of (x, y) positions from start to goal
        """
        start_x, start_y = start
        goal_x, goal_y = goal
        
        # Priority queue: (f_score, counter, position, path)
        counter = 0
        frontier = [(0, counter, start, [start])]
        visited = set()
        
        while frontier:
            f_score, _, current, path = heapq.heappop(frontier)
            
            if current in visited:
                continue
            visited.add(current)
            
            # Reached goal?
            if current == goal:
                return path
            
            # Max cost exceeded?
            if max_cost and f_score > max_cost:
                continue
            
            x, y = current
            
            # Explore neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), 
                          (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nx, ny = x + dx, y + dy
                
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                
                if (nx, ny) in visited:
                    continue
                
                # Calculate cost
                move_cost = np.sqrt(dx**2 + dy**2)  # Diagonal = sqrt(2)
                
                # Add avoidance cost
                if avoid_obstacles:
                    avoidance = self.collision_map.get_avoidance(nx, ny)
                    move_cost += avoidance * 10  # Scale avoidance
                
                # Add terrain cost
                move_cost *= self.collision_map.cost_map[ny, nx]
                
                g_score = f_score + move_cost
                
                # Heuristic (Manhattan distance with Brownian noise)
                h_score = abs(nx - goal_x) + abs(ny - goal_y)
                
                # Add Brownian motion (randomness)
                if brownian_factor > 0:
                    brownian_noise = random.uniform(-brownian_factor, brownian_factor) * h_score
                    h_score += brownian_noise
                
                new_f_score = g_score + h_score
                
                counter += 1
                new_path = path + [(nx, ny)]
                heapq.heappush(frontier, (new_f_score, counter, (nx, ny), new_path))
        
        # No path found
        return []
    
    def flow_path(self, 
                  start: Tuple[int, int],
                  elevation_map: np.ndarray,
                  min_length: int = 10,
                  max_length: int = 100,
                  brownian_factor: float = 0.2) -> List[Tuple[int, int]]:
        """
        Follow downhill slope (for rivers)
        
        Args:
            start: Starting position
            elevation_map: Height map
            min_length: Minimum path length
            max_length: Maximum path length
            brownian_factor: Randomness in direction choice
            
        Returns:
            List of positions
        """
        path = [start]
        x, y = start
        
        for _ in range(max_length):
            current_elev = elevation_map[y, x]
            
            # Find downhill neighbors
            candidates = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                          (-1, -1), (1, -1), (-1, 1), (1, 1)]:
                nx, ny = x + dx, y + dy
                
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                
                neighbor_elev = elevation_map[ny, nx]
                
                # Only go downhill (with small tolerance)
                if neighbor_elev < current_elev - 0.0001:
                    drop = current_elev - neighbor_elev
                    candidates.append((drop, nx, ny))
            
            if not candidates:
                break  # Reached local minimum
            
            # Sort by steepness
            candidates.sort(reverse=True)
            
            # Pick direction with Brownian randomness
            if brownian_factor > 0 and random.random() < brownian_factor:
                # Random choice from top 3
                choice_idx = random.randint(0, min(2, len(candidates) - 1))
                _, nx, ny = candidates[choice_idx]
            else:
                # Steepest descent
                _, nx, ny = candidates[0]
            
            path.append((nx, ny))
            x, y = nx, ny
        
        return path if len(path) >= min_length else []


class FractalGrowth:
    """
    Fractal algorithms for tree-like growth
    """
    
    @staticmethod
    def recursive_tree(start: Tuple[int, int],
                      initial_length: int,
                      initial_angle: float,
                      length_decay: float = 0.7,
                      angle_variation: float = 30.0,
                      min_length: int = 2,
                      branch_probability: float = 0.8,
                      max_depth: int = 6) -> List[Tuple[int, int]]:
        """
        Recursive tree branching
        
        Args:
            start: Root position (x, y)
            initial_length: Starting branch length
            initial_angle: Starting angle in degrees
            length_decay: How much shorter each branch gets (0.7 = 70%)
            angle_variation: Random angle variation
            min_length: Stop when branches this short
            branch_probability: Chance to create a branch
            max_depth: Maximum recursion depth
            
        Returns:
            List of all points in the tree
        """
        points = []
        
        def _branch(x, y, length, angle, depth):
            if depth > max_depth or length < min_length:
                return
            
            # Calculate end point
            angle_rad = np.radians(angle)
            end_x = int(x + length * np.cos(angle_rad))
            end_y = int(y + length * np.sin(angle_rad))
            
            # Add all points along branch
            steps = max(int(length), 1)
            for i in range(steps + 1):
                t = i / steps
                bx = int(x + (end_x - x) * t)
                by = int(y + (end_y - y) * t)
                points.append((bx, by))
            
            # Recurse with smaller branches
            if random.random() < branch_probability:
                new_length = length * length_decay
                
                # Left branch
                left_angle = angle + random.uniform(-angle_variation, -angle_variation/2)
                _branch(end_x, end_y, new_length, left_angle, depth + 1)
                
                # Right branch
                right_angle = angle + random.uniform(angle_variation/2, angle_variation)
                _branch(end_x, end_y, new_length, right_angle, depth + 1)
        
        x, y = start
        _branch(x, y, initial_length, initial_angle, 0)
        
        return points
    
    @staticmethod
    def random_walk_tree(start: Tuple[int, int],
                        total_points: int = 100,
                        branch_points: int = 5,
                        branch_length_range: Tuple[int, int] = (5, 15)) -> List[Tuple[int, int]]:
        """
        Random walk tree: pick random visited point, branch off
        
        Args:
            start: Starting position
            total_points: Total points to generate
            branch_points: Points to choose from for branching
            branch_length_range: (min, max) length for each branch
            
        Returns:
            List of all points
        """
        points = [start]
        
        while len(points) < total_points:
            # Pick a random point we've visited
            branch_from = random.choice(points[-branch_points:] if len(points) > branch_points else points)
            
            # Random direction
            angle = random.uniform(0, 360)
            length = random.randint(*branch_length_range)
            
            # Walk from that point
            x, y = branch_from
            angle_rad = np.radians(angle)
            
            for step in range(length):
                x += int(np.cos(angle_rad))
                y += int(np.sin(angle_rad))
                points.append((x, y))
                
                # Small random perturbation each step
                angle += random.uniform(-15, 15)
                angle_rad = np.radians(angle)
        
        return points
    
    @staticmethod
    def diffusion_limited_aggregation(start: Tuple[int, int],
                                     width: int,
                                     height: int,
                                     num_particles: int = 200,
                                     stick_probability: float = 0.3) -> List[Tuple[int, int]]:
        """
        DLA - particles random walk until they stick to structure
        Creates organic, crystal-like patterns
        
        Args:
            start: Seed position
            width, height: Bounds
            num_particles: Number of particles to add
            stick_probability: Chance to stick when adjacent
            
        Returns:
            List of all positions in structure
        """
        structure = {start}
        points = [start]
        
        for _ in range(num_particles):
            # Start particle at random edge
            if random.random() < 0.5:
                px = random.randint(0, width - 1)
                py = 0 if random.random() < 0.5 else height - 1
            else:
                px = 0 if random.random() < 0.5 else width - 1
                py = random.randint(0, height - 1)
            
            # Random walk until adjacent to structure
            max_steps = 1000
            for _ in range(max_steps):
                # Check if adjacent to structure
                is_adjacent = False
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = px + dx, py + dy
                    if (nx, ny) in structure:
                        is_adjacent = True
                        break
                
                if is_adjacent and random.random() < stick_probability:
                    structure.add((px, py))
                    points.append((px, py))
                    break
                
                # Random walk
                dx, dy = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
                px = max(0, min(width - 1, px + dx))
                py = max(0, min(height - 1, py + dy))
        
        return points
    
    @staticmethod
    def l_system(axiom: str,
                rules: Dict[str, str],
                iterations: int,
                start: Tuple[int, int],
                step_size: int = 2,
                angle: float = 25.0) -> List[Tuple[int, int]]:
        """
        L-system for plant-like growth
        
        Example:
            axiom = "F"
            rules = {"F": "F[+F]F[-F]F"}
            Creates a branching plant
            
        Commands:
            F = move forward
            + = turn right
            - = turn left
            [ = push state
            ] = pop state
            
        Args:
            axiom: Starting string
            rules: Replacement rules
            iterations: How many times to apply rules
            start: Starting position
            step_size: Distance to move for 'F'
            angle: Angle to turn for +/-
            
        Returns:
            List of points
        """
        # Generate L-system string
        current = axiom
        for _ in range(iterations):
            next_string = ""
            for char in current:
                next_string += rules.get(char, char)
            current = next_string
        
        # Interpret string as turtle graphics
        points = []
        x, y = start
        heading = 90.0  # Start pointing up
        
        stack = []  # For [ and ]
        
        for char in current:
            if char == 'F':
                # Move forward
                rad = np.radians(heading)
                new_x = int(x + step_size * np.cos(rad))
                new_y = int(y + step_size * np.sin(rad))
                
                # Add points along line
                steps = max(int(step_size), 1)
                for i in range(steps + 1):
                    t = i / steps
                    px = int(x + (new_x - x) * t)
                    py = int(y + (new_y - y) * t)
                    points.append((px, py))
                
                x, y = new_x, new_y
            
            elif char == '+':
                heading += angle
            
            elif char == '-':
                heading -= angle
            
            elif char == '[':
                stack.append((x, y, heading))
            
            elif char == ']':
                if stack:
                    x, y, heading = stack.pop()
        
        return points


# Example usage and tests
if __name__ == "__main__":
    print("="*70)
    print("PATHFINDING & GROWTH ALGORITHMS TEST")
    print("="*70)
    
    # Test collision detection
    print("\n1. Collision Detection")
    collision_map = CollisionMap(100, 100)
    collision_map.add_obstacle(50, 50, 'mountain', avoidance_radius=10, avoidance_strength=2.0)
    print(f"   Avoidance at (50, 50): {collision_map.get_avoidance(50, 50):.2f}")
    print(f"   Avoidance at (55, 50): {collision_map.get_avoidance(55, 50):.2f}")
    print(f"   Avoidance at (70, 50): {collision_map.get_avoidance(70, 50):.2f}")
    
    # Test A* pathfinding
    print("\n2. A* Pathfinding")
    pathfinder = PathFinder(collision_map)
    path = pathfinder.find_path((10, 10), (90, 90), brownian_factor=0.0)
    print(f"   Perfect A* path length: {len(path)}")
    
    path_organic = pathfinder.find_path((10, 10), (90, 90), brownian_factor=0.3)
    print(f"   Organic path (brownian=0.3) length: {len(path_organic)}")
    
    # Test flow path (rivers)
    print("\n3. Flow Path (Rivers)")
    elevation = np.random.rand(100, 100)
    elevation[50:60, 40:60] = 0.9  # Mountain
    elevation[10:20, 10:20] = 0.1  # Valley
    
    river = pathfinder.flow_path((55, 55), elevation, brownian_factor=0.2)
    print(f"   River length: {len(river)} tiles")
    
    # Test recursive tree
    print("\n4. Recursive Tree")
    tree_points = FractalGrowth.recursive_tree(
        start=(50, 50),
        initial_length=20,
        initial_angle=90,
        length_decay=0.7,
        angle_variation=30,
        max_depth=5
    )
    print(f"   Tree has {len(tree_points)} points")
    
    # Test random walk tree
    print("\n5. Random Walk Tree")
    walk_tree = FractalGrowth.random_walk_tree(
        start=(50, 50),
        total_points=100,
        branch_length_range=(5, 15)
    )
    print(f"   Random walk tree: {len(walk_tree)} points")
    
    # Test DLA
    print("\n6. Diffusion Limited Aggregation")
    dla = FractalGrowth.diffusion_limited_aggregation(
        start=(50, 50),
        width=100,
        height=100,
        num_particles=50
    )
    print(f"   DLA structure: {len(dla)} points")
    
    # Test L-system
    print("\n7. L-System Plant")
    plant = FractalGrowth.l_system(
        axiom="F",
        rules={"F": "F[+F]F[-F]F"},
        iterations=3,
        start=(50, 50),
        step_size=3,
        angle=25.0
    )
    print(f"   L-system plant: {len(plant)} points")
    
    print("\n" + "="*70)
    print("All tests complete!")
