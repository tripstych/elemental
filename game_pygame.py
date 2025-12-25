"""
Elemental RPG - Pygame GUI Version
WASD controls, visual dungeon rendering, real-time gameplay
"""

import sys
import os
import random
import json
from datetime import datetime
import pygame

# Add seed directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'seed'))

from seed.dungeon_generator import DungeonGenerator
from seed.pathfinding import Pathfinder

# Import from the original game
from game import GameWorld
from game_api import GameSession, GameAPIClient

# ============================================================================
# CONSTANTS
# ============================================================================

# Window settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Tile sizes
TILE_SIZE = 24

# Difficulty: 0.5 = easy, 1.0 = normal, 2.0 = hard
TOUGHNESS = 0.8

SPAWN_MONSTERS = 15

SPAWN_SOLVENTS = 15

# Solvents for alchemy
SOLVENTS = {
    "aqua_ignis": {
        "name": "Aqua Ignis",
        "extracts": ["fire", "air"],
        "strength": 0.8,
        "description": "Boiling alchemical water",
    },
    "oleum_terra": {
        "name": "Oleum Terra", 
        "extracts": ["earth", "water"],
        "strength": 0.9,
        "description": "Thick mineral oil",
    },
    "alkahest": {
        "name": "Alkahest",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal solvent",
    },
}

# Material essence values for dissolution
MATERIAL_ESSENCES = {
    'weapons': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'tools': {'fire': 20, 'water': 10, 'earth': 35, 'air': 10},
    'gems': {'fire': 30, 'water': 20, 'earth': 30, 'air': 20},
    'food': {'fire': 10, 'water': 40, 'earth': 20, 'air': 5},
    'liquids': {'fire': 5, 'water': 50, 'earth': 5, 'air': 15},
    'default': {'fire': 15, 'water': 15, 'earth': 15, 'air': 15},
}

# Colors
COLORS = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'gray': (128, 128, 128),
    'dark_gray': (64, 64, 64),
    'light_gray': (192, 192, 192),
    'red': (255, 0, 0),
    'dark_red': (139, 0, 0),
    'green': (0, 255, 0),
    'dark_green': (0, 100, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'orange': (255, 165, 0),
    'purple': (128, 0, 128),
    'cyan': (0, 255, 255),
    'brown': (139, 69, 19),
    'floor': (60, 50, 40),
    'wall': (40, 35, 30),
    'corridor': (50, 45, 35),
    'door': (139, 90, 43),
    'entrance': (100, 200, 100),
    'exit': (200, 100, 100),
    'player': (0, 150, 255),
    'monster': (200, 50, 50),
    'item': (255, 215, 0),
    'ui_bg': (30, 30, 40),
    'ui_border': (80, 80, 100),
    'hp_bar': (200, 50, 50),
    'stamina_bar': (50, 150, 200),
    'essence_fire': (255, 100, 50),
    'essence_water': (50, 150, 255),
    'essence_earth': (139, 90, 43),
    'essence_air': (200, 200, 255),
}

# ============================================================================
# PYGAME GAME CLASS
# ============================================================================

