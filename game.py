"""
Elemental RPG - Beta Test Game Loop
Integrates: dungeon generation, animate entities, pathfinding, combat, items
"""

import sys
import os
import json
import random
from typing import Dict, List, Optional, Tuple

# Add seed directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'seed'))

from seed.animate import Animate, Inventory, Stats, Player, Monster
from seed.dungeon_generator import DungeonGenerator
from seed.pathfinding import Pathfinder
from seed.spell_casting import SpellCaster, SpellResult, cast_spell_full
from seed.visibility import Visibility

# ============================================================================
# DATA LOADING
# ============================================================================

def load_game_objects(filepath: str = None) -> List[Dict]:
    """Load game objects from JSON"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), 'game_objects.json')
    
    with open(filepath, 'r') as f:
        return json.load(f)

def load_spells(filepath: str = None) -> Dict:
    """Load spell definitions"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), 'elemental_spells.json')
    
    with open(filepath, 'r') as f:
        return json.load(f)

# ============================================================================
# GAME WORLD
# ============================================================================

class GameWorld:
    """
    Manages the game state: dungeon, entities, items
    """
    
    def __init__(self, width: int = 60, height: int = 30, seed: int = None):
        self.width = width
        self.height = height
        self.seed = seed or random.randint(0, 999999)
        
        # Generate dungeon
        self.dungeon = DungeonGenerator(width, height, seed=self.seed, algorithm='bsp')
        self.dungeon.generate()
        
        # Walkable tiles for pathfinding
        self.walkable_tiles = {
            DungeonGenerator.FLOOR,
            DungeonGenerator.CORRIDOR, 
            DungeonGenerator.ROOM_FLOOR,
            DungeonGenerator.ENTRANCE,
            DungeonGenerator.EXIT,
            DungeonGenerator.DOOR
        }
        
        # Setup pathfinding
        self.pathfinder = Pathfinder(self.dungeon.grid, self.walkable_tiles)
        
        # Setup visibility (walls block sight)
        blocking_tiles = {DungeonGenerator.WALL}
        self.visibility = Visibility(self.dungeon.grid, blocking_tiles)
        
        # Entity tracking
        self.player: Optional[Player] = None
        self.monsters: List[Monster] = []
        self.items_on_ground: Dict[Tuple[int, int], List[Dict]] = {}  # (x,y) -> [items]
        
        # Game object database
        self.game_objects = load_game_objects()
        self.spells = load_spells()
        
        # Filter objects by type for spawning
        self.objects_by_type = {}
        for obj in self.game_objects:
            obj_type = obj.get('type', 'misc')
            if obj_type not in self.objects_by_type:
                self.objects_by_type[obj_type] = []
            self.objects_by_type[obj_type].append(obj)
    
    def spawn_player(self, name: str = "Hero") -> Player:
        """Create and place player at dungeon entrance"""
        # Find entrance
        entrance_pos = self.dungeon.find_positions(DungeonGenerator.ENTRANCE)
        if entrance_pos:
            x, y = entrance_pos[0]
        else:
            # Fallback: find any floor tile
            floors = self.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR)
            x, y = floors[0] if floors else (1, 1)
        
        # Create player
        self.player = Player(name, x=x, y=y)
        self.player.set_pathfinder(self.pathfinder)
        
        # Give starter essences
        self.player.inventory.add_essence('fire', 100)
        self.player.inventory.add_essence('water', 100)
        self.player.inventory.add_essence('earth', 100)
        self.player.inventory.add_essence('air', 100)
        
        # Learn basic spells
        self.player.inventory.learn_spell('fireball.n.01')
        self.player.inventory.learn_spell('heal.v.01')
        blit = {
            'name': 'blit',
            'type': 'food',
            'weight': 0.1,
            'essence': { 'earth': 53, 'water': 47, 'fire': 12, 'air': 8 }
        }

        self.player.inventory.add_object(blit)
        self.player.inventory.add_object(blit)
        self.player.inventory.add_object(blit)
        self.player.inventory.add_object(blit)
        
        return self.player
    
    def spawn_monster(self, name: str = None, near_player: bool = False) -> Monster:
        """Spawn a monster in the dungeon"""
        if name is None:
            names = ["Goblin", "Skeleton", "Orc", "Troll", "Spider", "Bat", "Rat"]
            name = random.choice(names)
        
        # Find valid spawn position
        floors = (self.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) + 
                  self.dungeon.find_positions(DungeonGenerator.CORRIDOR))
        
        if near_player and self.player:
            # Filter to positions within 10-20 tiles of player
            valid = []
            for pos in floors:
                dist = ((pos[0] - self.player.x)**2 + (pos[1] - self.player.y)**2)**0.5
                if 5 < dist < 20:
                    valid.append(pos)
            floors = valid if valid else floors
        
        x, y = random.choice(floors) if floors else (5, 5)
        
        monster = Monster(name, x=x, y=y)
        monster.set_pathfinder(self.pathfinder)
        
        # Set as enemy targeting player
        monster.faction = 'enemy'
        monster.is_hostile = True
        if self.player:
            monster.target = self.player
        
        self.monsters.append(monster)
        return monster
    
    def spawn_item(self, pos: Tuple[int, int] = None, item_type: str = None) -> Dict:
        """Spawn an item on the ground"""
        # Choose random position if not specified
        if pos is None:
            floors = self.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR)
            pos = random.choice(floors) if floors else (1, 1)

        # Choose item type
        if item_type is None:
            item_type = random.choice(['weapons', 'tools', 'gems', 'food'])

        # Get random item of that type
        if item_type in self.objects_by_type:
            item = random.choice(self.objects_by_type[item_type]).copy()
        else:
            # Fallback
            item = random.choice(self.game_objects).copy()

        # Add combat stats to weapons
        if item.get('type') == 'weapons':
            self._add_weapon_stats(item)

        # Add to ground
        if pos not in self.items_on_ground:
            self.items_on_ground[pos] = []
        self.items_on_ground[pos].append(item)

        return item

    def _add_weapon_stats(self, item: Dict):
        """Add combat stats to a weapon based on its properties"""
        name = item.get('name', '').lower()

        # Determine if weapon is ranged based on name/definition
        ranged_keywords = ['bow', 'crossbow', 'gun', 'pistol', 'rifle', 'sling',
                          'javelin', 'dart', 'throwing', 'missile', 'arrow']
        definition = item.get('definition', '').lower()

        is_ranged = any(kw in name or kw in definition for kw in ranged_keywords)
        item['ranged'] = is_ranged

        # Base damage bonus based on size
        size = item.get('size', 'medium')
        size_bonus = {'small': 2, 'medium': 5, 'large': 8}.get(size, 5)

        # Material bonus
        material = item.get('material', 'wood').lower()
        material_bonus = {
            'wood': 0, 'bone': 1, 'stone': 2, 'bronze': 3,
            'iron': 4, 'steel': 6, 'metal': 5, 'silver': 5
        }.get(material, 2)

        # Add some randomness
        item['damage_bonus'] = size_bonus + material_bonus + random.randint(-1, 3)

        # Ranged weapons get range stat
        if is_ranged:
            item['range'] = 4 + random.randint(0, 3)  # 4-7 tiles
    
    def scatter_items(self, count: int = 10):
        """Randomly scatter items throughout dungeon"""
        for _ in range(count):
            self.spawn_item()
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.dungeon.grid[y, x] in self.walkable_tiles
    
    def get_entity_at(self, x: int, y: int) -> Optional[Animate]:
        """Get entity at position (player or monster)"""
        if self.player and self.player.x == x and self.player.y == y:
            return self.player
        for m in self.monsters:
            if m.x == x and m.y == y and m.stats.is_alive():
                return m
        return None
    
    # =========================================================================
    # VISIBILITY
    # =========================================================================
    
    def can_see(self, viewer: Animate, target: Animate, max_range: float = 10) -> bool:
        """Check if viewer can see target entity"""
        return self.visibility.can_see_entity(
            viewer.x, viewer.y, target.x, target.y, max_range
        )
    
    def has_los(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check line of sight between two points"""
        return self.visibility.has_line_of_sight(x1, y1, x2, y2)
    
    def get_fov(self, x: int, y: int, radius: int = 10) -> set:
        """Get set of visible tiles from a position"""
        return self.visibility.compute_fov(x, y, radius)
    
    def get_player_fov(self, radius: int = 10) -> set:
        """Get player's current field of view"""
        if not self.player:
            return set()
        return self.visibility.compute_fov(self.player.x, self.player.y, radius)
    
    def get_visible_monsters(self, radius: int = 10) -> List[Monster]:
        """Get monsters visible to player"""
        if not self.player:
            return []
        
        fov = self.get_player_fov(radius)
        visible = []
        for m in self.monsters:
            if m.stats.is_alive() and (m.x, m.y) in fov:
                visible.append(m)
        return visible
    
    def get_visible_items(self, radius: int = 10) -> Dict[Tuple[int, int], List[Dict]]:
        """Get items visible to player"""
        if not self.player:
            return {}
        
        fov = self.get_player_fov(radius)
        visible = {}
        for pos, items in self.items_on_ground.items():
            if pos in fov and items:
                visible[pos] = items
        return visible
    
    def render(self, show_fov: bool = False) -> str:
        """Render the dungeon with entities and items"""
        # Tile characters
        tile_chars = {
            DungeonGenerator.FLOOR: '.',
            DungeonGenerator.WALL: '#',
            DungeonGenerator.DOOR: '+',
            DungeonGenerator.CORRIDOR: '·',
            DungeonGenerator.ROOM_FLOOR: '.',
            DungeonGenerator.ENTRANCE: '<',
            DungeonGenerator.EXIT: '>'
        }
        
        lines = []
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                # Check for player
                if self.player and self.player.x == x and self.player.y == y:
                    line += '@'
                    continue
                
                # Check for monsters
                monster_here = None
                for m in self.monsters:
                    if m.x == x and m.y == y and m.stats.is_alive():
                        monster_here = m
                        break
                
                if monster_here:
                    # First letter of monster name
                    line += monster_here.name[0].upper()
                    continue
                
                # Check for items
                if (x, y) in self.items_on_ground and self.items_on_ground[(x, y)]:
                    line += '!'
                    continue
                
                # Default: tile
                tile = self.dungeon.grid[y, x]
                line += tile_chars.get(tile, '?')
            
            lines.append(line)
        
        return '\n'.join(lines)


# ============================================================================
# GAME ENGINE
# ============================================================================

class GameEngine:
    """
    Main game loop and command processing
    """
    
    HELP_TEXT = """
╔══════════════════════════════════════════════════════════════════════╗
║                    ELEMENTAL RPG - BETA TEST                         ║
╠══════════════════════════════════════════════════════════════════════╣
║ MOVEMENT:  n/north, s/south, e/east, w/west                          ║
║            wasd also works (w=up, a=left, s=down, d=right)          ║
║                                                                      ║
║ ACTIONS:   look        - describe current location                   ║
║            pickup/get  - pick up items at your feet                  ║
║            drop <#>    - drop item # from inventory                  ║
║            use <#>     - use/eat item # (food heals)                ║
║            inventory/i - show your inventory                         ║
║            stats       - show your character stats                   ║
║            attack      - attack adjacent monster                     ║
║            cast <spell>- cast a spell (fireball, heal)              ║
║            wait        - skip turn (monsters still act)             ║
║                                                                      ║
║ META:      map         - show full dungeon map                       ║
║            help        - show this help                              ║
║            quit        - exit game                                   ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    
    DIRECTION_MAP = {
        'n': (0, -1), 'north': (0, -1), 'w': (0, -1),
        's': (0, 1), 'south': (0, 1), 'z': (0, 1),
        'e': (1, 0), 'east': (1, 0), 'd': (1, 0),
        'w': (-1, 0), 'west': (-1, 0), 'a': (-1, 0),
        # Arrow key escape sequences get translated before this
    }
    
    def __init__(self, world: GameWorld = None):
        self.world = world or GameWorld()
        self.running = True
        self.turn_count = 0
        
        # Spell definitions for casting
        self.spell_defs = {
            'fireball': {
                'synset': 'fireball.n.01',
                'word': 'krata',
                'composition': {'fire': 58, 'water': 5, 'earth': 10, 'air': 12},
                'definition': 'a ball of fire',
                'spell_effect': {'type': 'damage', 'element': 'fire'}
            },
            'heal': {
                'synset': 'heal.v.01',
                'word': 'lumno',
                'composition': {'fire': 8, 'water': 55, 'earth': 15, 'air': 18},
                'definition': 'restore to health',
                'spell_effect': {'type': 'heal', 'amount': 30}
            }
        }
    
    def start(self):
        """Initialize game and start loop"""
        print("\n" + "="*70)
        print("          ELEMENTAL RPG - BETA TEST")
        print("="*70)
        
        # Spawn player
        player_name = input("\nEnter your name (or press Enter for 'Hero'): ").strip()
        if not player_name:
            player_name = "Hero"
        
        self.world.spawn_player(player_name)
        print(f"\n🧙 {player_name} enters the dungeon...")
        
        # Spawn monsters
        for _ in range(5):
            m = self.world.spawn_monster(near_player=True)
            print(f"👹 A {m.name} lurks in the shadows...")
        
        # Scatter items
        self.world.scatter_items(15)
        print("✨ Ancient treasures glitter in the darkness...")
        
        print(self.HELP_TEXT)
        
        # Show initial view
        self.cmd_look()
        
        # Main loop
        self.game_loop()
    
    def game_loop(self):
        """Main game loop"""
        while self.running:
            # Check player alive
            if not self.world.player.stats.is_alive():
                self.player_death()
                continue
            
            # Get command
            try:
                cmd = input("\n> ").strip().lower()
            except EOFError:
                break
            
            if not cmd:
                continue
            
            # Process command
            self.process_command(cmd)
            
            # Monster turns (if player did something)
            if self.turn_count > 0:
                self.monster_turns()
    
    def process_command(self, cmd: str):
        """Process player command"""
        parts = cmd.split()
        action = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Movement - handle both compass and WASD
        movement_cmds = {
            'n': 'n', 'north': 'n', 
            's': 's', 'south': 's',
            'e': 'e', 'east': 'e',
            'west': 'west',
            'a': 'a', 'd': 'd',
            'up': 'n', 'down': 's', 'left': 'west', 'right': 'e'
        }
        
        if action in movement_cmds:
            self.cmd_move(movement_cmds[action])
        elif action == 'w':
            # Ambiguous: could be WASD 'w' (up) or compass 'west'
            # Default to WASD (up)
            self.cmd_move('n')
        
        # Actions
        elif action in ['look', 'l']:
            self.cmd_look()
        elif action in ['pickup', 'get', 'take', 'p']:
            self.cmd_pickup()
        elif action in ['inventory', 'inv', 'i']:
            self.cmd_inventory()
        elif action in ['stats', 'st']:
            self.cmd_stats()
        elif action == 'attack':
            self.cmd_attack()
        elif action == 'cast':
            spell_name = args[0] if args else None
            self.cmd_cast(spell_name)
        elif action == 'drop':
            item_num = int(args[0]) if args else None
            self.cmd_drop(item_num)
        elif action == 'use':
            item_num = int(args[0]) if args else None
            self.cmd_use(item_num)
        elif action == 'wait':
            print("⏳ You wait...")
            self.turn_count += 1
        elif action == 'map':
            self.cmd_map()
        elif action == 'help':
            print(self.HELP_TEXT)
        elif action in ['quit', 'exit', 'q']:
            self.running = False
            print("\n👋 Thanks for playing!")
        else:
            print(f"❓ Unknown command: {action}. Type 'help' for commands.")
    
    def cmd_move(self, direction: str):
        """Move player in direction"""
        player = self.world.player
        
        # Get direction vector
        # WASD: w=up, a=left, s=down, d=right
        # Also support n/s/e/w compass directions
        dir_map = {
            'n': (0, -1), 'north': (0, -1), 'up': (0, -1),
            's': (0, 1), 'south': (0, 1), 'down': (0, 1),
            'e': (1, 0), 'east': (1, 0), 'right': (1, 0),
            'west': (-1, 0), 'left': (-1, 0),
            # WASD (w=west conflicts with w=up, so we handle WASD mode)
            'a': (-1, 0), 'd': (1, 0),
        }
        
        if direction not in dir_map:
            print(f"❓ Unknown direction: {direction}")
            return
        
        dx, dy = dir_map[direction]
        new_x, new_y = player.x + dx, player.y + dy
        
        # Check for monster
        entity = self.world.get_entity_at(new_x, new_y)
        if entity and entity != player:
            print(f"⚔️ A {entity.name} blocks your path!")
            return
        
        # Check walkable
        if not self.world.is_walkable(new_x, new_y):
            print("🧱 You bump into a wall.")
            return
        
        # Move
        player.x = new_x
        player.y = new_y
        self.turn_count += 1
        
        # Check for items
        pos = (new_x, new_y)
        if pos in self.world.items_on_ground and self.world.items_on_ground[pos]:
            items = self.world.items_on_ground[pos]
            if len(items) == 1:
                print(f"✨ You see a {items[0]['name']} here.")
            else:
                print(f"✨ You see {len(items)} items here.")
        
        # Check for exit
        if self.world.dungeon.grid[new_y, new_x] == DungeonGenerator.EXIT:
            print("🚪 You found the exit! (In full game, this leads to next level)")
        
        # Brief location
        self._brief_look()
    
    def cmd_look(self):
        """Describe current location"""
        player = self.world.player
        x, y = player.x, player.y
        
        # Get tile type
        tile = self.world.dungeon.grid[y, x]
        tile_names = {
            DungeonGenerator.FLOOR: "stone floor",
            DungeonGenerator.CORRIDOR: "narrow corridor",
            DungeonGenerator.ROOM_FLOOR: "chamber floor",
            DungeonGenerator.ENTRANCE: "dungeon entrance",
            DungeonGenerator.EXIT: "stairway leading down",
            DungeonGenerator.DOOR: "doorway"
        }
        tile_name = tile_names.get(tile, "dungeon floor")
        
        print(f"\n📍 You stand on {tile_name}.")
        
        # Items here
        pos = (x, y)
        if pos in self.world.items_on_ground and self.world.items_on_ground[pos]:
            items = self.world.items_on_ground[pos]
            print(f"✨ On the ground: {', '.join(i['name'] for i in items)}")
        
        # Nearby monsters
        for m in self.world.monsters:
            if m.stats.is_alive():
                dist = ((m.x - x)**2 + (m.y - y)**2)**0.5
                if dist <= 5:
                    direction = self._get_direction(x, y, m.x, m.y)
                    print(f"👹 A {m.name} is {direction}! (HP: {m.stats.current_health}/{m.stats.max_health})")
        
        # Show local map
        self._show_local_map()
    
    def _brief_look(self):
        """Quick status after moving"""
        player = self.world.player
        x, y = player.x, player.y
        
        # Check nearby monsters
        for m in self.world.monsters:
            if m.stats.is_alive():
                dist = ((m.x - x)**2 + (m.y - y)**2)**0.5
                if dist <= 2:
                    print(f"⚠️ A {m.name} is right next to you!")
    
    def _show_local_map(self, radius: int = 5):
        """Show small area around player"""
        player = self.world.player
        px, py = player.x, player.y
        
        tile_chars = {
            DungeonGenerator.FLOOR: '.',
            DungeonGenerator.WALL: '#',
            DungeonGenerator.DOOR: '+',
            DungeonGenerator.CORRIDOR: '·',
            DungeonGenerator.ROOM_FLOOR: '.',
            DungeonGenerator.ENTRANCE: '<',
            DungeonGenerator.EXIT: '>'
        }
        
        print("\n   ", end="")
        for dx in range(-radius, radius+1):
            print(f"{(px+dx) % 10}", end="")
        print()
        
        for dy in range(-radius, radius+1):
            y = py + dy
            print(f"{y:2} ", end="")
            
            for dx in range(-radius, radius+1):
                x = px + dx
                
                # Player
                if x == px and y == py:
                    print('@', end='')
                    continue
                
                # Out of bounds
                if not (0 <= x < self.world.width and 0 <= y < self.world.height):
                    print(' ', end='')
                    continue
                
                # Monster
                monster_here = None
                for m in self.world.monsters:
                    if m.x == x and m.y == y and m.stats.is_alive():
                        monster_here = m
                        break
                
                if monster_here:
                    print(monster_here.name[0].upper(), end='')
                    continue
                
                # Item
                if (x, y) in self.world.items_on_ground and self.world.items_on_ground[(x, y)]:
                    print('!', end='')
                    continue
                
                # Tile
                tile = self.world.dungeon.grid[y, x]
                print(tile_chars.get(tile, '?'), end='')
            
            print()
    
    def _get_direction(self, x1: int, y1: int, x2: int, y2: int) -> str:
        """Get cardinal direction from (x1,y1) to (x2,y2)"""
        dx = x2 - x1
        dy = y2 - y1
        
        if abs(dx) > abs(dy):
            return "to the east" if dx > 0 else "to the west"
        elif dy != 0:
            return "to the south" if dy > 0 else "to the north"
        else:
            return "right here"
    
    def cmd_pickup(self):
        """Pick up items at player's feet"""
        player = self.world.player
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground or not self.world.items_on_ground[pos]:
            print("📦 Nothing here to pick up.")
            return
        
        items = self.world.items_on_ground[pos]
        picked_up = []
        
        for item in items[:]:  # Copy list to iterate while modifying
            if player.inventory.add_object(item):
                items.remove(item)
                picked_up.append(item['name'])
            else:
                print(f"📦 Your inventory is full! Can't pick up {item['name']}.")
                break
        
        if picked_up:
            print(f"✅ Picked up: {', '.join(picked_up)}")
        
        # Clean up empty positions
        if not items:
            del self.world.items_on_ground[pos]
    
    def cmd_inventory(self):
        """Show player inventory"""
        player = self.world.player
        inv = player.inventory
        
        print("\n╔══════════════════════════════════════╗")
        print("║           INVENTORY                  ║")
        print("╠══════════════════════════════════════╣")
        
        # Essences
        print("║ 🔮 ESSENCES:                         ║")
        for elem, amount in inv.essences.items():
            bar = '█' * int(amount / 20) + '░' * (5 - int(amount / 20))
            print(f"║   {elem.capitalize():8} {bar} {amount:>6.0f}       ║")
        
        # Objects
        print("╠══════════════════════════════════════╣")
        print("║ 📦 OBJECTS:                          ║")
        if inv.objects:
            for i, obj in enumerate(inv.objects[:10]):  # Show first 10
                name = obj['name'][:25]
                print(f"║   {i+1:2}. {name:28} ║")
            if len(inv.objects) > 10:
                print(f"║   ... and {len(inv.objects)-10} more items          ║")
        else:
            print("║   (empty)                            ║")
        
        # Weight
        weight = inv.get_total_weight()
        print(f"╠══════════════════════════════════════╣")
        print(f"║ Weight: {weight:.1f} / {inv.max_weight:.1f}               ║")
        
        # Spells
        print("╠══════════════════════════════════════╣")
        print("║ 📖 KNOWN SPELLS:                     ║")
        for spell in inv.grimoire:
            print(f"║   • {spell:32} ║")
        
        print("╚══════════════════════════════════════╝")
    
    def cmd_stats(self):
        """Show player stats"""
        player = self.world.player
        s = player.stats
        
        print("\n╔══════════════════════════════════════╗")
        print(f"║  {player.name:^34}  ║")
        print("╠══════════════════════════════════════╣")
        
        # Health bar
        hp_pct = s.current_health / s.max_health
        hp_bar = '█' * int(hp_pct * 20) + '░' * (20 - int(hp_pct * 20))
        print(f"║ ❤️  HP: [{hp_bar}] {s.current_health:>3}/{s.max_health:<3}║")
        
        # Stamina bar
        st_pct = s.current_stamina / s.max_stamina
        st_bar = '█' * int(st_pct * 20) + '░' * (20 - int(st_pct * 20))
        print(f"║ ⚡ ST: [{st_bar}] {s.current_stamina:>3}/{s.max_stamina:<3}║")
        
        print("╠══════════════════════════════════════╣")
        print("║ ATTRIBUTES:                          ║")
        print(f"║   STR: {s.strength:2}  DEX: {s.dexterity:2}  CON: {s.constitution:2}       ║")
        print(f"║   INT: {s.intelligence:2}  WIS: {s.wisdom:2}  CHA: {s.charisma:2}       ║")
        print("╠══════════════════════════════════════╣")
        print("║ COMBAT:                              ║")
        print(f"║   Attack: {s.attack_power:2}   Defense: {s.defense:2}          ║")
        print(f"║   Magic:  {s.magic_power:2}   M.Def:   {s.magic_defense:2}          ║")
        print(f"║   Level:  {player.level:2}                          ║")
        print("╚══════════════════════════════════════╝")
    
    def cmd_attack(self):
        """Attack adjacent monster"""
        player = self.world.player
        
        # Find adjacent monster
        target = None
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            x, y = player.x + dx, player.y + dy
            entity = self.world.get_entity_at(x, y)
            if entity and entity != player and entity.stats.is_alive():
                target = entity
                break
        
        if not target:
            print("⚔️ No enemy in range. Move next to a monster to attack.")
            return
        
        # Attack!
        result = player.attack(target)
        
        if result['success']:
            print(f"⚔️ You strike the {target.name} for {result['damage']} damage!")
            print(f"   {target.name} HP: {target.stats.current_health}/{target.stats.max_health}")
            
            if not result['target_alive']:
                print(f"💀 The {target.name} is defeated!")
                # Drop loot
                self._drop_monster_loot(target)
        
        self.turn_count += 1
    
    def cmd_cast(self, spell_name: str = None):
        """Cast a spell"""
        player = self.world.player
        
        if not spell_name:
            print("🔮 Available spells:")
            for name, spell in self.spell_defs.items():
                cost = sum(spell['composition'].values())
                print(f"   • {name}: {spell['definition']} (cost: {cost} essence)")
            print("\nUse: cast <spell_name>")
            return
        
        spell_name = spell_name.lower()
        if spell_name not in self.spell_defs:
            print(f"❓ Unknown spell: {spell_name}")
            return
        
        spell = self.spell_defs[spell_name]
        
        # Find target for damage spells
        target = None
        if spell['spell_effect']['type'] == 'damage':
            # Find nearest monster
            nearest_dist = float('inf')
            for m in self.world.monsters:
                if m.stats.is_alive():
                    dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                    if dist < nearest_dist and dist <= 10:
                        nearest_dist = dist
                        target = m
            
            if not target:
                print("⚔️ No enemies in range (10 tiles).")
                return
        
        # Cast!
        print(f"\n🔮 Casting {spell_name.upper()}...")
        print(f"   Incanting: \"{spell['word']}\"")
        
        result = player.cast_spell(spell['synset'], spell, target=target)
        
        print(f"   🎲 Roll: {result.get('roll', '?')} vs DC {result.get('dc', '?')}")
        print(f"   Result: {result['result'].value}")
        
        if result['success']:
            if 'damage' in result:
                print(f"   ⚔️ {target.name} takes {result['damage']} damage!")
                print(f"   {target.name} HP: {target.stats.current_health}/{target.stats.max_health}")
                
                if not target.stats.is_alive():
                    print(f"   💀 The {target.name} is destroyed!")
                    self._drop_monster_loot(target)
            
            if 'healed' in result:
                print(f"   💚 You heal for {result['healed']} HP!")
                print(f"   HP: {player.stats.current_health}/{player.stats.max_health}")
            
            print(f"   💎 Essence spent: {result.get('essence_spent', {})}")
        else:
            if 'message' in result:
                print(f"   ❌ {result['message']}")
        
        self.turn_count += 1
    
    def cmd_drop(self, item_num: int = None):
        """Drop an item from inventory"""
        player = self.world.player
        inv = player.inventory
        
        if not inv.objects:
            print("📦 Your inventory is empty.")
            return
        
        if item_num is None:
            print("📦 Drop which item? (use: drop <number>)")
            for i, obj in enumerate(inv.objects[:10]):
                print(f"   {i+1}. {obj['name']}")
            return
        
        idx = item_num - 1
        if idx < 0 or idx >= len(inv.objects):
            print(f"❓ Invalid item number: {item_num}")
            return
        
        item = inv.objects.pop(idx)
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground:
            self.world.items_on_ground[pos] = []
        self.world.items_on_ground[pos].append(item)
        
        print(f"📦 Dropped {item['name']}.")
    
    def cmd_use(self, item_num: int = None):
        """Use an item (food heals, etc.)"""
        player = self.world.player
        inv = player.inventory
        
        if not inv.objects:
            print("📦 Your inventory is empty.")
            return
        
        if item_num is None:
            print("📦 Use which item? (use: use <number>)")
            for i, obj in enumerate(inv.objects[:10]):
                usable = "🍖" if obj.get('type') == 'food' else "📦"
                print(f"   {usable} {i+1}. {obj['name']}")
            return
        
        idx = item_num - 1
        if idx < 0 or idx >= len(inv.objects):
            print(f"❓ Invalid item number: {item_num}")
            return
        
        item = inv.objects[idx]
        
        # Food heals
        if item.get('type') == 'food':
            heal_amount = int(item.get('weight', 5) * 2)  # Weight-based healing
            heal_amount = max(5, min(50, heal_amount))  # Clamp 5-50
            
            player.stats.heal(heal_amount)
            inv.objects.pop(idx)
            
            print(f"🍖 You eat the {item['name']} and heal {heal_amount} HP!")
            print(f"   HP: {player.stats.current_health}/{player.stats.max_health}")
        
        # Gems give essence
        elif item.get('type') == 'gems':
            element = random.choice(['fire', 'water', 'earth', 'air'])
            amount = int(item.get('weight', 1) * 10)
            
            inv.add_essence(element, amount)
            inv.objects.pop(idx)
            
            print(f"💎 The {item['name']} dissolves into {amount} {element} essence!")
            print(f"   {element.capitalize()}: {inv.essences[element]:.0f}")
        
        # Liquids restore stamina
        elif item.get('type') == 'liquids':
            stamina = 25
            player.stats.restore_stamina(stamina)
            inv.objects.pop(idx)
            
            print(f"🧪 You drink the {item['name']} and restore {stamina} stamina!")
        
        else:
            print(f"❓ You can't figure out how to use the {item['name']}.")
    
    def cmd_map(self):
        """Show full dungeon map"""
        print("\n" + self.world.render())
        print("\nLegend: @ = You, # = Wall, . = Floor, ! = Item, < = Entrance, > = Exit")
        print("        Letters = Monsters (first letter of name)")
    
    def _drop_monster_loot(self, monster: Monster):
        """Drop random loot when monster dies"""
        pos = (monster.x, monster.y)
        
        # 50% chance to drop something
        if random.random() < 0.5:
            item = self.world.spawn_item(pos)
            print(f"   ✨ The {monster.name} dropped a {item['name']}!")
    
    def monster_turns(self):
        """Process monster AI"""
        player = self.world.player
        
        for monster in self.world.monsters:
            if not monster.stats.is_alive():
                continue
            
            dist = monster.distance_to(player)
            
            # If adjacent, attack
            if dist <= 1.5:
                result = monster.attack(player)
                if result['success']:
                    print(f"\n👹 The {monster.name} attacks you for {result['damage']} damage!")
                    print(f"   Your HP: {player.stats.current_health}/{player.stats.max_health}")
            
            # If close, move toward player
            elif dist < 10:
                # Simple movement toward player
                dx = 1 if player.x > monster.x else -1 if player.x < monster.x else 0
                dy = 1 if player.y > monster.y else -1 if player.y < monster.y else 0
                
                new_x, new_y = monster.x + dx, monster.y + dy
                
                # Check walkable and not occupied
                if self.world.is_walkable(new_x, new_y):
                    if not self.world.get_entity_at(new_x, new_y):
                        monster.x = new_x
                        monster.y = new_y
    
    def player_death(self):
        """Handle player death - beta test resurrection"""
        player = self.world.player
        
        print("\n" + "="*50)
        print("💀 YOU HAVE DIED! 💀")
        print("="*50)
        print("\n[BETA TEST MODE] Resurrecting in 3... 2... 1...")
        
        # Resurrect
        player.stats.current_health = player.stats.max_health
        player.stats.current_stamina = player.stats.max_stamina
        
        # Restore some essence
        for elem in player.inventory.essences:
            player.inventory.essences[elem] = max(50, player.inventory.essences[elem])
        
        # Move to entrance
        entrance = self.world.dungeon.find_positions(DungeonGenerator.ENTRANCE)
        if entrance:
            player.x, player.y = entrance[0]
        
        print("✨ You return to life at the dungeon entrance!")
        print(f"   HP: {player.stats.current_health}/{player.stats.max_health}")
        self.cmd_look()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Entry point"""
    # Parse args for seed
    seed = None
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            pass
    
    # Create world
    world = GameWorld(width=60, height=30, seed=seed)
    
    # Create and start engine
    engine = GameEngine(world)
    engine.start()


if __name__ == "__main__":
    main()
