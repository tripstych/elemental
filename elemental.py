"""
Elemental RPG - Pygame GUI Version
WASD controls, visual dungeon rendering, real-time gameplay
"""

import traceback
import sys
import os
import random
import json
from datetime import datetime
import pygame
from pygame.locals import DOUBLEBUF, OPENGL

# OpenGL and ImGui imports
import OpenGL.GL as gl
import imgui
from imgui.integrations.pygame import PygameRenderer


# Add seed directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'seed'))

from seed.dungeon_generator import DungeonGenerator
from seed.pathfinding import Pathfinder

# Import from the original game
from game import GameWorld
from game_api import GameSession, GameAPIClient

from render import Render

from imguiui import ImguiUI

# Import core modules (game logic separated from UI)
from core import GameController

from transmutation_engine import TransmutationEngine

from constants import *


# ============================================================================
# ELEMENTAL GAME CLASS
# ============================================================================

class ElementalGame:
    """
    Pygame-based GUI for Elemental RPG
    """
    
    def __init__(self, seed: int = None):
        pygame.init()

        self.COLORS = COLORS
        # OpenGL mode for imgui
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Elemental RPG")

        # Create a software surface for pygame drawing (will be uploaded to OpenGL texture)
        self.game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Initialize imgui
        imgui.create_context()
        self.imgui_impl = PygameRenderer()
        io = imgui.get_io()
        io.display_size = (SCREEN_WIDTH, SCREEN_HEIGHT)

        # OpenGL texture for game surface
        self.game_texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.game_texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)
        
        # Game state
        self.running = True
        self.paused = False
        self.show_full_map = False
        self.messages = []
        self.max_messages = 8
        self.turn = 0

        self.drop_mode = False
        self.show_drop_menu = False
        self.show_inventory_ui = False
        
        # Action logging
        self.log_file = f"logs/game_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.action_log = []
        
        # Create game world
        self.world = GameWorld(width=60, height=30, seed=seed)
        self.world.spawn_player("Hero")

        # Create game controller (clean API for game logic)
        self.controller = GameController(self.world)

        # Create imgui UI handler
        self.imgui_ui = ImguiUI(self)
        
        # Create renderer
        self.renderer = Render(self)
        
        # Buff player for better combat feel
        player = self.world.player
        player.stats.attack_power = 20
        player.stats.magic_power = 18
        player.stats.defense = 12
        
        # Spawn monsters - stats scaled by TOUGHNESS
        for _ in range(SPAWN_MONSTERS):
            m = self.world.spawn_monster(near_player=True)
            # Base monster stats scaled by toughness
            m.stats.max_health = int(40 * TOUGHNESS)
            m.stats.current_health = m.stats.max_health
            m.stats.attack_power = int(10 * TOUGHNESS)
            m.stats.defense = int(6 * TOUGHNESS)
        self.world.scatter_items(20)
        
        # Spawn solvents and coagulants throughout the dungeon
        self.spawn_solvents(SPAWN_SOLVENTS)
        self.spawn_coagulants(SPAWN_COAGULANTS)

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
        self.selected_item = None
        self.selected_solvent = None
        
        # Ranged attack interface state
        self.ranged_mode = False
        self.ranged_target = None
        self.ranged_range = 2  # Base range for ranged attacks

        # Spell targeting interface state
        self.spell_target_mode = False
        self.pending_spell = None  # Spell name waiting to be cast

        # Melee targeting interface state
        self.melee_target_mode = False

        # Autotarget mode - auto-targets nearest enemy for attacks/spells
        self.autotarget_mode = False

        # Spell book - records meditated items with their essence
        self.spell_book = {}
        basic_spells = ['fireball.n.01', 'heal.v.01', 'shield.n.01']
        
        for synset_id in basic_spells:
            if synset_id in self.world.spells:
                spell_data = self.world.spells[synset_id]
                # Add to controller's spell book as castable spells
                from core.alchemy import SpellBookEntry
                entry = SpellBookEntry(
                    name=spell_data['definition'],
                    synset=synset_id,
                    definition=spell_data['definition'],
                    composition=spell_data['composition'],
                    item_type='spell',
                    castable=True,
                    spell_effect=spell_data.get('spell_effect'),
                    power=1.0
                )
                self.controller.alchemy.spell_book[synset_id] = entry
                # Also add to game's spell book for compatibility
                self.spell_book[synset_id] = {
                    'name': spell_data['definition'],
                    'synset': synset_id,
                    'definition': spell_data['definition'],
                    'composition': spell_data['composition'],
                    'type': 'spell',
                    'castable': True,
                    'spell_effect': spell_data.get('spell_effect'),
                    'word': spell_data.get('word')
                }  # {synset: {name, synset, composition, definition}}

        # Meditation mode
        self.meditate_mode = False
        self.show_spell_book = False

        # Transmutation engine
        self.transmutation_engine = TransmutationEngine(self)
        
        # Simplified mode system
        self.menu_mode = False  # False=gameplay, True=menu mode (blocks movement)

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
        self.add_message("Q=Meditate, G=Coagulate, B=Spell Book, I=Inventory")
        self.add_message("1=Fireball, 2=Heal")
    
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
        """Spawn solvent items in the dungeon with random vial sizes"""
        solvent_keys = list(SOLVENTS.keys())

        # Weighted vial size distribution (smaller vials more common)
        vial_weights = [
            ("tiny", 30),
            ("small", 35),
            ("medium", 20),
            ("large", 10),
            ("grand", 5),
        ]
        vial_pool = []
        for vial_key, weight in vial_weights:
            vial_pool.extend([vial_key] * weight)

        floors = (self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) +
                  self.world.dungeon.find_positions(DungeonGenerator.CORRIDOR))

        for _ in range(count):
            if not floors:
                break
            pos = random.choice(floors)
            solvent_key = random.choice(solvent_keys)
            vial_key = random.choice(vial_pool)

            solvent_data = SOLVENTS[solvent_key]
            vial_data = VIAL_SIZES[vial_key]

            # Create solvent item with quantity
            solvent_item = {
                'name': f"{vial_data['name']} of {solvent_data['name']}",
                'type': 'solvent',
                'is_solvent': True,
                'solvent_type': solvent_key,
                'vial_size': vial_key,
                'quantity': vial_data['volume'],
                'max_quantity': vial_data['volume'],
                'description': f"{solvent_data['description']} ({vial_data['volume']}ml)",
                'weight': vial_data['weight'],
            }

            if pos not in self.world.items_on_ground:
                self.world.items_on_ground[pos] = []
            self.world.items_on_ground[pos].append(solvent_item)

    def spawn_coagulants(self, count: int):
        """Spawn coagulant items in the dungeon with random vial sizes"""
        coagulant_keys = list(COAGULANTS.keys())

        # Weighted vial size distribution (smaller vials more common)
        vial_weights = [
            ("tiny", 30),
            ("small", 35),
            ("medium", 20),
            ("large", 10),
            ("grand", 5),
        ]
        vial_pool = []
        for vial_key, weight in vial_weights:
            vial_pool.extend([vial_key] * weight)

        floors = (self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR) +
                  self.world.dungeon.find_positions(DungeonGenerator.CORRIDOR))

        for _ in range(count):
            if not floors:
                break
            pos = random.choice(floors)
            coagulant_key = random.choice(coagulant_keys)
            vial_key = random.choice(vial_pool)

            coagulant_data = COAGULANTS[coagulant_key]
            vial_data = VIAL_SIZES[vial_key]

            # Create coagulant item with quantity
            coagulant_item = {
                'name': f"{vial_data['name']} of {coagulant_data['name']}",
                'type': 'coagulant',
                'is_coagulant': True,
                'coagulant_type': coagulant_key,
                'vial_size': vial_key,
                'quantity': vial_data['volume'],
                'max_quantity': vial_data['volume'],
                'description': f"{coagulant_data['description']} ({vial_data['volume']}ml)",
                'weight': vial_data['weight'],
            }

            if pos not in self.world.items_on_ground:
                self.world.items_on_ground[pos] = []
            self.world.items_on_ground[pos].append(coagulant_item)

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
        # Process imgui inputs first
        self.imgui_impl.process_inputs()

        for event in pygame.event.get():
            # Pass event to imgui
            self.imgui_impl.process_event(event)

            # Check if imgui wants keyboard/mouse
            io = imgui.get_io()

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # Only handle if imgui doesn't want keyboard
                if not io.want_capture_keyboard:
                    if event.key == pygame.K_RETURN and self.path_mode:
                        print("-"*10)
                        print(f"Event type:{event.type} Path: {self.path}  Path mode:{self.path_mode}")
                        print("Automove Initiated")
                        self.auto_move_path()
                    else:
                        self.handle_keydown(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Only handle if imgui doesn't want mouse
                if not io.want_capture_mouse:
                    if event.button == 1:  # Left click
                        if self.melee_target_mode:
                            self.handle_melee_target_click(event)
                        elif self.spell_target_mode:
                            self.handle_spell_target_click(event)
                        elif self.ranged_mode:
                            self.handle_ranged_click(event)
                        else:
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
    
    def is_menu_mode(self):
        """Check if we're in any menu mode (blocks gameplay movement)"""
        return (self.show_spell_book or 
                self.meditate_mode or 
                self.show_drop_menu or
                self.transmutation_engine.transmute_mode or
                self.melee_target_mode or
                self.spell_target_mode or
                self.ranged_mode)
    
    def set_menu_mode(self, active: bool):
        """Set menu mode state"""
        self.menu_mode = active

    def handle_keydown(self, event):
        """Handle key press"""
        player = self.world.player
        
        if not player.stats.is_alive():
            # Respawn on any key
            self.respawn_player()
            return
        
        if event.key == pygame.K_i:
            self.show_inventory()
            return

        if event.key == pygame.K_c:
            self.autotarget_mode = not self.autotarget_mode
            return
        # Toggle path mode with 'P'
        if event.key == pygame.K_p:
            self.toggle_path_mode()
            return
        
        # Toggle ranged mode with 'R'
        if event.key == pygame.K_r:
            self.toggle_ranged_mode()
            return

        # Toggle autotarget mode with 'T'
        if event.key == pygame.K_t:
            self.toggle_autotarget_mode()
            return

        # Toggle meditate mode with 'Q'
        if event.key == pygame.K_q:
            self.toggle_meditate_mode()
            return

        # Toggle spell book view with 'B'
        if event.key == pygame.K_b:
            self.show_spell_book = not self.show_spell_book
            if self.show_spell_book:
                self.add_message(f"Spell Book: {len(self.spell_book)} entries (B to close)")

        # Toggle inventory view with 'I'
        if event.key == pygame.K_i:
            self.show_inventory_ui = not self.show_inventory_ui
            if self.show_inventory_ui:
                self.add_message("Inventory opened (I to close)")
            else:
                self.add_message("Inventory closed")
            return

        # Save game with 'F5'
        if event.key == pygame.K_F5:
            self.save_game()
            return

        # Load game with 'F9'
        if event.key == pygame.K_F9:
            # Find most recent save file
            import glob
            save_files = glob.glob("savegame_*.json")
            if save_files:
                latest_save = max(save_files, key=os.path.getctime)
                self.load_game(latest_save)
            else:
                self.add_message("No save files found")
            return

        # Handle menu mode inputs first
        if self.is_menu_mode():
            # Transmute mode handled by engine
            if self.transmutation_engine.transmute_mode:
                self.transmutation_engine.handle_input(event)
                return
            
            # Meditate mode
            if self.meditate_mode:
                if pygame.K_0 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_0
                    self.meditate_on_item(index)
                    return
                elif event.key == pygame.K_ESCAPE:
                    self.meditate_mode = False
                    self.add_message("Meditation cancelled")
                    return
            
            # Drop menu
            if self.show_drop_menu:
                if pygame.K_0 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_0
                    self.drop_item(index)
                    return
                elif event.key == pygame.K_ESCAPE:
                    self.show_drop_menu = False
                    self.add_message("Drop cancelled")
                    return
            
            # Target modes (melee, spell, ranged)
            if event.key == pygame.K_ESCAPE:
                if self.melee_target_mode:
                    self.melee_target_mode = False
                    self.add_message("Attack cancelled")
                elif self.spell_target_mode:
                    self.spell_target_mode = False
                    self.pending_spell = None
                    self.add_message("Spell cancelled")
                elif self.ranged_mode:
                    self.ranged_mode = False
                    self.add_message("Ranged mode cancelled")
                return
        
        # Global keys (work in both modes)
        if event.key == pygame.K_ESCAPE and self.show_spell_book:
            self.show_spell_book = False
            return

        # Gameplay-only keys (blocked in menu mode)
        if self.is_menu_mode():
            return  # Block all gameplay input when in menu mode

        # Toggle gameplay modes
        if event.key == pygame.K_g:  # Transmute mode
            self.transmutation_engine.toggle_mode()
            return
        
        if event.key == pygame.K_q:  # Meditate mode
            self.toggle_meditate_mode()
            return
        
        if event.key == pygame.K_b:  # Spell book
            self.show_spell_book = not self.show_spell_book
            return
        
        if event.key == pygame.K_r:  # Ranged mode
            self.toggle_ranged_mode()
            return
        
        if event.key == pygame.K_t:  # Autotarget mode
            self.toggle_autotarget_mode()
            return
        
        if event.key == pygame.K_p:  # Path mode
            self.toggle_path_mode()
            return
        
        if event.key == pygame.K_c:  # Autotarget toggle
            self.autotarget_mode = not self.autotarget_mode
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
        
        # Pickup (E)
        elif event.key == pygame.K_e:
            self.do_pickup()
        # Drop item (X)
        elif event.key == pygame.K_x:
            self.do_dropitem()
        # Spells (1 = Fireball, 2 = Heal)
        elif event.key == pygame.K_1:
            # Enter spell targeting mode for damage spells
            self.enter_spell_target_mode('fireball')
        elif event.key == pygame.K_2:
            self.cast_spell('heal')
            moved = True
        
        # Map toggle (M)
        elif event.key == pygame.K_m:
            self.show_full_map = not self.show_full_map
        
        # Inventory (I)
        elif event.key == pygame.K_i:
            self.show_inventory()
        
        # Wait (Period)
        elif event.key == pygame.K_PERIOD:
            self.add_message("You wait...")
            moved = True
        
        # Monster turns after player action
        if moved:
            self.monster_turns()
    
    def toggle_ranged_mode(self):
        """Toggle ranged attack interface mode"""
        self.ranged_mode = not self.ranged_mode
        if self.ranged_mode:
            self.ranged_target = None
            self.add_message(f"Ranged mode: Click target within {self.ranged_range} tiles")
        else:
            self.add_message("Ranged mode: OFF")

    def toggle_autotarget_mode(self):
        """Toggle autotarget mode for attacks and spells"""
        self.autotarget_mode = not self.autotarget_mode
        if self.autotarget_mode:
            self.add_message("AUTOTARGET: ON - attacks/spells auto-target nearest enemy")
        else:
            self.add_message("AUTOTARGET: OFF - manual targeting")

    def toggle_meditate_mode(self):
        """Toggle meditation mode for studying items"""
        player = self.world.player
        items = [obj for obj in player.inventory.objects if not obj.get('is_solvent')]

        if not items:
            self.add_message("No items to meditate on!")
            return

        self.meditate_mode = not self.meditate_mode
        if self.meditate_mode:
            self.add_message("MEDITATE: Press 0-9 to select item")
        else:
            self.add_message("Meditation cancelled")

    def meditate_on_item(self, index: int):
        """Meditate on an inventory item to record it in the spell book"""
        player = self.world.player
        
        # Find item by actual inventory index, not filtered position
        target_item = None
        for obj in player.inventory.objects:
            if obj.get('index') == index and not obj.get('is_solvent'):
                target_item = obj
                break
        
        if not target_item:
            self.add_message("No meditate-able item at that slot!")
            return
        
        self.add_message(f"Meditating on: {target_item['name']}")

        # Check if item has a synset (from WordNet database)
        synset = target_item.get('synset')
        if not synset:
            self.add_message(f"Cannot meditate on {target_item['name']} - no essence pattern!")
            self.meditate_mode = False
            return

        # Calculate essence composition based on item type/material
        item_type = target_item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])

        # Create spell book entry
        entry = {
            'name': target_item['name'],
            'synset': synset,
            'definition': target_item.get('definition', 'Unknown'),
            'composition': base_essence.copy(),
            'type': item_type,
        }

        # Check if already in spell book
        if synset in self.spell_book:
            self.add_message(f"'{target_item['name']}' is already in your Spell Book!")
        else:
            self.spell_book[synset] = entry
            essence_str = ", ".join(f"{e[0].upper()}:{v}" for e, v in base_essence.items())
            self.add_message(f"Recorded '{target_item['name']}' to Spell Book!")
            self.add_message(f"Essence: {essence_str}")
            self.log_action('meditate', {
                'item': target_item['name'],
                'synset': synset,
                'essence': base_essence
            })

        self.meditate_mode = False

    def drop_item(self, index: int):
        """Drop an inventory item to the ground"""
        player = self.world.player
        items = player.inventory.objects

        if index >= len(items):
            self.add_message("No item at that slot!")
            return

        item = items[index]
        
        # Remove item from inventory
        player.inventory.objects.pop(index)
        
        # Add item to ground at player position
        player_pos = (player.x, player.y)
        if player_pos not in self.world.items_on_ground:
            self.world.items_on_ground[player_pos] = []
        self.world.items_on_ground[player_pos].append(item)
        
        self.add_message(f"Dropped {item['name']} on the ground")
        self.show_drop_menu = False
        
        self.log_action('drop_item', {
            'item': item['name'],
            'position': player_pos
        })

    def find_nearest_enemy_in_range(self, max_range: float, require_los: bool = True):
        """Find the nearest living enemy within range, optionally requiring line of sight"""
        player = self.world.player
        nearest_dist = float('inf')
        nearest_enemy = None

        for m in self.world.monsters:
            if not m.stats.is_alive():
                continue
            dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
            if dist <= max_range and dist < nearest_dist:
                # Check line of sight if required
                if require_los and not self.has_line_of_sight(player.x, player.y, m.x, m.y):
                    continue
                nearest_dist = dist
                nearest_enemy = m

        return nearest_enemy

    def enter_spell_target_mode(self, spell_name: str):
        """Enter spell targeting mode for a damage spell"""
        if spell_name not in self.spell_defs:
            self.add_message(f"Unknown spell: {spell_name}")
            return

        spell = self.spell_defs[spell_name]

        # Only damage spells need targeting
        if spell['spell_effect']['type'] != 'damage':
            self.cast_spell(spell_name)
            return

        player = self.world.player

        # Calculate spell range
        spell_range = 3 + int(player.stats.magic_power / 10)

        # Check if player has enough essence
        composition = spell.get('composition', {})
        can_cast = True
        for elem, cost in composition.items():
            if player.inventory.essences.get(elem, 0) < cost:
                can_cast = False
                break

        if not can_cast:
            self.add_message(f"Not enough essence to cast {spell_name}!")
            return

        # If autotarget is on, find and hit nearest enemy automatically
        if self.autotarget_mode:
            target = self.find_nearest_enemy_in_range(spell_range)
            if target:
                self.cast_spell_at_target(spell_name, target)
            else:
                self.add_message(f"No enemies in range! (Range: {spell_range} tiles)")
            return

        self.spell_target_mode = True
        self.pending_spell = spell_name
        self.add_message(f"SPELL TARGET: Click enemy within {spell_range} tiles (ESC to cancel)")

    def handle_spell_target_click(self, event):
        """Handle mouse click for spell targeting"""
        if not self.spell_target_mode or not self.pending_spell:
            return

        # Convert mouse position to world coordinates
        mouse_x, mouse_y = event.pos
        tile_x = mouse_x // TILE_SIZE + self.camera_x
        tile_y = mouse_y // TILE_SIZE + self.camera_y

        player = self.world.player
        spell = self.spell_defs[self.pending_spell]
        spell_range = 3 + int(player.stats.magic_power / 10)

        # Check if target is within range
        dist = ((tile_x - player.x)**2 + (tile_y - player.y)**2)**0.5
        if dist > spell_range:
            self.add_message(f"Target out of range! (Max: {spell_range} tiles)")
            return

        # Check if there's an entity at target
        target_entity = self.world.get_entity_at(tile_x, tile_y)
        if not target_entity or target_entity == player:
            self.add_message("No valid target!")
            return

        # Check line of sight
        if not self.has_line_of_sight(player.x, player.y, tile_x, tile_y):
            self.add_message("No clear line of sight!")
            return

        # Cast the spell at the targeted entity
        self.cast_spell_at_target(self.pending_spell, target_entity)

        # Exit spell target mode
        self.spell_target_mode = False
        self.pending_spell = None

    def cast_spell_at_target(self, spell_name: str, target):
        """Cast a spell at a specific target"""
        player = self.world.player
        spell = self.spell_defs[spell_name]

        # Cast the spell
        result = player.cast_spell(spell['synset'], spell, target=target)

        if result['success']:
            # Show essence spent
            spent = result.get('essence_spent', spell.get('composition', {}))
            spent_str = ", ".join(f"{e[:1].upper()}:{int(v)}" for e, v in spent.items() if v > 0)

            log_details = {'spell': spell_name, 'cost': spent}

            if 'damage' in result:
                rel_pos = self.get_relative_pos(target.x, target.y)
                self.add_message(f"{spell_name.upper()} hits {target.name} {rel_pos} for {result['damage']} damage!")
                log_details['target'] = target.name
                log_details['position'] = rel_pos
                log_details['damage'] = result['damage']
                log_details['killed'] = not target.stats.is_alive()
                if not target.stats.is_alive():
                    self.add_message(f"{target.name} is destroyed!")
                    self.drop_monster_loot(target)

            self.turn += 1
            self.log_action('cast', log_details)

            # Show remaining essence
            ess = player.inventory.essences
            self.add_message(f"Spent: {spent_str} | F:{int(ess['fire'])} W:{int(ess['water'])} E:{int(ess['earth'])} A:{int(ess['air'])}")

            # Monster turns after casting
            self.monster_turns()
        else:
            self.add_message(f"Spell failed: {result.get('message', result.get('reason', 'not enough essence'))}")

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
    
    def handle_ranged_click(self, event):
        """Handle mouse click for ranged attacks"""
        # Convert mouse position to world coordinates
        mouse_x, mouse_y = event.pos
        
        # Convert to tile coordinates
        tile_x = mouse_x // TILE_SIZE + self.camera_x
        tile_y = mouse_y // TILE_SIZE + self.camera_y
        
        player = self.world.player
        
        # Check if target is within range
        dist = ((tile_x - player.x)**2 + (tile_y - player.y)**2)**0.5
        if dist > self.ranged_range:
            self.add_message(f"Target out of range! (Max: {self.ranged_range} tiles)")
            return
        
        # Check if there's an entity at target
        target_entity = self.world.get_entity_at(tile_x, tile_y)
        if not target_entity or target_entity == player:
            self.add_message("No valid target!")
            return
        
        # Check if there's a clear line of sight
        if not self.has_line_of_sight(player.x, player.y, tile_x, tile_y):
            self.add_message("No clear line of sight!")
            return
        
        # Perform ranged attack
        self.perform_ranged_attack(target_entity)
    
    def has_line_of_sight(self, x1, y1, x2, y2) -> bool:
        """Check if there's a clear line between two points"""
        # Simple line-of-sight check using Bresenham's algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            if x == x2 and y == y2:
                break
            
            # Check if current position blocks sight
            if (x, y) != (x1, y1):  # Don't check starting position
                if not self.world.is_walkable(x, y):
                    entity = self.world.get_entity_at(x, y)
                    # Only block if there's a wall, not just entities
                    if not self.world.is_walkable(x, y):
                        return False
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return True
    
    def perform_ranged_attack(self, target):
        """Perform a ranged attack on target"""
        player = self.world.player
        
        # Check if player has ranged weapon
        ranged_weapon = None
        for item in player.inventory.objects:
            if item.get('type') == 'weapon' and item.get('ranged', False):
                ranged_weapon = item
                break
        
        if not ranged_weapon:
            self.add_message("No ranged weapon equipped!")
            return
        
        # Calculate damage (base + weapon bonus)
        base_damage = player.stats.attack_power
        weapon_bonus = ranged_weapon.get('damage_bonus', 0)
        total_damage = base_damage + weapon_bonus
        
        # Apply damage
        result = target.take_damage(total_damage)
        
        # Log the attack
        rel_pos = self.get_relative_pos(target.x, target.y)
        self.add_message(f"You shoot {target.name} {rel_pos} for {result['damage']} damage!")
        
        self.turn += 1
        self.log_action('ranged_attack', {
            'target': target.name,
            'position': rel_pos,
            'damage': result['damage'],
            'target_hp': f"{target.stats.current_health}/{target.stats.max_health}",
            'killed': not target.stats.is_alive(),
            'weapon': ranged_weapon['name']
        })
        
        if not target.stats.is_alive():
            self.add_message(f"{target.name} is defeated!")
            self.drop_monster_loot(target)
        
        # Exit ranged mode
        self.ranged_mode = False
        self.ranged_target = None
        self.monster_turns()
    
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
        
        # Update camera to follow player
        self.update_camera()
        
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
        """Attack: autotarget nearest, or enter targeting mode for manual selection"""
        player = self.world.player

        # If autotarget is on, find nearest enemy in melee range (1.5 tiles for diagonals)
        if self.autotarget_mode:
            target = self.find_nearest_enemy_in_range(1.5, require_los=False)
            if target:
                self.perform_melee_attack(target)
            else:
                self.add_message("No enemies in melee range.")
            return

        # Manual mode: enter melee targeting mode
        # Check if any enemies are in range first
        has_targets = False
        for dx, dy in [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]:
            x, y = player.x + dx, player.y + dy
            entity = self.world.get_entity_at(x, y)
            if entity and entity != player and entity.stats.is_alive():
                has_targets = True
                break

        if has_targets:
            self.melee_target_mode = True
            self.add_message("MELEE TARGET: Click adjacent enemy (ESC to cancel)")
        else:
            self.add_message("No enemies in melee range.")

    def handle_melee_target_click(self, event):
        """Handle mouse click for melee targeting"""
        if not self.melee_target_mode:
            return

        # Convert mouse position to world coordinates
        mouse_x, mouse_y = event.pos
        tile_x = mouse_x // TILE_SIZE + self.camera_x
        tile_y = mouse_y // TILE_SIZE + self.camera_y

        player = self.world.player

        # Check if target is adjacent (including diagonals)
        dx = tile_x - player.x
        dy = tile_y - player.y
        if abs(dx) > 1 or abs(dy) > 1:
            self.add_message("Target must be adjacent!")
            return

        # Check if there's an enemy at target
        target_entity = self.world.get_entity_at(tile_x, tile_y)
        if not target_entity or target_entity == player:
            self.add_message("No enemy there!")
            return

        if not target_entity.stats.is_alive():
            self.add_message("Target is already dead!")
            return

        # Perform the attack
        self.perform_melee_attack(target_entity)

        # Exit melee target mode
        self.melee_target_mode = False
        self.monster_turns()

    def perform_melee_attack(self, target):
        """Perform a melee attack on target"""
        player = self.world.player
        result = player.attack(target)

        if result['success']:
            # Determine direction for logging
            dx = target.x - player.x
            dy = target.y - player.y
            direction = {(0,-1):'n', (1,-1):'ne', (1,0):'e', (1,1):'se',
                        (0,1):'s', (-1,1):'sw', (-1,0):'w', (-1,-1):'nw'}.get((dx, dy), '?')
            rel_pos = self.get_relative_pos(target.x, target.y)

            self.add_message(f"You hit {target.name} {rel_pos} for {result['damage']} damage!")
            self.turn += 1
            self.log_action('attack', {
                'target': target.name,
                'direction': direction,
                'damage': result['damage'],
                'target_hp': f"{target.stats.current_health}/{target.stats.max_health}",
                'killed': not result['target_alive']
            })
            if not result['target_alive']:
                self.add_message(f"{target.name} is defeated!")
                self.drop_monster_loot(target)
    
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
            
    def do_dropitem(self):
        """Toggle drop item mode"""
        self.show_drop_menu = True
        
    
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
        """Perform dissolution - use solvent to extract essence from item"""
        if not self.selected_item or not self.selected_solvent:
            return

        player = self.world.player
        inv = player.inventory

        # Get solvent properties
        solvent_key = self.selected_solvent.get('solvent_type', 'alkahest')
        solvent_data = SOLVENTS.get(solvent_key, SOLVENTS['alkahest'])

        # Check solvent has enough quantity (10ml per extraction)
        solvent_cost = 10
        current_qty = self.selected_solvent.get('quantity', 0)
        if current_qty < solvent_cost:
            self.add_message(f"Not enough solvent! Need {solvent_cost}ml, have {current_qty}ml")
            self.selected_item = None
            self.selected_solvent = None
            return

        # Get item's material essence
        item_type = self.selected_item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])

        # Extract essences based on solvent affinity
        extracted = {}
        for elem in solvent_data['extracts']:
            amount = base_essence.get(elem, 10) * solvent_data['strength']
            extracted[elem] = amount
            inv.add_essence(elem, amount)

        # Consume solvent quantity (not the item!)
        self.selected_solvent['quantity'] -= solvent_cost

        # Remove empty solvent containers
        if self.selected_solvent['quantity'] <= 0:
            inv.objects.remove(self.selected_solvent)
            self.add_message(f"{self.selected_solvent['name']} is now empty!")

        # Report results
        extracted_str = ", ".join(f"{elem[:1].upper()}:{int(amount)}" for elem, amount in extracted.items())
        remaining = self.selected_solvent.get('quantity', 0)
        self.add_message(f"Extracted essence from {self.selected_item['name']}!")
        self.add_message(f"Got: {extracted_str} (used {solvent_cost}ml, {remaining}ml left)")
        self.log_action('extract', {
            'item': self.selected_item['name'],
            'solvent': self.selected_solvent['name'],
            'solvent_used': solvent_cost,
            'extracted': extracted
        })

        self.selected_item = None
        self.selected_solvent = None
    
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
    
    def save_game(self, filename: str = None):
        """Save game state to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"savegame_{timestamp}.json"
        
        # Save controller's spell book too
        controller_spell_book = {}
        for synset, entry in self.controller.alchemy.spell_book.items():
            controller_spell_book[synset] = {
                'name': entry.name,
                'synset': entry.synset,
                'definition': entry.definition,
                'composition': entry.composition,
                'item_type': entry.item_type,
                'castable': entry.castable,
                'spell_effect': entry.spell_effect,
                'power': entry.power
            }
        
        save_data = {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'player': {
                'name': self.world.player.name,
                'x': self.world.player.x,
                'y': self.world.player.y,
                'stats': {
                    'max_health': self.world.player.stats.max_health,
                    'current_health': self.world.player.stats.current_health,
                    'max_stamina': self.world.player.stats.max_stamina,
                    'current_stamina': self.world.player.stats.current_stamina,
                    'strength': self.world.player.stats.strength,
                    'magic_power': self.world.player.stats.magic_power,
                },
                'level': self.world.player.level,
                'experience': self.world.player.experience,
                'inventory': {
                    'max_essence': self.world.player.inventory.max_essence,
                },
            },
            'inventory': {
                'objects': self.world.player.inventory.objects,
                'essences': self.world.player.inventory.essences,
                'grimoire': list(self.world.player.inventory.grimoire)
            },
            'spell_book': self.spell_book,
            'controller_spell_book': controller_spell_book,
            'world': {
                'dungeon_seed': self.world.dungeon.seed,
                'turn': self.turn,
                'items_on_ground': {str(k): v for k, v in self.world.items_on_ground.items()}
            },
            'game_state': {
                'running': self.running,
                'paused': self.paused,
                'show_full_map': self.show_full_map,
                'show_spell_book': self.show_spell_book,
                'transmute_mode': self.transmute_mode,
                'meditate_mode': self.meditate_mode,
                'messages': self.messages[-20:]  # Save last 20 messages
            }
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(save_data, f, indent=2)
            self.add_message(f"Game saved to {filename}")
            self.log_action('save', {'filename': filename})
            return True
        except Exception as e:
            self.add_message(f"Failed to save: {e}")
            return False

    def load_game(self, filename: str):
        """Load game state from file"""
        try:
            with open(filename, 'r') as f:
                save_data = json.load(f)
            
            # Restore player stats and position
            player = self.world.player
            player.name = save_data['player']['name']
            player.x = save_data['player']['x']
            player.y = save_data['player']['y']
            player.level = save_data['player']['level']
            player.experience = save_data['player']['experience']
            
            stats = save_data['player']['stats']
            player.stats.max_health = stats['max_health']
            player.stats.current_health = stats['current_health']
            player.stats.max_stamina = stats['max_stamina']
            player.stats.current_stamina = stats['current_stamina']
            player.stats.strength = stats['strength']
            player.stats.magic_power = stats['magic_power']
            
            # Restore inventory-specific properties
            if 'inventory' in save_data['player'] and 'max_essence' in save_data['player']['inventory']:
                player.inventory.max_essence = save_data['player']['inventory']['max_essence']
            
            # Restore inventory
            player.inventory.objects = save_data['inventory']['objects']
            player.inventory.essences = save_data['inventory']['essences']
            player.inventory.grimoire = set(save_data['inventory']['grimoire'])
            
            # Restore spell book
            self.spell_book = save_data['spell_book']
            
            # Restore controller's spell book
            if 'controller_spell_book' in save_data:
                self.controller.alchemy.spell_book.clear()
                for synset, entry_data in save_data['controller_spell_book'].items():
                    from core.alchemy import SpellBookEntry
                    entry = SpellBookEntry(
                        name=entry_data['name'],
                        synset=entry_data['synset'],
                        definition=entry_data['definition'],
                        composition=entry_data['composition'],
                        item_type=entry_data['item_type'],
                        castable=entry_data.get('castable', False),
                        spell_effect=entry_data.get('spell_effect'),
                        power=entry_data.get('power', 0.0)
                    )
                    self.controller.alchemy.spell_book[synset] = entry
            
            # Restore world state
            self.turn = save_data['world']['turn']
            # Convert string keys back to tuples for items_on_ground
            self.world.items_on_ground = {}
            for pos_str, items in save_data['world']['items_on_ground'].items():
                pos = eval(pos_str)  # Convert string back to tuple
                self.world.items_on_ground[pos] = items
            
            # Restore game state
            game_state = save_data['game_state']
            self.running = game_state['running']
            self.paused = game_state['paused']
            self.show_full_map = game_state['show_full_map']
            self.show_spell_book = game_state['show_spell_book']
            self.transmute_mode = game_state['transmute_mode']
            self.meditate_mode = game_state['meditate_mode']
            self.messages = game_state['messages']
            
            # Update camera
            self.update_camera()
            
            self.add_message(f"Game loaded from {filename}")
            self.log_action('load', {'filename': filename})
            return True
            
        except Exception as e:
            self.add_message(f"Failed to load: {e}")
            return False

    def calculate_transmute_cost(self, source_item, target_pattern):
        """Calculate if transmutation is possible based on weight and essence constraints"""
        player = self.world.player
        
        # Get source item weight
        source_weight = source_item.get('weight', 0)
        
        # Find target object weight from game objects database
        target_weight = 0
        target_material = None
        
        # Check if this is a spell (castable) or object pattern
        if hasattr(target_pattern, 'castable') and target_pattern.castable:
            # For spells, use fixed weight property or default to 1g
            target_weight = getattr(target_pattern, 'weight', 1.0)
        else:
            # For objects, look up physical weight
            for obj in self.world.game_objects:
                if obj.get('synset') == target_pattern.synset:
                    target_weight = obj.get('weight', 0)
                    target_material = obj.get('material', None)
                    break
        
        if target_weight == 0 and not (hasattr(target_pattern, 'castable') and target_pattern.castable):
            return None, None, None, None, "Unknown target object"
        
        # Check weight constraint - can't create heavier object without more mass
        if target_weight > source_weight * 2:  # Allow some essence to add mass
            return None, None, None, None, f"Target too heavy: {target_weight}kg vs {source_weight}kg source"
        
        # Calculate essence requirements based on weight difference
        weight_ratio = target_weight / max(source_weight, 0.1)
        
        # Base essence cost scales with weight difference
        base_cost = {
            'fire': 5 * weight_ratio,
            'water': 5 * weight_ratio, 
            'earth': 5 * weight_ratio,
            'air': 5 * weight_ratio
        }
        
        # Adjust for target's actual composition
        if hasattr(target_pattern, 'composition'):
            for element, amount in target_pattern.composition.items():
                if element in base_cost:
                    base_cost[element] = amount * weight_ratio
        
        # Apply Wisdom modifier (5% reduction per point above 10)
        wisdom_modifier = max(0, (player.stats.wisdom - 10) * 0.05)
        
        # Apply modifier to costs
        final_cost = {}
        for element, cost in base_cost.items():
            final_cost[element] = cost * (1.0 - wisdom_modifier)
        
        return final_cost, target_weight, None, None, None

    def respawn_player(self):
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
        """Toggle inventory display using ImGui"""
        self.show_inventory_ui = not self.show_inventory_ui
    
    def build_inventory_content(self):
        """Build inventory content for overlay"""
        inv = self.world.player.inventory
        content = []
        
        # Add index to all items first
        for i, item in enumerate(inv.objects):
            item['index'] = i + 1
        
        # Separate items by type
        items = [obj for obj in inv.objects if not obj.get('is_solvent') and not obj.get('is_coagulant') and obj.get('type') not in ['weapon', 'weapons']]
        weapons = [obj for obj in inv.objects if obj.get('type') in ['weapon', 'weapons']]
        solvents = [obj for obj in inv.objects if obj.get('is_solvent')]
        coagulants = [obj for obj in inv.objects if obj.get('is_coagulant')]
        
        # Items section
        if items:
            content.append({"type": "header", "text": "ITEMS", "color": "white"})
            for item in items:
                content.append({"type": "text", "text": f"{item['index']}. {item['name']}", "color": "light_gray"})
        
        # Weapons section
        if weapons:
            if items:  # Add separator only if items section exists
                content.append({"type": "seperator"})
            content.append({"type": "header", "text": "WEAPONS", "color": "orange"})
            for weapon in weapons:
                content.append({"type": "text", "text": f"{weapon['index']}. {weapon['name']}", "color": "orange"})
        
        # Solvents section
        if solvents:
            if items or weapons:  # Add separator if previous sections exist
                content.append({"type": "seperator"})
            content.append({"type": "header", "text": "SOLVENTS", "color": "yellow"})
            for solvent in solvents:
                content.append({"type": "text", "text": f"{solvent['index']}. {solvent['name']}", "color": "yellow"})
        
        # Coagulants section
        if coagulants:
            if items or weapons or solvents:  # Add separator if previous sections exist
                content.append({"type": "seperator"})
            content.append({"type": "header", "text": "COAGULANTS", "color": "cyan"})
            for coag in coagulants:
                content.append({"type": "text", "text": f"{coag['index']}. {coag['name']}", "color": "cyan"})
        
        return content
    
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
        """Render the game to game_surface"""
        self.renderer.render()
    
   
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()

            # Render game to software surface
            self.render()

            # Start imgui frame
            imgui.new_frame()

            # Render imgui overlays
            self.imgui_ui.render()

            # Upload game surface to OpenGL texture
            texture_data = pygame.image.tostring(self.game_surface, "RGBA", True)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.game_texture)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, SCREEN_WIDTH, SCREEN_HEIGHT,
                           0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture_data)

            # Clear and draw game texture as fullscreen quad
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.game_texture)

            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(0, 0); gl.glVertex2f(-1, -1)
            gl.glTexCoord2f(1, 0); gl.glVertex2f(1, -1)
            gl.glTexCoord2f(1, 1); gl.glVertex2f(1, 1)
            gl.glTexCoord2f(0, 1); gl.glVertex2f(-1, 1)
            gl.glEnd()

            gl.glDisable(gl.GL_TEXTURE_2D)

            # Render imgui on top
            imgui.render()
            self.imgui_impl.render(imgui.get_draw_data())

            pygame.display.flip()
            self.clock.tick(60)

        # Save action log on exit
        self.save_log()
        print(f"Game log saved to {self.log_file}")
        self.imgui_impl.shutdown()
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
    
    seed = 42
    game = ElementalGame(seed=seed)
    game.run()


if __name__ == "__main__":
    main()