class PygameGame:
    """
    Pygame-based GUI for Elemental RPG
    """
    
    def __init__(self, seed: int = None):
        pygame.init()
        pygame.display.set_caption("Elemental RPG")
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 18)
        self.spawn_solvents = SPAWN_SOLVENTS
        self.spawn_monsters = SPAWN_MONSTERS
        
        # Game state
        self.running = True
        self.paused = False
        self.show_full_map = False
        self.messages = []
        self.max_messages = 8
        self.turn = 0
        
        # Action logging
        self.log_file = f"game_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.action_log = []
        
        # Create game world
        self.world = GameWorld(width=60, height=30, seed=seed)
        self.world.spawn_player("Hero")
        
        # Buff player for better combat feel
        player = self.world.player
        player.stats.attack_power = 20
        player.stats.magic_power = 18
        player.stats.defense = 12
        
        # Spawn monsters - stats scaled by TOUGHNESS
        for _ in range(self.spawn_monsters):
            m = self.world.spawn_monster(near_player=True)
            # Base monster stats scaled by toughness
            m.stats.max_health = int(40 * TOUGHNESS)
            m.stats.current_health = m.stats.max_health
            m.stats.attack_power = int(10 * TOUGHNESS)
            m.stats.defense = int(6 * TOUGHNESS)
        self.world.scatter_items(20)
        
        # Spawn solvents throughout the dungeon
        self.spawn_solvents(self.spawn_solvents)
        
        # Initialize pathfinding
        self.pathfinder = Pathfinder(
            self.world.dungeon.grid,
            walkable_tiles={DungeonGenerator.ROOM_FLOOR, DungeonGenerator.CORRIDOR, DungeonGenerator.EXIT}
        )
        
        # Override pathfinder's is_valid_position to check entities
        def is_valid_with_entities(x, y):
            # Check bounds first
            if not (0 <= x < self.world.width and 0 <= y < self.world.height):
                return False
            # Check if tile is walkable
            if not self.pathfinder.is_walkable(self.world.dungeon.grid[y, x]):
                return False
            # Check if entity blocks position (except player)
            entity = self.world.get_entity_at(x, y)
            return entity is None or entity == self.world.player
        self.pathfinder.is_valid_position = is_valid_with_entities
        
        # Pathfinding state
        self.path = []
        self.target_pos = None
        self.path_mode = False  # False=WASD, True=click-to-move
        
        # Dissolution interface state
        self.dissolve_mode = False
        self.selected_item = None
        self.selected_solvent = None
        
        # Camera position (centered on player)
        self.camera_x = 0
        self.camera_y = 0
        
        # Viewport dimensions (in tiles)
        self.viewport_width = 32
        self.viewport_height = 22
        
        # UI dimensions
        self.game_area_width = self.viewport_width * TILE_SIZE
        self.game_area_height = self.viewport_height * TILE_SIZE
        self.sidebar_width = SCREEN_WIDTH - self.game_area_width - 20
        
        # Spell definitions (from GameEngine)
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
        
        # Key repeat settings
        pygame.key.set_repeat(200, 100)
        
        self.add_message("Welcome to the dungeon!")
        self.add_message("WASD=move, SPACE=attack, E=pickup")
        self.add_message("1=Fireball, 2=Heal, 3=Dissolve item")
    
    def add_message(self, msg: str):
        """Add a message to the log"""
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
    
    def log_action(self, action: str, details: dict = None):
        """Log a player action to JSON"""
        player = self.world.player
        entry = {
            'turn': self.turn,
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'player': {
                'pos': f"({player.x},{player.y})",
                'hp': f"{player.stats.current_health}/{player.stats.max_health}",
                'level': player.level,
            },
            'visible': self.get_visible_info(radius=10),
        }
        if details:
            entry['details'] = details
        self.action_log.append(entry)
    
    def save_log(self):
        """Save action log to JSON file"""
        with open(self.log_file, 'w') as f:
            json.dump({
                'game_seed': self.world.seed,
                'total_turns': self.turn,
                'actions': self.action_log
            }, f, indent=2)
    
    def spawn_solvents(self, count: int):
        """Spawn solvent items in the dungeon"""
        solvent_types = [
            ('aqua_ignis', 'Aqua Ignis', 'Extracts fire & air'),
            ('oleum_terra', 'Oleum Terra', 'Extracts earth & water'),
            ('alkahest', 'Alkahest', 'Universal solvent'),
        ]
        
        floors = (self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) +
                  self.world.dungeon.find_positions(DungeonGenerator.CORRIDOR))
        
        for _ in range(count):
            if not floors:
                break
            pos = random.choice(floors)
            solvent_key, name, desc = random.choice(solvent_types)
            
            solvent_item = {
                'name': name,
                'type': 'solvent',
                'is_solvent': True,
                'solvent_type': solvent_key,
                'description': desc,
                'weight': 0.5,
            }
            
            if pos not in self.world.items_on_ground:
                self.world.items_on_ground[pos] = []
            self.world.items_on_ground[pos].append(solvent_item)
    
    def update_camera(self):
        """Center camera on player"""
        player = self.world.player
        self.camera_x = player.x - self.viewport_width // 2
        self.camera_y = player.y - self.viewport_height // 2
        
        # Clamp to world bounds
        self.camera_x = max(0, min(self.camera_x, self.world.width - self.viewport_width))
        self.camera_y = max(0, min(self.camera_y, self.world.height - self.viewport_height))
    
    def handle_events(self):
        """Process input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.path_mode:
                    print("-"*10)
                    print(f"Event type:{event.type} Path: {self.path}  Path mode:{self.path_mode}")
                    print("Automove Initiated")
                    self.auto_move_path()
                else:
                    self.handle_keydown(event)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.handle_mouse_click(event)
                    if self.path_mode: 
                        self.auto_move_path()
                elif event.button == 3:  # Right click
                    self.enable_path_mode()
            
            # Handle auto-move timer
            elif event.type == pygame.USEREVENT + 1:
                if self.path_mode and self.path:
                    self.auto_move_path()
                else:
                    pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Stop timer
    
    def handle_keydown(self, event):
        """Handle key press"""
        player = self.world.player
        
        if not player.stats.is_alive():
            # Respawn on any key
            self.respawn_player()
            return
        
        # Toggle path mode with 'P'
        if event.key == pygame.K_p:
            self.toggle_path_mode()
            return
        
        # Toggle dissolve mode with 'F'
        if event.key == pygame.K_f:
            self.toggle_dissolve_mode()
            return
        
        # Handle dissolve mode selections
        if self.dissolve_mode:
            # Number keys for item/solvent selection
            if pygame.K_1 <= event.key <= pygame.K_9:
                index = event.key - pygame.K_1  # 0-based index
                
                if not self.selected_item:
                    # Select item
                    items = [obj for obj in player.inventory.objects if not obj.get('is_solvent')]
                    if index < len(items):
                        self.selected_item = items[index]
                        self.add_message(f"Selected item: {self.selected_item['name']}")
                        self.add_message("Now select solvent (1-9)")
                    else:
                        self.add_message("No item at that slot!")
                elif not self.selected_solvent:
                    # Select solvent
                    solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
                    if index < len(solvents):
                        self.selected_solvent = solvents[index]
                        self.add_message(f"Selected solvent: {self.selected_solvent['name']}")
                        # Perform dissolution
                        self.perform_dissolution()
                    else:
                        self.add_message("No solvent at that slot!")
                return
            # ESC to cancel dissolve mode
            elif event.key == pygame.K_ESCAPE:
                self.dissolve_mode = False
                self.selected_item = None
                self.selected_solvent = None
                self.add_message("Dissolve cancelled")
                return
        
        moved = False
        
        # WASD Movement
        if event.key == pygame.K_w or event.key == pygame.K_UP:
            moved = self.try_move(0, -1)
        elif event.key == pygame.K_s or event.key == pygame.K_DOWN:
            moved = self.try_move(0, 1)
        elif event.key == pygame.K_a or event.key == pygame.K_LEFT:
            moved = self.try_move(-1, 0)
        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
            moved = self.try_move(1, 0)
        
        # Attack (Space)
        elif event.key == pygame.K_SPACE:
            self.do_attack()
            moved = True
        
        # Pickup (E or G)
        elif event.key == pygame.K_e or event.key == pygame.K_g:
            self.do_pickup()
        
        # Spells (1 = Fireball, 2 = Heal)
        elif event.key == pygame.K_1:
            self.cast_spell('fireball')
            moved = True
        elif event.key == pygame.K_2:
            self.cast_spell('heal')
            moved = True
        
        # Dissolve item (3)
        elif event.key == pygame.K_3:
            self.dissolve_item()
        
        # Map toggle (M)
        elif event.key == pygame.K_m:
            self.show_full_map = not self.show_full_map
        
        # Inventory (I)
        elif event.key == pygame.K_i:
            self.show_inventory()
        
        # Quit (Escape)
        elif event.key == pygame.K_ESCAPE:
            self.running = False
        
        # Wait (Period)
        elif event.key == pygame.K_PERIOD:
            self.add_message("You wait...")
            moved = True
        
        # Monster turns after player action
        if moved:
            self.monster_turns()
    
    def toggle_dissolve_mode(self):
        """Toggle dissolution interface mode"""
        self.dissolve_mode = not self.dissolve_mode
        if self.dissolve_mode:
            self.selected_item = None
            self.selected_solvent = None
            self.add_message("Dissolve mode: Select item (1-9) then solvent (1-9)")
        else:
            self.add_message("Dissolve mode: OFF")
    
    def enable_path_mode(self):
        self.path_mode = True
        self.path = []
        self.target_pos = None
        mode = "Pathfinding"
        self.add_message(f"Movement mode: {mode}")
 
    def toggle_path_mode(self):
        """Toggle between WASD and click-to-move modes"""
        self.path_mode = not self.path_mode
        self.path = []
        self.target_pos = None
        mode = "Pathfinding" if self.path_mode else "WASD"
        self.add_message(f"Movement mode: {mode}")
    
    def handle_mouse_click(self, event):
        """Handle mouse click for pathfinding"""
        if not self.path_mode:
            return
        
        # Convert mouse position to world coordinates
        mouse_x, mouse_y = event.pos
        
        # Convert to tile coordinates
        tile_x = mouse_x // TILE_SIZE + self.camera_x
        tile_y = mouse_y // TILE_SIZE + self.camera_y
        
        # Check if position is valid
        if not self.world.is_walkable(tile_x, tile_y):
            self.add_message("Cannot move there!")
            return
        
        player = self.world.player
        start_pos = (player.x, player.y)
        goal_pos = (tile_x, tile_y)
        
        # Find path
        path = self.pathfinder.astar(start_pos, goal_pos)
        
        if path:
            # Remove the starting position (player is already there)
            self.path = path[1:] if len(path) > 1 else []
            self.target_pos = goal_pos
            
            rel_pos = self.get_relative_pos(tile_x, tile_y)
            self.add_message(f"Path to {rel_pos} ({len(self.path)} steps)")
        else:
            self.add_message("No path found!")
            self.path = []
            self.target_pos = None
    
    def move_along_path(self, auto_continue: bool = False) -> bool:
        """Move one step along the current path"""
        if not self.path:
            return False
        
        # Get next step
        next_x, next_y = self.path[0]
        
        # Try to move there
        player = self.world.player
        dx = next_x - player.x
        dy = next_y - player.y
        
        moved = self.try_move(dx, dy)
        
        if moved:
            # Remove the step we just took
            self.path.pop(0)
            
            # Check if we reached the target
            if not self.path:
                self.add_message("Reached destination!")
                self.target_pos = None
            elif auto_continue:
                # Continue moving automatically after delay
                pygame.time.set_timer(pygame.USEREVENT + 1, 500)  # 500ms delay
        
        return moved
    
    def auto_move_path(self):
        """Start automatic movement along path"""
        print("MAP value",self.move_along_path(auto_continue=True))
        if self.path and self.move_along_path(auto_continue=True):
            print("Starting automove")
            self.monster_turns()
    
    def try_move(self, dx: int, dy: int) -> bool:
        """Try to move player in direction"""
        player = self.world.player
        new_x = player.x + dx
        new_y = player.y + dy
        direction = {(0,-1): 'n', (0,1): 's', (1,0): 'e', (-1,0): 'w'}.get((dx, dy), '?')
        
        # Check for entity blocking movement
        entity = self.world.get_entity_at(new_x, new_y)
        if entity and entity != player:
            # Can't walk through entities - they're like walls
            return False
        
        # Check walkable
        if not self.world.is_walkable(new_x, new_y):
            return False
        
        # Move
        player.x = new_x
        player.y = new_y
        self.turn += 1
        self.log_action('move', {'direction': direction, 'to': f"({new_x},{new_y})"})
        
        # Check for items
        pos = (new_x, new_y)
        if pos in self.world.items_on_ground and self.world.items_on_ground[pos]:
            items = self.world.items_on_ground[pos]
            if len(items) == 1:
                self.add_message(f"You see a {items[0]['name']} here. (E to pickup)")
            else:
                self.add_message(f"You see {len(items)} items here. (E to pickup)")
        
        # Check for exit
        if self.world.dungeon.grid[new_y, new_x] == DungeonGenerator.EXIT:
            self.add_message("You found the exit! (Next level coming soon)")
        
        return True
    
    def do_attack(self):
        """Attack adjacent monster (including diagonals)"""
        player = self.world.player
        
        # Find adjacent monster (8 directions including diagonals)
        for dx, dy in [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]:
            x, y = player.x + dx, player.y + dy
            entity = self.world.get_entity_at(x, y)
            if entity and entity != player and entity.stats.is_alive():
                result = player.attack(entity)
                if result['success']:
                    # Determine direction for logging
                    direction = {(0,-1):'n', (1,-1):'ne', (1,0):'e', (1,1):'se', 
                                (0,1):'s', (-1,1):'sw', (-1,0):'w', (-1,-1):'nw'}.get((dx, dy), '?')
                    self.add_message(f"You hit {entity.name} {direction} for {result['damage']} damage!")
                    self.turn += 1
                    self.log_action('attack', {
                        'target': entity.name,
                        'direction': direction,
                        'damage': result['damage'],
                        'target_hp': f"{entity.stats.current_health}/{entity.stats.max_health}",
                        'killed': not result['target_alive']
                    })
                    if not result['target_alive']:
                        self.add_message(f"{entity.name} is defeated!")
                        self.drop_monster_loot(entity)
                return
        
        self.add_message("Nothing to attack nearby.")
    
    def do_pickup(self):
        """Pick up items at player's feet"""
        player = self.world.player
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground or not self.world.items_on_ground[pos]:
            self.add_message("Nothing here to pick up.")
            return
        
        items = self.world.items_on_ground[pos]
        picked = []
        for item in items[:]:
            if player.inventory.add_object(item):
                items.remove(item)
                picked.append(item['name'])
                self.add_message(f"Picked up {item['name']}")
            else:
                self.add_message("Inventory full!")
                break
        
        if picked:
            self.log_action('pickup', {'items': picked})
        
        if not items:
            del self.world.items_on_ground[pos]
    
    def cast_spell(self, spell_name: str):
        """Cast a spell"""
        player = self.world.player
        
        if spell_name not in self.spell_defs:
            self.add_message(f"Unknown spell: {spell_name}")
            return
        
        spell = self.spell_defs[spell_name]
        
        # Find target for damage spells
        target = None
        if spell['spell_effect']['type'] == 'damage':
            # Calculate fireball range based on magic power
            fireball_range = 3 + int(player.stats.magic_power / 10)  # Base 3 tiles + 1 per 10 magic power
            
            nearest_dist = float('inf')
            for m in self.world.monsters:
                if m.stats.is_alive():
                    dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                    if dist < nearest_dist and dist <= fireball_range:
                        nearest_dist = dist
                        target = m
            
            if not target:
                self.add_message(f"No enemies in range! (Fireball range: {fireball_range} tiles)")
                return
        
        # Cast
        result = player.cast_spell(spell['synset'], spell, target=target)
        
        if result['success']:
            # Show essence spent
            spent = result.get('essence_spent', spell.get('composition', {}))
            spent_str = ", ".join(f"{e[:1].upper()}:{int(v)}" for e, v in spent.items() if v > 0)
            
            log_details = {'spell': spell_name, 'cost': spent}
            
            if 'damage' in result:
                self.add_message(f"{spell_name.upper()} hits {target.name} for {result['damage']} damage!")
                log_details['target'] = target.name
                log_details['damage'] = result['damage']
                log_details['killed'] = not target.stats.is_alive()
                if not target.stats.is_alive():
                    self.add_message(f"{target.name} is destroyed!")
                    self.drop_monster_loot(target)
            if 'healed' in result:
                self.add_message(f"HEAL restores {result['healed']} HP!")
                log_details['healed'] = result['healed']
            
            self.turn += 1
            self.log_action('cast', log_details)
            
            # Show remaining essence
            ess = player.inventory.essences
            self.add_message(f"Spent: {spent_str} | F:{int(ess['fire'])} W:{int(ess['water'])} E:{int(ess['earth'])} A:{int(ess['air'])}")
        else:
            self.add_message(f"Spell failed: {result.get('message', result.get('reason', 'not enough essence'))}")
    
    def perform_dissolution(self):
        """Perform dissolution with selected item and solvent"""
        if not self.selected_item or not self.selected_solvent:
            return
        
        player = self.world.player
        inv = player.inventory
        
        # Get solvent properties
        solvent_key = self.selected_solvent.get('solvent_type', 'alkahest')
        solvent_data = SOLVENTS.get(solvent_key, SOLVENTS['alkahest'])
        
        # Get item's material essence
        item_type = self.selected_item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])
        
        # Extract essences based on solvent
        extracted = {}
        for elem in solvent_data['extracts']:
            amount = base_essence.get(elem, 10) * solvent_data['strength']
            extracted[elem] = amount
            inv.add_essence(elem, amount)
        
        # Remove both items
        inv.objects.remove(self.selected_item)
        inv.objects.remove(self.selected_solvent)
        
        # Report results
        extracted_str = ", ".join(f"{elem[:1].upper()}:{int(amount)}" for elem, amount in extracted.items())
        self.add_message(f"Dissolved {self.selected_item['name']} with {self.selected_solvent['name']}!")
        self.add_message(f"Extracted: {extracted_str}")
        self.log_action('dissolve', {
            'item': self.selected_item['name'],
            'solvent': self.selected_solvent['name'],
            'extracted': extracted
        })
        
        # Reset dissolve mode
        self.dissolve_mode = False
        self.selected_item = None
        self.selected_solvent = None
        self.add_message("Dissolve complete!")
    
    def dissolve_item(self):
        """Legacy dissolve method - uses dissolve mode now"""
        self.toggle_dissolve_mode()
    
    def drop_monster_loot(self, monster):
        """Drop loot when monster dies and award XP"""
        player = self.world.player
        pos = (monster.x, monster.y)
        
        # Award XP (20-40 based on monster)
        xp_award = 20 + hash(monster.name) % 21
        result = player.gain_xp(xp_award)
        self.add_message(f"+{xp_award} XP!")
        
        if result['leveled_up']:
            self.add_message(f"LEVEL UP! Now level {result['new_level']}!")
            self.add_message(f"Essence capacity: {int(result['new_max_essence'])}")
        
        # Drop loot
        if random.random() < 0.5:
            item = self.world.spawn_item(pos)
            self.add_message(f"{monster.name} dropped {item['name']}!")
    
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
                    self.add_message(f"{monster.name} hits you for {result['damage']} damage!")
                    if not player.stats.is_alive():
                        self.add_message("You have died! Press any key to respawn.")
            
            # If close, move toward player
            elif dist < 10:
                dx = 1 if player.x > monster.x else -1 if player.x < monster.x else 0
                dy = 1 if player.y > monster.y else -1 if player.y < monster.y else 0
                
                new_x, new_y = monster.x + dx, monster.y + dy
                
                # Check if position is walkable and not blocked by any entity
                if self.world.is_walkable(new_x, new_y):
                    blocking_entity = self.world.get_entity_at(new_x, new_y)
                    if not blocking_entity:
                        monster.x = new_x
                        monster.y = new_y
    
    def respawn_player(self):
        """Respawn player after death"""
        player = self.world.player
        player.stats.current_health = player.stats.max_health
        player.stats.current_stamina = player.stats.max_stamina
        
        for elem in player.inventory.essences:
            player.inventory.essences[elem] = max(50, player.inventory.essences[elem])
        
        entrance = self.world.dungeon.find_positions(DungeonGenerator.ENTRANCE)
        if entrance:
            player.x, player.y = entrance[0]
        
        self.add_message("You respawn at the entrance!")
    
    def show_inventory(self):
        """Toggle inventory display"""
        inv = self.world.player.inventory
        if inv.objects:
            items = ", ".join(obj['name'] for obj in inv.objects[:5])
            if len(inv.objects) > 5:
                items += f" (+{len(inv.objects)-5} more)"
            self.add_message(f"Inventory: {items}")
        else:
            self.add_message("Inventory is empty.")
    
    def get_relative_pos(self, target_x: int, target_y: int) -> str:
        """
        Get relative position string like 'n3e4' (3 north, 4 east).
        Returns 'here' if same position as player.
        """
        player = self.world.player
        dx = target_x - player.x
        dy = target_y - player.y
        
        if dx == 0 and dy == 0:
            return "here"
        
        parts = []
        if dy < 0:
            parts.append(f"n{abs(dy)}")
        elif dy > 0:
            parts.append(f"s{dy}")
        
        if dx > 0:
            parts.append(f"e{dx}")
        elif dx < 0:
            parts.append(f"w{abs(dx)}")
        
        return "".join(parts)
    
    def get_visible_info(self, radius: int = 10) -> dict:
        """
        Get all visible entities and items with relative positions.
        Returns dict with 'monsters' and 'items' lists.
        Format: "Goblin:n3e2" means Goblin is 3 north, 2 east
        """
        player = self.world.player
        fov = self.world.get_player_fov(radius)
        
        # Visible monsters with relative positions
        monsters = []
        for m in self.world.monsters:
            if m.stats.is_alive() and (m.x, m.y) in fov:
                rel_pos = self.get_relative_pos(m.x, m.y)
                dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                monsters.append({
                    'name': m.name,
                    'pos': rel_pos,
                    'formatted': f"{m.name}:{rel_pos}",
                    'hp': m.stats.current_health,
                    'max_hp': m.stats.max_health,
                    'distance': round(dist, 1),
                    'adjacent': dist <= 1.5,
                })
        
        # Visible items with relative positions
        items = []
        for pos, item_list in self.world.items_on_ground.items():
            if pos in fov and item_list:
                rel_pos = self.get_relative_pos(pos[0], pos[1])
                dist = ((pos[0] - player.x)**2 + (pos[1] - player.y)**2)**0.5
                for item in item_list:
                    items.append({
                        'name': item['name'],
                        'type': item.get('type', 'misc'),
                        'pos': rel_pos,
                        'formatted': f"{item['name']}:{rel_pos}",
                        'distance': round(dist, 1),
                    })
        
        # Sort by distance
        monsters.sort(key=lambda x: x['distance'])
        items.sort(key=lambda x: x['distance'])
        
        return {'monsters': monsters, 'items': items}
    
    def render(self):
        """Render the game"""
        self.screen.fill(COLORS['black'])
        
        self.update_camera()
        
        # Draw game area
        self.render_dungeon()
        self.render_entities()
        self.render_items()
        
        # Draw UI
        self.render_sidebar()
        self.render_messages()
        self.render_controls()
        
        pygame.display.flip()
    
    def render_dungeon(self):
        """Render dungeon tiles"""
        tile_colors = {
            DungeonGenerator.FLOOR: COLORS['floor'],
            DungeonGenerator.WALL: COLORS['wall'],
            DungeonGenerator.DOOR: COLORS['door'],
            DungeonGenerator.CORRIDOR: COLORS['corridor'],
            DungeonGenerator.ROOM_FLOOR: COLORS['floor'],
            DungeonGenerator.ENTRANCE: COLORS['entrance'],
            DungeonGenerator.EXIT: COLORS['exit'],
        }
        
        for screen_y in range(self.viewport_height):
            for screen_x in range(self.viewport_width):
                world_x = self.camera_x + screen_x
                world_y = self.camera_y + screen_y
                
                if 0 <= world_x < self.world.width and 0 <= world_y < self.world.height:
                    tile = self.world.dungeon.grid[world_y, world_x]
                    color = tile_colors.get(tile, COLORS['black'])
                    
                    rect = pygame.Rect(
                        10 + screen_x * TILE_SIZE,
                        10 + screen_y * TILE_SIZE,
                        TILE_SIZE - 1,
                        TILE_SIZE - 1
                    )
                    pygame.draw.rect(self.screen, color, rect)
                    
                    # Draw wall borders
                    if tile == DungeonGenerator.WALL:
                        pygame.draw.rect(self.screen, COLORS['dark_gray'], rect, 1)
                    
                    # Draw path if in pathfinding mode
                    if self.path_mode and (world_x, world_y) in self.path:
                        pygame.draw.rect(self.screen, COLORS['yellow'], rect, 2)
                    
                    # Draw target position
                    if self.target_pos and (world_x, world_y) == self.target_pos:
                        pygame.draw.rect(self.screen, COLORS['green'], rect, 3)
    
    def render_entities(self):
        """Render player and monsters"""
        player = self.world.player
        
        # Player
        if self.camera_x <= player.x < self.camera_x + self.viewport_width and \
           self.camera_y <= player.y < self.camera_y + self.viewport_height:
            screen_x = (player.x - self.camera_x) * TILE_SIZE + 10
            screen_y = (player.y - self.camera_y) * TILE_SIZE + 10
            
            # Player circle
            center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
            pygame.draw.circle(self.screen, COLORS['player'], center, TILE_SIZE // 2 - 2)
            pygame.draw.circle(self.screen, COLORS['white'], center, TILE_SIZE // 2 - 2, 2)
            
            # @ symbol
            text = self.font.render("@", True, COLORS['white'])
            text_rect = text.get_rect(center=center)
            self.screen.blit(text, text_rect)
        
        # Monsters
        for monster in self.world.monsters:
            if not monster.stats.is_alive():
                continue
            
            if self.camera_x <= monster.x < self.camera_x + self.viewport_width and \
               self.camera_y <= monster.y < self.camera_y + self.viewport_height:
                screen_x = (monster.x - self.camera_x) * TILE_SIZE + 10
                screen_y = (monster.y - self.camera_y) * TILE_SIZE + 10
                
                # Monster circle
                center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
                pygame.draw.circle(self.screen, COLORS['monster'], center, TILE_SIZE // 2 - 2)
                pygame.draw.circle(self.screen, COLORS['dark_red'], center, TILE_SIZE // 2 - 2, 2)
                
                # First letter
                text = self.font.render(monster.name[0].upper(), True, COLORS['white'])
                text_rect = text.get_rect(center=center)
                self.screen.blit(text, text_rect)
                
                # Health bar above monster
                hp_pct = monster.stats.current_health / monster.stats.max_health
                bar_width = TILE_SIZE - 4
                bar_rect = pygame.Rect(screen_x + 2, screen_y - 4, int(bar_width * hp_pct), 3)
                bg_rect = pygame.Rect(screen_x + 2, screen_y - 4, bar_width, 3)
                pygame.draw.rect(self.screen, COLORS['dark_red'], bg_rect)
                pygame.draw.rect(self.screen, COLORS['red'], bar_rect)
    
    def render_items(self):
        """Render items on ground"""
        for pos, items in self.world.items_on_ground.items():
            if not items:
                continue
            
            x, y = pos
            if self.camera_x <= x < self.camera_x + self.viewport_width and \
               self.camera_y <= y < self.camera_y + self.viewport_height:
                screen_x = (x - self.camera_x) * TILE_SIZE + 10
                screen_y = (y - self.camera_y) * TILE_SIZE + 10
                
                # Item diamond
                center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
                points = [
                    (center[0], center[1] - 6),
                    (center[0] + 6, center[1]),
                    (center[0], center[1] + 6),
                    (center[0] - 6, center[1]),
                ]
                pygame.draw.polygon(self.screen, COLORS['item'], points)
                pygame.draw.polygon(self.screen, COLORS['orange'], points, 1)
    
    def render_sidebar(self):
        """Render right sidebar with stats"""
        sidebar_x = self.game_area_width + 20
        y = 10
        
        # Background
        sidebar_rect = pygame.Rect(sidebar_x, 0, self.sidebar_width, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, COLORS['ui_bg'], sidebar_rect)
        pygame.draw.rect(self.screen, COLORS['ui_border'], sidebar_rect, 2)
        
        player = self.world.player
        
        # Player name
        title = self.font_large.render(player.name, True, COLORS['white'])
        self.screen.blit(title, (sidebar_x + 10, y))
        y += 40
        
        # Health bar
        self.render_bar(sidebar_x + 10, y, "HP", 
                       player.stats.current_health, player.stats.max_health,
                       COLORS['hp_bar'], COLORS['dark_red'])
        y += 30
        
        # Stamina bar
        self.render_bar(sidebar_x + 10, y, "ST",
                       player.stats.current_stamina, player.stats.max_stamina,
                       COLORS['stamina_bar'], COLORS['blue'])
        y += 40
        
        # Essences
        essence_label = self.font.render("ESSENCES", True, COLORS['white'])
        self.screen.blit(essence_label, (sidebar_x + 10, y))
        y += 25
        
        essence_colors = {
            'fire': COLORS['essence_fire'],
            'water': COLORS['essence_water'],
            'earth': COLORS['essence_earth'],
            'air': COLORS['essence_air'],
        }
        
        max_ess = player.inventory.max_essence
        for elem, amount in player.inventory.essences.items():
            color = essence_colors.get(elem, COLORS['white'])
            self.render_bar(sidebar_x + 10, y, elem[:3].upper(),
                           amount, max_ess, color, COLORS['dark_gray'], bar_width=150)
            y += 22
        
        y += 20
        
        # Stats
        stats_label = self.font.render("STATS", True, COLORS['white'])
        self.screen.blit(stats_label, (sidebar_x + 10, y))
        y += 25
        
        s = player.stats
        xp_to_next = player.xp_for_next_level()
        stats_text = [
            f"Level: {player.level}  XP: {player.experience}/{player.level * 100}",
            f"STR: {s.strength}  DEX: {s.dexterity}",
            f"CON: {s.constitution}  INT: {s.intelligence}",
            f"ATK: {s.attack_power}  DEF: {s.defense}",
        ]
        for line in stats_text:
            text = self.font_small.render(line, True, COLORS['light_gray'])
            self.screen.blit(text, (sidebar_x + 10, y))
            y += 18
        
        y += 20
        
        # Inventory
        inv_label = self.font.render("INVENTORY", True, COLORS['white'])
        self.screen.blit(inv_label, (sidebar_x + 10, y))
        y += 25
        
        if player.inventory.objects:
            # Separate items and solvents for display
            items = [obj for obj in player.inventory.objects if not obj.get('is_solvent')]
            solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
            
            # Show regular items
            if items:
                for i, item in enumerate(items[:8]):  # Show first 8 items
                    # Item name with type color
                    type_colors = {
                        'weapon': COLORS['orange'],
                        'armor': COLORS['blue'], 
                        'potion': COLORS['green'],
                        'scroll': COLORS['purple'],
                        'essence': COLORS['cyan']
                    }
                    color = type_colors.get(item.get('type', ''), COLORS['light_gray'])
                    
                    # Highlight if selected in dissolve mode
                    if self.dissolve_mode and self.selected_item == item:
                        item_text = f"> {i+1}. {item['name']} <"
                        color = COLORS['yellow']
                    else:
                        item_text = f"{i+1}. {item['name']}"
                    
                    text = self.font_small.render(item_text, True, color)
                    self.screen.blit(text, (sidebar_x + 10, y))
                    y += 18
                
                if len(items) > 8:
                    more_text = f"...and {len(items) - 8} more items"
                    text = self.font_small.render(more_text, True, COLORS['gray'])
                    self.screen.blit(text, (sidebar_x + 10, y))
                    y += 18
            
            # Show solvents
            if solvents:
                y += 5
                solvent_label = self.font_small.render("SOLVENTS:", True, COLORS['yellow'])
                self.screen.blit(solvent_label, (sidebar_x + 10, y))
                y += 18
                
                for i, solvent in enumerate(solvents[:4]):  # Show first 4 solvents
                    # Highlight if selected in dissolve mode
                    if self.dissolve_mode and self.selected_solvent == solvent:
                        solvent_text = f"> {i+1}. {solvent['name']} <"
                        color = COLORS['yellow']
                    else:
                        solvent_text = f"{i+1}. {solvent['name']}"
                        color = COLORS['yellow']
                    
                    text = self.font_small.render(solvent_text, True, color)
                    self.screen.blit(text, (sidebar_x + 10, y))
                    y += 18
                
                if len(solvents) > 4:
                    more_text = f"...and {len(solvents) - 4} more solvents"
                    text = self.font_small.render(more_text, True, COLORS['gray'])
                    self.screen.blit(text, (sidebar_x + 10, y))
                    y += 18
        else:
            empty_text = self.font_small.render("Empty", True, COLORS['gray'])
            self.screen.blit(empty_text, (sidebar_x + 10, y))
            y += 18
        
        y += 15
        
        # Movement mode
        mode_color = COLORS['green'] if self.path_mode else COLORS['white']
        mode_text = f"MODE: {'Pathfinding' if self.path_mode else 'WASD'}"
        mode_label = self.font.render(mode_text, True, mode_color)
        self.screen.blit(mode_label, (sidebar_x + 10, y))
        y += 25
        
        # Path info
        if self.path_mode and self.path:
            path_text = f"Path: {len(self.path)} steps"
            path_label = self.font_small.render(path_text, True, COLORS['yellow'])
            self.screen.blit(path_label, (sidebar_x + 10, y))
            y += 20
        
        # Visible entities (using FOV system)
        visible = self.get_visible_info(radius=10)
        
        # Monsters with relative positions
        monsters_label = self.font.render("VISIBLE", True, COLORS['white'])
        self.screen.blit(monsters_label, (sidebar_x + 10, y))
        y += 25
        
        if visible['monsters']:
            for m in visible['monsters'][:4]:
                # Format: "Goblin:n3e2 (HP)"
                hp_text = f"{m['formatted']} ({m['hp']}/{m['max_hp']})"
                color = COLORS['orange'] if m['adjacent'] else COLORS['red']
                text = self.font_small.render(hp_text, True, color)
                self.screen.blit(text, (sidebar_x + 10, y))
                y += 18
        else:
            text = self.font_small.render("No enemies visible", True, COLORS['gray'])
            self.screen.blit(text, (sidebar_x + 10, y))
            y += 18
        
        y += 10
        
        # Visible items with relative positions
        items_label = self.font.render("ITEMS", True, COLORS['white'])
        self.screen.blit(items_label, (sidebar_x + 10, y))
        y += 25
        
        if visible['items']:
            for item in visible['items'][:5]:
                # Format: "Sword:n2w1"
                item_text = f"{item['formatted']}"
                color = COLORS['yellow'] if item['type'] == 'solvent' else COLORS['item']
                text = self.font_small.render(item_text, True, color)
                self.screen.blit(text, (sidebar_x + 10, y))
                y += 16
        else:
            text = self.font_small.render("No items visible", True, COLORS['gray'])
            self.screen.blit(text, (sidebar_x + 10, y))
    
    def render_bar(self, x: int, y: int, label: str, 
                   current: float, maximum: float,
                   fg_color, bg_color, bar_width: int = 180):
        """Render a status bar"""
        # Label
        label_text = self.font_small.render(label, True, COLORS['white'])
        self.screen.blit(label_text, (x, y))
        
        # Bar background
        bar_x = x + 35
        bar_rect = pygame.Rect(bar_x, y + 2, bar_width, 14)
        pygame.draw.rect(self.screen, bg_color, bar_rect)
        
        # Bar fill
        fill_width = int(bar_width * (current / maximum)) if maximum > 0 else 0
        fill_rect = pygame.Rect(bar_x, y + 2, fill_width, 14)
        pygame.draw.rect(self.screen, fg_color, fill_rect)
        
        # Border
        pygame.draw.rect(self.screen, COLORS['ui_border'], bar_rect, 1)
        
        # Value text
        value_text = self.font_small.render(f"{int(current)}/{int(maximum)}", True, COLORS['white'])
        text_rect = value_text.get_rect(center=(bar_x + bar_width // 2, y + 9))
        self.screen.blit(value_text, text_rect)
    
    def render_messages(self):
        """Render message log at bottom"""
        msg_y = self.game_area_height + 30
        
        # Background
        msg_rect = pygame.Rect(10, msg_y - 5, self.game_area_width, 100)
        pygame.draw.rect(self.screen, COLORS['ui_bg'], msg_rect)
        pygame.draw.rect(self.screen, COLORS['ui_border'], msg_rect, 1)
        
        # Messages
        for i, msg in enumerate(self.messages[-6:]):
            alpha = 128 + int(127 * (i / 6))
            text = self.font_small.render(msg, True, COLORS['light_gray'])
            self.screen.blit(text, (15, msg_y + i * 15))
    
    def render_controls(self):
        """Render controls help"""
        controls_y = SCREEN_HEIGHT - 30
        if self.dissolve_mode:
            controls = "1-9: Select item/solvent | ESC: Cancel | D: Exit dissolve mode"
        elif self.path_mode:
            controls = "LEFT CLICK: Set target | ENTER: Auto-move | RIGHT CLICK/P: Toggle mode | D: Dissolve | ESC: Quit"
        else:
            controls = "WASD: Move | SPACE: Attack | E: Pickup | 1: Fireball | 2: Heal | D: Dissolve | M: Map | P: Path mode | ESC: Quit"
        text = self.font_small.render(controls, True, COLORS['gray'])
        self.screen.blit(text, (10, controls_y))
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.render()
            self.clock.tick(60)
        
        # Save action log on exit
        self.save_log()
        print(f"Game log saved to {self.log_file}")
        pygame.quit()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Entry point"""
    seed = None
    if len(sys.argv) > 1:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            pass
    
    game = PygameGame(seed=seed)
    game.run()


if __name__ == "__main__":
    main()
