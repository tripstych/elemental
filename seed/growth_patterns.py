import random
import numpy as np

from game_object import GameObject
from path_finding import PathFinder

class FractalGrowth(GameObject):


    """Helper class for fractal-based growth patterns"""
    
    @staticmethod
    def recursive_tree(start, initial_length, initial_angle, length_decay, angle_variation, max_depth):
        """Generate tree points recursively"""
        points = []
        
        def branch(x, y, length, angle, depth):
            if depth <= 0 or length < 1:
                return
            
            end_x = x + int(length * np.cos(np.radians(angle)))
            end_y = y - int(length * np.sin(np.radians(angle)))
            
            # Add points along the branch
            steps = max(1, int(length))
            for i in range(steps):
                px = int(x + (end_x - x) * i / steps)
                py = int(y + (end_y - y) * i / steps)
                points.append((px, py))
            
            # Create child branches
            new_length = length * length_decay
            branch(end_x, end_y, new_length, angle - angle_variation + random.uniform(-10, 10), depth - 1)
            branch(end_x, end_y, new_length, angle + angle_variation + random.uniform(-10, 10), depth - 1)
        
        branch(start[0], start[1], initial_length, initial_angle, max_depth)
        return points
    
    @staticmethod
    def random_walk_tree(start, total_points, branch_length_range):
        """Generate tree using random walk"""
        points = [start]
        x, y = start
        
        for _ in range(total_points):
            length = random.randint(*branch_length_range)
            angle = random.uniform(0, 2 * np.pi)
            x = x + int(length * np.cos(angle))
            y = y + int(length * np.sin(angle))
            points.append((x, y))
        
        return points
    
    @staticmethod
    def dla_crystal(center, num_particles, stick_probability):
        """Diffusion-limited aggregation crystal growth"""
        crystal = {center}
        
        for _ in range(num_particles):
            # Start particle at random position on circle
            angle = random.uniform(0, 2 * np.pi)
            radius = 20
            x = int(center[0] + radius * np.cos(angle))
            y = int(center[1] + radius * np.sin(angle))
            
            # Random walk until it sticks
            for _ in range(200):
                # Check if adjacent to crystal
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if (x + dx, y + dy) in crystal:
                        if random.random() < stick_probability:
                            crystal.add((x, y))
                            break
                else:
                    # Random walk step
                    x += random.choice([-1, 0, 1])
                    y += random.choice([-1, 0, 1])
                    continue
                break
        
        return list(crystal)


class LSystemGrowth:
    """L-System based vegetation growth"""
    
    @staticmethod
    def generate(start, step_size, angle, iterations):
        """Generate L-system plant"""
        # Simple L-system: F -> FF+[+F-F-F]-[-F+F+F]
        axiom = "F"
        rules = {"F": "FF+[+F-F-F]-[-F+F+F]"}
        
        # Generate string
        current = axiom
        for _ in range(iterations):
            next_str = ""
            for char in current:
                next_str += rules.get(char, char)
            current = next_str
        
        # Interpret string as turtle graphics
        points = []
        x, y = start
        current_angle = 90  # Start pointing up
        stack = []
        
        for char in current:
            if char == "F":
                new_x = x + int(step_size * np.cos(np.radians(current_angle)))
                new_y = y - int(step_size * np.sin(np.radians(current_angle)))
                points.append((new_x, new_y))
                x, y = new_x, new_y
            elif char == "+":
                current_angle += angle
            elif char == "-":
                current_angle -= angle
            elif char == "[":
                stack.append((x, y, current_angle))
            elif char == "]":
                if stack:
                    x, y, current_angle = stack.pop()
        
        return points


