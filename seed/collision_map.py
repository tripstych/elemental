from game_object import GameObject

class CollisionMap(GameObject):
    """
    Spatial hash map for fast collision detection
    Tracks what's at each cell and provides avoidance
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # What occupies each cell
        self.occupants = [[[] for _ in range(width)] for _ in range(height)]
        
        # Cost modifiers for pathfinding
        self.cost_map = np.ones((height, width))
        
        # Avoidance zones (higher = avoid more)
        self.avoidance_map = np.zeros((height, width))
    
    def add_obstacle(self, x: int, y: int, obstacle_type: str, avoidance_radius: int = 0, avoidance_strength: float = 1.0):
        """Add an obstacle that affects pathfinding"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.occupants[y][x].append(obstacle_type)
            
            # Add avoidance zone around obstacle
            if avoidance_radius > 0:
                for dy in range(-avoidance_radius, avoidance_radius + 1):
                    for dx in range(-avoidance_radius, avoidance_radius + 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            dist = np.sqrt(dx**2 + dy**2)
                            if dist <= avoidance_radius:
                                # Falloff with distance
                                falloff = 1.0 - (dist / avoidance_radius)
                                self.avoidance_map[ny, nx] += avoidance_strength * falloff
    
    def is_occupied(self, x: int, y: int, by_type: str = None) -> bool:
        """Check if cell is occupied (optionally by specific type)"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return True  # Out of bounds = occupied
        
        if by_type is None:
            return len(self.occupants[y][x]) > 0
        else:
            return by_type in self.occupants[y][x]
    
    def get_avoidance(self, x: int, y: int) -> float:
        """Get avoidance strength at position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.avoidance_map[y, x]
        return 1000.0  # Very high avoidance for out of bounds
    
    def clear_type(self, obstacle_type: str):
        """Remove all obstacles of a specific type"""
        for y in range(self.height):
            for x in range(self.width):
                if obstacle_type in self.occupants[y][x]:
                    self.occupants[y][x].remove(obstacle_type)