class GrowthPatterns:
    """
    Collection of growth pattern functions
    Each takes (generator, seed, seed_config, max_radius)
    """
    
    @staticmethod
    def radial(generator, seed, config, max_radius):
        """Circular growth from center"""
        spikiness = config.get('spikiness', 0.5)
        decay = config.get('decay', 0.9)
        
        y_min = max(0, seed['y'] - max_radius)
        y_max = min(generator.height, seed['y'] + max_radius + 1)
        x_min = max(0, seed['x'] - max_radius)
        x_max = min(generator.width, seed['x'] + max_radius + 1)
        
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                dx = x - seed['x']
                dy = y - seed['y']
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance > max_radius:
                    continue
                
                # Add spikiness
                angle = np.arctan2(dy, dx)
                radius_variance = 1.0 + spikiness * (np.sin(angle * 5) * 0.3)
                effective_distance = distance / radius_variance
                
                if effective_distance > max_radius:
                    continue
                
                strength = seed['strength'] * (decay ** effective_distance)
                generator._claim_cell(x, y, seed, strength, config)
    
    @staticmethod
    def directional(generator, seed, config, max_radius):
        """Growth with preferred direction"""
        direction_angle = (seed['x'] * 37 + seed['y'] * 73) % 360
        direction_x = np.cos(np.radians(direction_angle))
        direction_y = np.sin(np.radians(direction_angle))
        decay = config.get('decay', 0.9)
        
        y_min = max(0, seed['y'] - max_radius)
        y_max = min(generator.height, seed['y'] + max_radius + 1)
        x_min = max(0, seed['x'] - max_radius)
        x_max = min(generator.width, seed['x'] + max_radius + 1)
        
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                dx = x - seed['x']
                dy = y - seed['y']
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance > max_radius or distance < 0.1:
                    continue
                
                # Favor growth in preferred direction
                dot_product = (dx * direction_x + dy * direction_y) / distance
                directional_bonus = max(0, dot_product) * 0.5 + 0.5
                
                strength = seed['strength'] * (decay ** distance) * directional_bonus
                generator._claim_cell(x, y, seed, strength, config)
    
    @staticmethod
    def branching(generator, seed, config, max_radius):
        """Growth along branching paths"""
        num_branches = config.get('branches', 5)
        decay = config.get('decay', 0.85)
        branch_width = config.get('branch_width', 3)
        
        for branch in range(num_branches):
            angle = (360 / num_branches) * branch + (seed['x'] * seed['y']) % 45
            angle_rad = np.radians(angle)
            
            for dist in range(0, max_radius, 2):
                wave = np.sin(dist * 0.3) * 3
                
                dx = int(np.cos(angle_rad) * dist + wave * np.sin(angle_rad))
                dy = int(np.sin(angle_rad) * dist - wave * np.cos(angle_rad))
                
                x, y = seed['x'] + dx, seed['y'] + dy
                
                if not (0 <= x < generator.width and 0 <= y < generator.height):
                    break
                
                branch_strength = seed['strength'] * (decay ** (dist / 5))
                
                # Branch width
                for radius in range(branch_width):
                    for ox in range(-radius, radius + 1):
                        for oy in range(-radius, radius + 1):
                            if ox**2 + oy**2 <= radius**2:
                                bx, by = x + ox, y + oy
                                if 0 <= bx < generator.width and 0 <= by < generator.height:
                                    width_strength = branch_strength * (1.0 - radius * 0.3)
                                    generator._claim_cell(bx, by, seed, width_strength, config)
    
    @staticmethod
    def clustered(generator, seed, config, max_radius):
        """Patchy, irregular growth"""
        decay = config.get('decay', 0.7)
        num_clusters = random.randint(
            config.get('min_clusters', 5),
            config.get('max_clusters', 10)
        )
        
        for _ in range(num_clusters):
            cluster_distance = random.uniform(0, max_radius)
            cluster_angle = random.uniform(0, 2 * np.pi)
            
            cluster_x = int(seed['x'] + cluster_distance * np.cos(cluster_angle))
            cluster_y = int(seed['y'] + cluster_distance * np.sin(cluster_angle))
            
            cluster_radius = random.randint(
                config.get('min_cluster_size', 3),
                config.get('max_cluster_size', 8)
            )
            
            for dy in range(-cluster_radius, cluster_radius + 1):
                for dx in range(-cluster_radius, cluster_radius + 1):
                    x, y = cluster_x + dx, cluster_y + dy
                    
                    if not (0 <= x < generator.width and 0 <= y < generator.height):
                        continue
                    
                    distance = np.sqrt(dx**2 + dy**2)
                    if distance > cluster_radius:
                        continue
                    
                    total_distance = np.sqrt((x - seed['x'])**2 + (y - seed['y'])**2)
                    strength = seed['strength'] * (decay ** total_distance) * (1.0 - distance / cluster_radius)
                    
                    generator._claim_cell(x, y, seed, strength, config)
    
    @staticmethod
    def spiral(generator, seed, config, max_radius):
        """Spiral growth pattern"""
        decay = config.get('decay', 0.85)
        tightness = config.get('spiral_tightness', 0.3)
        
        for angle_degrees in range(0, max_radius * 360, 10):
            angle = np.radians(angle_degrees)
            radius = angle * tightness
            
            if radius > max_radius:
                break
            
            x = int(seed['x'] + radius * np.cos(angle))
            y = int(seed['y'] + radius * np.sin(angle))
            
            if 0 <= x < generator.width and 0 <= y < generator.height:
                strength = seed['strength'] * (decay ** radius)
                
                # Make spiral have width
                for r in range(2):
                    for ox in range(-r, r + 1):
                        for oy in range(-r, r + 1):
                            if ox**2 + oy**2 <= r**2:
                                sx, sy = x + ox, y + oy
                                if 0 <= sx < generator.width and 0 <= sy < generator.height:
                                    generator._claim_cell(sx, sy, seed, strength * 0.8, config)
    
    # === INTEGRATED PATHFINDING PATTERNS (require pathfinding.py) ===
    
    @staticmethod
    def river_network(generator, seed, config, max_radius):
        """Rivers that follow terrain using flow pathfinding"""
        if not PATHFINDING_AVAILABLE:
            GrowthPatterns.directional(generator, seed, config, max_radius)
            return
        
        GrowthPatterns.radial(generator, seed, config, max_radius // 2)
        collision_map = CollisionMap(generator.width, generator.height)
        pathfinder = PathFinder(collision_map)
        num_branches = config.get('river_branches', 3)
        
        for _ in range(num_branches):
            river = pathfinder.flow_path(
                start=(seed['x'], seed['y']),
                elevation_map=generator.elevation,
                min_length=config.get('min_river_length', 10),
                max_length=max_radius * 2,
                brownian_factor=config.get('river_brownian', 0.3)
            )
            for x, y in river:
                if 0 <= x < generator.width and 0 <= y < generator.height:
                    generator._claim_cell(x, y, seed, seed['strength'], config)
    
    @staticmethod
    def fractal_forest(generator, seed, config, max_radius):
        """Forest with individual trees using fractal growth"""
        if not PATHFINDING_AVAILABLE:
            GrowthPatterns.branching(generator, seed, config, max_radius)
            return
        
        GrowthPatterns.radial(generator, seed, config, max_radius)
        num_trees = config.get('num_trees', 10)
        tree_type = config.get('tree_type', 'recursive')
        
        for _ in range(num_trees):
            angle = random.uniform(0, 2 * np.pi)
            dist = random.uniform(0, max_radius * 0.8)
            tx = int(seed['x'] + dist * np.cos(angle))
            ty = int(seed['y'] + dist * np.sin(angle))
            if not (0 <= tx < generator.width and 0 <= ty < generator.height):
                continue
            
            if tree_type == 'recursive':
                tree = FractalGrowth.recursive_tree(
                    start=(tx, ty), initial_length=config.get('tree_size', 8),
                    initial_angle=random.uniform(60, 120),
                    length_decay=config.get('tree_decay', 0.7),
                    angle_variation=config.get('tree_angle_var', 30),
                    max_depth=config.get('tree_depth', 4)
                )
            else:
                tree = FractalGrowth.random_walk_tree(
                    start=(tx, ty), total_points=config.get('tree_points', 50),
                    branch_length_range=(3, 8)
                )
            
            for px, py in tree:
                if 0 <= px < generator.width and 0 <= py < generator.height:
                    if 'trees' not in generator.metadata[py][px]:
                        generator.metadata[py][px]['trees'] = []
                    generator.metadata[py][px]['trees'].append({'type': tree_type, 'seed_x': tx, 'seed_y': ty})
    
    @staticmethod
    def crystal_field_dla(generator, seed, config, max_radius):
        """Crystal field using DLA"""
        if not PATHFINDING_AVAILABLE:
            GrowthPatterns.clustered(generator, seed, config, max_radius)
            return
        
        num_clusters = config.get('num_clusters', 5)
        for _ in range(num_clusters):
            angle = random.uniform(0, 2 * np.pi)
            dist = random.uniform(0, max_radius)
            cx = int(seed['x'] + dist * np.cos(angle))
            cy = int(seed['y'] + dist * np.sin(angle))
            if not (0 <= cx < generator.width and 0 <= cy < generator.height):
                continue
            
            crystal = FractalGrowth.diffusion_limited_aggregation(
                start=(cx, cy), width=generator.width, height=generator.height,
                num_particles=config.get('particles_per_cluster', 30),
                stick_probability=config.get('stick_prob', 0.4)
            )
            
            for x, y in crystal:
                if 0 <= x < generator.width and 0 <= y < generator.height:
                    dist_from_seed = np.sqrt((x-seed['x'])**2 + (y-seed['y'])**2)
                    strength = seed['strength'] * max(0.0, 1.0 - dist_from_seed / (max_radius + 1))
                    if strength > generator.terrain_strength[y, x]:
                        generator._claim_cell(x, y, seed, strength, config)
    
    @staticmethod
    def lsystem_vegetation(generator, seed, config, max_radius):
        """Vegetation using L-systems"""
        if not PATHFINDING_AVAILABLE:
            GrowthPatterns.radial(generator, seed, config, max_radius)
            return
        
        GrowthPatterns.radial(generator, seed, config, max_radius)
        num_plants = config.get('num_plants', 15)
        axiom = config.get('lsystem_axiom', 'F')
        rules = config.get('lsystem_rules', {'F': 'F[+F]F[-F]F'})
        iterations = config.get('lsystem_iterations', 3)
        
        for _ in range(num_plants):
            angle = random.uniform(0, 2 * np.pi)
            dist = random.uniform(0, max_radius * 0.9)
            px = int(seed['x'] + dist * np.cos(angle))
            py = int(seed['y'] + dist * np.sin(angle))
            if not (0 <= px < generator.width and 0 <= py < generator.height):
                continue
            
            plant = FractalGrowth.l_system(
                axiom=axiom, rules=rules, iterations=iterations,
                start=(px, py), step_size=config.get('plant_step_size', 2),
                angle=config.get('plant_angle', 25)
            )
            
            for x, y in plant:
                if 0 <= x < generator.width and 0 <= y < generator.height:
                    if 'vegetation' not in generator.metadata[y][x]:
                        generator.metadata[y][x]['vegetation'] = []
                    generator.metadata[y][x]['vegetation'].append('lsystem_plant')

