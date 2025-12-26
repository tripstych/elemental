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

# Import core modules (game logic separated from UI)
from core import GameController

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
SPAWN_COAGULANTS = 10

# Vial sizes for solvents
VIAL_SIZES = {
    "tiny": {"name": "Tiny Vial", "volume": 10, "weight": 0.2},
    "small": {"name": "Small Vial", "volume": 25, "weight": 0.4},
    "medium": {"name": "Medium Flask", "volume": 50, "weight": 0.8},
    "large": {"name": "Large Flask", "volume": 100, "weight": 1.5},
    "grand": {"name": "Grand Bottle", "volume": 200, "weight": 3.0},
}

# Solvents for alchemy (dissolve items -> extract essence)
SOLVENTS = {
    "aqua_ignis": {
        "name": "Aqua Ignis",
        "extracts": ["fire", "air"],
        "strength": 0.8,
        "description": "Boiling alchemical water",
        "color": "orange",
    },
    "oleum_terra": {
        "name": "Oleum Terra",
        "extracts": ["earth", "water"],
        "strength": 0.9,
        "description": "Thick mineral oil",
        "color": "brown",
    },
    "alkahest": {
        "name": "Alkahest",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal solvent",
        "color": "purple",
    },
}

# Coagulants for alchemy (combine essence -> form items/spells)
COAGULANTS = {
    "ite_ignis": {
        "name": "Ite Ignis",
        "affinity": ["fire"],
        "strength": 0.9,
        "description": "Ite powder",
        "color": "red",
    },
    "ite_aqua": {
        "name": "Ite Aqua",
        "affinity": ["water"],
        "strength": 0.9,
        "description": "Cool shimmering gel",
        "color": "blue",
    },
    "ite_terra": {
        "name": "Ite Terra",
        "affinity": ["earth"],
        "strength": 0.85,
        "description": "iteiteiteite",
        "color": "green",
    },
    "ite_aether": {
        "name": "Ite Aether",
        "affinity": ["air"],
        "strength": 0.85,
        "description": "Wispy ethereal mist",
        "color": "white",
    },
    "prima_ite": {
        "name": "Prima Ite",
        "affinity": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal coagulant",
        "color": "gold",
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
# IMGUI UI CLASS
# ============================================================================

class ImguiUI:
    """Handles all imgui-based overlay rendering"""

    def __init__(self, game):
        self.game = game
        # Selection indices for keyboard navigation (per menu)
        self._selection_indices = {}

        # Transmutation state
        self._transmute_step = 0  # 0=item, 1=solvent, 2=solvent_amt, 3=coagulant, 4=coag_amt, 5=pattern
        self._transmute_item = None
        self._transmute_solvent = None
        self._transmute_solvent_amount = 50
        self._transmute_coagulant = None
        self._transmute_coagulant_amount = 50
        self._transmute_pattern = None

    def _render_selectable_list(
        self,
        list_id: str,
        items: list,
        label_fn,
        on_select,
        filter_fn=None,
        disabled_label_fn=None
    ):
        """
        Render a list of selectable items with keyboard navigation.

        Args:
            list_id: Unique ID for this list (for tracking selection index)
            items: List of items to display
            label_fn: Function(item, index) -> str for selectable items
            on_select: Callback(item) when item is selected (click or Enter)
            filter_fn: Optional function(item) -> bool, True = selectable
            disabled_label_fn: Optional function(item, index) -> str for disabled items

        Returns:
            The selected item if one was selected this frame, else None
        """
        if list_id not in self._selection_indices:
            self._selection_indices[list_id] = 0

        # Build list of selectable vs disabled items
        selectable = []
        display_order = []  # (item, is_selectable, original_index)

        for i, item in enumerate(items):
            is_selectable = filter_fn(item) if filter_fn else True
            display_order.append((item, is_selectable, i))
            if is_selectable:
                selectable.append(item)

        if not selectable:
            # Render all as disabled
            for item, _, orig_idx in display_order:
                if disabled_label_fn:
                    imgui.text_colored(disabled_label_fn(item, orig_idx), 0.5, 0.5, 0.5)
                else:
                    imgui.text_colored(label_fn(item, orig_idx), 0.5, 0.5, 0.5)
            return None

        # Keyboard navigation
        sel_idx = self._selection_indices[list_id]
        if imgui.is_key_pressed(imgui.KEY_DOWN_ARROW):
            sel_idx = (sel_idx + 1) % len(selectable)
        if imgui.is_key_pressed(imgui.KEY_UP_ARROW):
            sel_idx = (sel_idx - 1) % len(selectable)

        # Clamp
        if sel_idx >= len(selectable):
            sel_idx = 0
        self._selection_indices[list_id] = sel_idx

        # Check Enter key
        selected_item = None
        if imgui.is_key_pressed(imgui.KEY_ENTER) and selectable:
            selected_item = selectable[sel_idx]
            on_select(selected_item)

        # Render items
        selectable_idx = 0
        for item, is_selectable, orig_idx in display_order:
            if is_selectable:
                is_highlighted = (selectable_idx == sel_idx)
                clicked, _ = imgui.selectable(label_fn(item, orig_idx), is_highlighted)
                if clicked:
                    selected_item = item
                    on_select(item)
                selectable_idx += 1
            else:
                if disabled_label_fn:
                    imgui.text_colored(disabled_label_fn(item, orig_idx), 0.5, 0.5, 0.5)
                else:
                    imgui.text_colored(f"({label_fn(item, orig_idx)})", 0.5, 0.5, 0.5)

        return selected_item

    def reset_selection(self, list_id: str):
        """Reset selection index for a list"""
        self._selection_indices[list_id] = 0

    def render(self):
        """Render all active imgui windows"""
        if self.game.show_spell_book:
            self._render_spell_book()
        if self.game.transmute_mode:
            self._render_transmute()
        if self.game.dissolve_mode:
            self._render_dissolve()
        if self.game.meditate_mode:
            self._render_meditate()

    def _render_spell_book(self):
        """Render spell book overlay"""
        imgui.set_next_window_size(600, 400, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 200,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Spell Book", True)
        if not opened:
            self.game.show_spell_book = False
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        spell_book = self.game.spell_book
        if not spell_book:
            imgui.text_colored("No entries yet.", 0.5, 0.5, 0.5)
            imgui.text("Meditate (Q) on items to learn their essence.")
        else:
            imgui.columns(5, "spell_book_cols", True)
            imgui.set_column_width(0, 150)
            imgui.set_column_width(1, 150)
            imgui.set_column_width(2, 60)
            imgui.set_column_width(3, 60)
            imgui.set_column_width(4, 60)

            imgui.text_colored("Name", 0.4, 0.8, 1.0)
            imgui.next_column()
            imgui.text_colored("Synset", 0.4, 0.8, 1.0)
            imgui.next_column()
            imgui.text_colored("Fire", 1.0, 0.4, 0.2)
            imgui.next_column()
            imgui.text_colored("Water", 0.2, 0.6, 1.0)
            imgui.next_column()
            imgui.text_colored("Earth", 0.6, 0.4, 0.2)
            imgui.next_column()
            imgui.separator()

            for key, entry in spell_book.items():
                comp = entry['composition']
                name = entry['name'][:18] + ".." if len(entry['name']) > 18 else entry['name']
                synset = entry['synset'][:18] if len(entry['synset']) > 18 else entry['synset']

                imgui.text(name)
                imgui.next_column()
                imgui.text(synset)
                imgui.next_column()
                imgui.text_colored(str(comp.get('fire', 0)), 1.0, 0.4, 0.2)
                imgui.next_column()
                imgui.text_colored(str(comp.get('water', 0)), 0.2, 0.6, 1.0)
                imgui.next_column()
                imgui.text_colored(str(comp.get('earth', 0)), 0.6, 0.4, 0.2)
                imgui.next_column()

            imgui.columns(1)

        imgui.separator()
        imgui.text(f"Total entries: {len(spell_book)}")
        imgui.same_line(imgui.get_window_width() - 100)
        if imgui.button("Close [B]"):
            self.game.show_spell_book = False

        imgui.end()

    def _render_meditate(self):
        """Render meditation item selection popup"""
        imgui.set_next_window_size(400, 350, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 175,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Meditate", True)
        if not opened:
            self.game.meditate_mode = False
            self.reset_selection("meditate")
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        player = self.game.world.player

        imgui.text_colored("Select an item to study its essence:", 0.4, 0.8, 1.0)
        imgui.text_colored("(UP/DOWN + ENTER, or click)", 0.5, 0.5, 0.5)
        imgui.separator()
        imgui.spacing()

        # Get non-reagent items
        items = [obj for obj in player.inventory.objects[:9]
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]

        if not items:
            imgui.text_colored("No items to meditate on!", 0.8, 0.3, 0.3)
        else:
            def is_unknown(obj):
                synset = obj.get('synset')
                return not (synset and synset in self.game.spell_book)

            self._render_selectable_list(
                list_id="meditate",
                items=items,
                label_fn=lambda obj, i: f"{i+1}. {obj['name']}",
                on_select=self._do_meditate,
                filter_fn=is_unknown,
                disabled_label_fn=lambda obj, i: f"{i+1}. {obj['name']} (known)"
            )

        imgui.spacing()
        imgui.separator()
        imgui.text(f"Spell Book entries: {len(self.game.spell_book)}")

        imgui.same_line(imgui.get_window_width() - 100)
        if imgui.button("Cancel [Q]"):
            self.game.meditate_mode = False
            self.reset_selection("meditate")

        imgui.end()

    def _do_meditate(self, obj):
        """Perform meditation on an item"""
        result = self.game.controller.meditate(obj)
        self.game.add_message(result.message)

        # Sync spell book from controller
        if result.success:
            known_essences = self.game.controller.get_known_essences()
            for entry in known_essences:
                if entry.synset not in self.game.spell_book:
                    self.game.spell_book[entry.synset] = {
                        'name': entry.name,
                        'synset': entry.synset,
                        'definition': entry.definition,
                        'composition': entry.composition,
                    }

        self.game.meditate_mode = False
        self.reset_selection("meditate")

    def _render_dissolve(self):
        """Render dissolve mode overlay"""
        imgui.set_next_window_size(500, 400, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 250, SCREEN_HEIGHT // 2 - 200,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Dissolve", True)
        if not opened:
            self._close_dissolve()
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        player = self.game.world.player

        if not self.game.selected_item:
            imgui.text_colored("Step 1/2: Select Item", 0.4, 0.8, 1.0)
        else:
            imgui.text_colored("Step 2/2: Select Solvent", 0.4, 0.8, 1.0)

        imgui.text_colored("(UP/DOWN + ENTER, or click)", 0.5, 0.5, 0.5)
        imgui.separator()

        if self.game.selected_item:
            imgui.text(f"Selected: {self.game.selected_item['name']}")
            imgui.separator()

        items = player.inventory.objects[:9]

        if not self.game.selected_item:
            imgui.text("Select an item to dissolve:")
            imgui.spacing()

            def select_item(obj):
                self.game.selected_item = obj
                self.reset_selection("dissolve_item")

            self._render_selectable_list(
                list_id="dissolve_item",
                items=items,
                label_fn=lambda obj, i: f"{i+1}. {obj['name']}",
                on_select=select_item,
                filter_fn=lambda obj: not obj.get('is_solvent') and not obj.get('is_coagulant'),
                disabled_label_fn=lambda obj, i: f"{i+1}. {obj['name']} (reagent)"
            )
        else:
            imgui.text("Select a solvent:")
            imgui.spacing()

            def do_dissolve(solvent):
                result = self.game.controller.dissolve(
                    item=self.game.selected_item,
                    solvent=solvent,
                    amount=min(10, solvent.get('quantity', 0))
                )
                self.game.add_message(result.message)
                self._close_dissolve()

            self._render_selectable_list(
                list_id="dissolve_solvent",
                items=items,
                label_fn=lambda obj, i: f"{i+1}. {obj['name']} ({obj.get('quantity', 0)}ml)",
                on_select=do_dissolve,
                filter_fn=lambda obj: obj.get('is_solvent'),
                disabled_label_fn=lambda obj, i: f"{i+1}. {obj['name']} (not a solvent)"
            )

        imgui.separator()
        if imgui.button("Cancel [ESC]"):
            self._close_dissolve()

        imgui.end()

    def _close_dissolve(self):
        """Close dissolve mode and reset state"""
        self.game.dissolve_mode = False
        self.game.selected_item = None
        self.reset_selection("dissolve_item")
        self.reset_selection("dissolve_solvent")

    def _reset_transmute(self):
        """Reset all transmutation state"""
        self._transmute_step = 0
        self._transmute_item = None
        self._transmute_solvent = None
        self._transmute_solvent_amount = 50
        self._transmute_coagulant = None
        self._transmute_coagulant_amount = 50
        self._transmute_pattern = None
        self.reset_selection("transmute_item")
        self.reset_selection("transmute_solvent")
        self.reset_selection("transmute_coagulant")
        self.reset_selection("transmute_pattern")

    def _render_transmute(self):
        """Render transmutation mode overlay - full wizard"""
        imgui.set_next_window_size(700, 500, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 250,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Transmutation", True)
        if not opened:
            self.game.transmute_mode = False
            self._reset_transmute()
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        # Two column layout
        imgui.columns(2, "transmute_cols", True)
        imgui.set_column_width(0, 400)

        # Left panel: current step
        self._render_transmute_left_panel()

        imgui.next_column()

        # Right panel: known essences reference
        self._render_transmute_right_panel()

        imgui.columns(1)

        # Bottom bar
        imgui.separator()
        if imgui.button("Cancel [ESC]"):
            self.game.transmute_mode = False
            self._reset_transmute()

        # Back button (if not on first step)
        if self._transmute_step > 0:
            imgui.same_line()
            if imgui.button("< Back"):
                self._transmute_step -= 1

        # Transmute button when ready
        if self._can_transmute():
            imgui.same_line(imgui.get_window_width() - 120)
            if imgui.button("TRANSMUTE!"):
                self._do_transmute()

        imgui.end()

    def _render_transmute_left_panel(self):
        """Render the left panel with step-by-step selections"""
        step_names = ["Select Item", "Select Solvent", "Solvent Amount",
                      "Select Coagulant", "Coagulant Amount", "Select Pattern"]

        imgui.text_colored(f"Step {self._transmute_step + 1}/6: {step_names[self._transmute_step]}", 0.4, 0.8, 1.0)
        imgui.text_colored("(UP/DOWN + ENTER, or click)", 0.5, 0.5, 0.5)
        imgui.separator()

        # Show current selections
        imgui.text("Current Selections:")
        if self._transmute_item:
            imgui.bullet_text(f"Item: {self._transmute_item['name']}")
            essence = self.game.controller.get_essence_for_item(self._transmute_item)
            if essence:
                imgui.same_line()
                self._render_essence_inline(essence)
            else:
                imgui.same_line()
                imgui.text_colored("(unknown)", 1.0, 0.3, 0.3)

        if self._transmute_solvent:
            imgui.bullet_text(f"Solvent: {self._transmute_solvent['name']} ({self._transmute_solvent_amount}ml)")

        if self._transmute_coagulant:
            imgui.bullet_text(f"Coagulant: {self._transmute_coagulant['name']} ({self._transmute_coagulant_amount}ml)")

        if self._transmute_pattern:
            imgui.bullet_text(f"Pattern: {self._transmute_pattern.name}")

        imgui.spacing()
        imgui.separator()
        imgui.spacing()

        # Render current step UI
        if self._transmute_step == 0:
            self._render_transmute_item_step()
        elif self._transmute_step == 1:
            self._render_transmute_solvent_step()
        elif self._transmute_step == 2:
            self._render_transmute_solvent_amount_step()
        elif self._transmute_step == 3:
            self._render_transmute_coagulant_step()
        elif self._transmute_step == 4:
            self._render_transmute_coagulant_amount_step()
        elif self._transmute_step == 5:
            self._render_transmute_pattern_step()

    def _render_transmute_item_step(self):
        """Step 0: Select item to transmute"""
        imgui.text("Select an item to transmute:")
        imgui.spacing()

        player = self.game.world.player
        items = [obj for obj in player.inventory.objects[:9]
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]

        if not items:
            imgui.text_colored("No items available!", 0.8, 0.3, 0.3)
            return

        def select_item(item):
            self._transmute_item = item
            self._transmute_step = 1
            self.reset_selection("transmute_item")

        def label_fn(item, i):
            essence = self.game.controller.get_essence_for_item(item)
            if essence:
                return f"{i+1}. {item['name']}"
            return f"{i+1}. {item['name']} (?)"

        self._render_selectable_list(
            list_id="transmute_item",
            items=items,
            label_fn=label_fn,
            on_select=select_item
        )

    def _render_transmute_solvent_step(self):
        """Step 1: Select solvent"""
        imgui.text("Select a solvent:")
        imgui.spacing()

        player = self.game.world.player
        solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]

        if not solvents:
            imgui.text_colored("No solvents in inventory!", 0.8, 0.3, 0.3)
            return

        def select_solvent(solvent):
            self._transmute_solvent = solvent
            self._transmute_solvent_amount = min(50, solvent.get('quantity', 0))
            self._transmute_step = 2
            self.reset_selection("transmute_solvent")

        self._render_selectable_list(
            list_id="transmute_solvent",
            items=solvents,
            label_fn=lambda obj, i: f"{obj['name']} ({obj.get('quantity', 0)}ml)",
            on_select=select_solvent
        )

    def _render_transmute_solvent_amount_step(self):
        """Step 2: Set solvent amount"""
        if not self._transmute_solvent:
            return

        max_amt = self._transmute_solvent.get('quantity', 0)
        imgui.text(f"Select solvent amount (max {max_amt}ml):")
        imgui.spacing()

        changed, self._transmute_solvent_amount = imgui.slider_int(
            "##solvent_amt", self._transmute_solvent_amount, 1, max_amt,
            f"{self._transmute_solvent_amount}ml"
        )

        # Quick buttons
        imgui.spacing()
        if imgui.button("25ml"):
            self._transmute_solvent_amount = min(25, max_amt)
        imgui.same_line()
        if imgui.button("50ml"):
            self._transmute_solvent_amount = min(50, max_amt)
        imgui.same_line()
        if imgui.button("100ml"):
            self._transmute_solvent_amount = min(100, max_amt)
        imgui.same_line()
        if imgui.button("Max"):
            self._transmute_solvent_amount = max_amt

        imgui.spacing()
        if imgui.button("Confirm Amount") or imgui.is_key_pressed(imgui.KEY_ENTER):
            self._transmute_step = 3

    def _render_transmute_coagulant_step(self):
        """Step 3: Select coagulant"""
        imgui.text("Select a coagulant:")
        imgui.spacing()

        player = self.game.world.player
        coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]

        if not coagulants:
            imgui.text_colored("No coagulants in inventory!", 0.8, 0.3, 0.3)
            return

        def select_coagulant(coag):
            self._transmute_coagulant = coag
            self._transmute_coagulant_amount = min(50, coag.get('quantity', 0))
            self._transmute_step = 4
            self.reset_selection("transmute_coagulant")

        self._render_selectable_list(
            list_id="transmute_coagulant",
            items=coagulants,
            label_fn=lambda obj, i: f"{obj['name']} ({obj.get('quantity', 0)}ml)",
            on_select=select_coagulant
        )

    def _render_transmute_coagulant_amount_step(self):
        """Step 4: Set coagulant amount"""
        if not self._transmute_coagulant:
            return

        max_amt = self._transmute_coagulant.get('quantity', 0)
        imgui.text(f"Select coagulant amount (max {max_amt}ml):")
        imgui.spacing()

        changed, self._transmute_coagulant_amount = imgui.slider_int(
            "##coag_amt", self._transmute_coagulant_amount, 1, max_amt,
            f"{self._transmute_coagulant_amount}ml"
        )

        imgui.spacing()
        if imgui.button("25ml##c"):
            self._transmute_coagulant_amount = min(25, max_amt)
        imgui.same_line()
        if imgui.button("50ml##c"):
            self._transmute_coagulant_amount = min(50, max_amt)
        imgui.same_line()
        if imgui.button("100ml##c"):
            self._transmute_coagulant_amount = min(100, max_amt)
        imgui.same_line()
        if imgui.button("Max##c"):
            self._transmute_coagulant_amount = max_amt

        imgui.spacing()
        if imgui.button("Confirm Amount##c") or imgui.is_key_pressed(imgui.KEY_ENTER):
            self._transmute_step = 5

    def _render_transmute_pattern_step(self):
        """Step 5: Select target pattern from spell book"""
        imgui.text("Select target pattern from known essences:")
        imgui.spacing()

        patterns = self.game.controller.get_known_essences()
        if not patterns:
            imgui.text_colored("No patterns known!", 0.8, 0.3, 0.3)
            imgui.text("Meditate (Q) on items first.")
            return

        def select_pattern(pattern):
            self._transmute_pattern = pattern
            self.reset_selection("transmute_pattern")

        def label_fn(entry, i):
            return entry.name

        self._render_selectable_list(
            list_id="transmute_pattern",
            items=patterns,
            label_fn=label_fn,
            on_select=select_pattern
        )

        # Show essence composition for selected pattern
        if self._transmute_pattern:
            imgui.spacing()
            imgui.text("Target essence:")
            imgui.same_line()
            self._render_essence_inline(self._transmute_pattern.composition)

    def _render_transmute_right_panel(self):
        """Render the right panel with known essences reference"""
        imgui.text_colored("Known Essences (Reference)", 0.8, 0.4, 1.0)
        imgui.separator()

        known = self.game.controller.get_known_essences()
        if not known:
            imgui.text_colored("No essences known!", 0.5, 0.5, 0.5)
            imgui.text("Meditate (Q) on items")
            imgui.text("to learn their essence.")
            return

        # Table
        imgui.columns(5, "essence_ref_table", True)
        imgui.set_column_width(0, 100)
        imgui.set_column_width(1, 35)
        imgui.set_column_width(2, 35)
        imgui.set_column_width(3, 35)
        imgui.set_column_width(4, 35)

        imgui.text("Name")
        imgui.next_column()
        imgui.text_colored("F", 1.0, 0.4, 0.2)
        imgui.next_column()
        imgui.text_colored("W", 0.2, 0.6, 1.0)
        imgui.next_column()
        imgui.text_colored("E", 0.6, 0.4, 0.2)
        imgui.next_column()
        imgui.text_colored("A", 0.7, 0.7, 1.0)
        imgui.next_column()

        imgui.separator()

        for entry in known:
            comp = entry.composition
            name = entry.name[:12] + ".." if len(entry.name) > 12 else entry.name

            imgui.text(name)
            imgui.next_column()
            imgui.text_colored(str(comp.get('fire', 0)), 1.0, 0.4, 0.2)
            imgui.next_column()
            imgui.text_colored(str(comp.get('water', 0)), 0.2, 0.6, 1.0)
            imgui.next_column()
            imgui.text_colored(str(comp.get('earth', 0)), 0.6, 0.4, 0.2)
            imgui.next_column()
            imgui.text_colored(str(comp.get('air', 0)), 0.7, 0.7, 1.0)
            imgui.next_column()

        imgui.columns(1)

    def _render_essence_inline(self, comp):
        """Render essence values inline with colors"""
        imgui.text_colored(f"F:{comp.get('fire', 0)}", 1.0, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"W:{comp.get('water', 0)}", 0.2, 0.6, 1.0)
        imgui.same_line()
        imgui.text_colored(f"E:{comp.get('earth', 0)}", 0.6, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"A:{comp.get('air', 0)}", 0.7, 0.7, 1.0)

    def _can_transmute(self):
        """Check if all selections are complete"""
        return (self._transmute_item is not None and
                self._transmute_solvent is not None and
                self._transmute_coagulant is not None and
                self._transmute_pattern is not None)

    def _do_transmute(self):
        """Execute the transmutation"""
        result = self.game.controller.transmute(
            item=self._transmute_item,
            solvent=self._transmute_solvent,
            solvent_amount=self._transmute_solvent_amount,
            coagulant=self._transmute_coagulant,
            coagulant_amount=self._transmute_coagulant_amount,
            pattern=self._transmute_pattern
        )

        self.game.add_message(result.message)
        self.game.transmute_mode = False
        self._reset_transmute()


# ============================================================================
# PYGAME GAME CLASS
# ============================================================================

class PygameGame:
    """
    Pygame-based GUI for Elemental RPG
    """
    
    def __init__(self, seed: int = None):
        pygame.init()

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
        self.font_small = pygame.font.Font(None, 18)
        
        # Game state
        self.running = True
        self.paused = False
        self.show_full_map = False
        self.messages = []
        self.max_messages = 8
        self.turn = 0
        
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
        self.dissolve_mode = False
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
        self.spell_book = {}  # {synset: {name, synset, composition, definition}}

        # Meditation mode
        self.meditate_mode = False
        self.show_spell_book = False

        # Transmutation mode - single action: item + solvent + coagulant + spell pattern -> cast
        self.transmute_mode = False
        self.transmute_step = 0  # 0=select item, 1=select solvent, 2=solvent amount, 3=select coagulant, 4=coagulant amount, 5=select pattern
        self.transmute_item = None
        self.transmute_solvent = None
        self.transmute_solvent_amount = 0
        self.transmute_coagulant = None
        self.transmute_coagulant_amount = 0
        self.transmute_pattern = None  # Spell book entry to create

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
        self.add_message("Q=Meditate, G=Coagulate, B=Spell Book")
        self.add_message("1=Fireball, 2=Heal, F=Dissolve")
    
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
        
        # Toggle dissolve mode with 'F'
        if event.key == pygame.K_f:
            self.toggle_dissolve_mode()
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
            return

        # Toggle transmute mode with 'G'
        if event.key == pygame.K_g and not self.dissolve_mode and not self.meditate_mode:
            self.toggle_transmute_mode()
            return

        # Handle transmute mode selections
        if self.transmute_mode:
            self.handle_transmute_input(event)
            return

        # Handle meditate mode selections
        if self.meditate_mode:
            if pygame.K_1 <= event.key <= pygame.K_9:
                index = event.key - pygame.K_1
                self.meditate_on_item(index)
                return
            elif event.key == pygame.K_ESCAPE:
                self.meditate_mode = False
                self.add_message("Meditation cancelled")
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
        
        # Dissolve item (3)
        elif event.key == pygame.K_3:
            self.dissolve_item()
        
        # Map toggle (M)
        elif event.key == pygame.K_m:
            self.show_full_map = not self.show_full_map
        
        # Inventory (I)
        elif event.key == pygame.K_i:
            self.show_inventory()
        
        # Cancel targeting modes (ESC no longer quits game)
        elif event.key == pygame.K_ESCAPE:
            if self.melee_target_mode:
                self.melee_target_mode = False
                self.add_message("Attack cancelled")
            elif self.spell_target_mode:
                self.spell_target_mode = False
                self.pending_spell = None
                self.add_message("Spell cancelled")
            # ESC no longer quits the game
        
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
            self.add_message("MEDITATE: Select item (1-9) to study its essence")
        else:
            self.add_message("Meditation cancelled")

    def meditate_on_item(self, index: int):
        """Meditate on an inventory item to record it in the spell book"""
        player = self.world.player
        items = [obj for obj in player.inventory.objects if not obj.get('is_solvent')]

        if index >= len(items):
            self.add_message("No item at that slot!")
            return

        item = items[index]

        # Check if item has a synset (from WordNet database)
        synset = item.get('synset')
        if not synset:
            self.add_message(f"Cannot meditate on {item['name']} - no essence pattern!")
            self.meditate_mode = False
            return

        # Calculate essence composition based on item type/material
        item_type = item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])

        # Create spell book entry
        entry = {
            'name': item['name'],
            'synset': synset,
            'definition': item.get('definition', 'Unknown'),
            'composition': base_essence.copy(),
            'type': item_type,
        }

        # Check if already in spell book
        if synset in self.spell_book:
            self.add_message(f"'{item['name']}' is already in your Spell Book!")
        else:
            self.spell_book[synset] = entry
            essence_str = ", ".join(f"{e[0].upper()}:{v}" for e, v in base_essence.items())
            self.add_message(f"Recorded '{item['name']}' to Spell Book!")
            self.add_message(f"Essence: {essence_str}")
            self.log_action('meditate', {
                'item': item['name'],
                'synset': synset,
                'essence': base_essence
            })

        self.meditate_mode = False

    def toggle_transmute_mode(self):
        """Toggle transmutation mode - single action spell casting"""
        player = self.world.player

        # Need spell book entries
        if not self.spell_book:
            self.add_message("Spell Book is empty! Meditate (Q) on items first.")
            return

        # Need items to extract from
        items = [obj for obj in player.inventory.objects
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]
        if not items:
            self.add_message("No items to transmute!")
            return

        # Need solvents
        solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
        if not solvents:
            self.add_message("No solvents in inventory!")
            return

        # Need coagulants
        coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
        if not coagulants:
            self.add_message("No coagulants in inventory!")
            return

        self.transmute_mode = not self.transmute_mode
        if self.transmute_mode:
            self.reset_transmute_state()
            self.add_message("TRANSMUTE: Select source item (1-9)")
        else:
            self.add_message("Transmutation cancelled")

    def reset_transmute_state(self):
        """Reset all transmutation state"""
        self.transmute_step = 0
        self.transmute_item = None
        self.transmute_solvent = None
        self.transmute_solvent_amount = 0
        self.transmute_coagulant = None
        self.transmute_coagulant_amount = 0
        self.transmute_pattern = None

    def handle_transmute_input(self, event):
        """Handle keyboard input during transmutation"""
        player = self.world.player

        # ESC cancels
        if event.key == pygame.K_ESCAPE:
            self.transmute_mode = False
            self.reset_transmute_state()
            self.add_message("Transmutation cancelled")
            return

        # Number keys for selection
        if pygame.K_1 <= event.key <= pygame.K_9:
            index = event.key - pygame.K_1
            self.handle_transmute_selection(index)
            return

        # 0 key for amounts (represents 10 in amount selection)
        if event.key == pygame.K_0:
            if self.transmute_step in [2, 4]:  # Amount selection steps
                self.handle_transmute_selection(9)  # 0 = 10 units
            return

    def handle_transmute_selection(self, index: int):
        """Handle selection at current transmutation step"""
        player = self.world.player

        if self.transmute_step == 0:
            # Step 0: Select item
            items = [obj for obj in player.inventory.objects
                     if not obj.get('is_solvent') and not obj.get('is_coagulant')]
            if index >= len(items):
                self.add_message("No item at that slot!")
                return
            self.transmute_item = items[index]
            self.transmute_step = 1
            self.add_message(f"Item: {self.transmute_item['name']}")
            self.add_message("Select solvent (1-9)")

        elif self.transmute_step == 1:
            # Step 1: Select solvent
            solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
            if index >= len(solvents):
                self.add_message("No solvent at that slot!")
                return
            self.transmute_solvent = solvents[index]
            self.transmute_step = 2
            max_amt = self.transmute_solvent.get('quantity', 0)
            self.add_message(f"Solvent: {self.transmute_solvent['name']} ({max_amt}ml)")
            self.add_message(f"Select amount: 1-9 for 10-90ml, 0 for 100ml (max {max_amt}ml)")

        elif self.transmute_step == 2:
            # Step 2: Select solvent amount (1-9 = 10-90ml, 0 = 100ml)
            amount = (index + 1) * 10  # 1->10, 2->20, ..., 9->90, 0->100
            if index == 9:
                amount = 100
            max_amt = self.transmute_solvent.get('quantity', 0)
            if amount > max_amt:
                amount = max_amt
            if amount <= 0:
                self.add_message("No solvent available!")
                return
            self.transmute_solvent_amount = amount
            self.transmute_step = 3
            self.add_message(f"Using {amount}ml solvent")
            self.add_message("Select coagulant (1-9)")

        elif self.transmute_step == 3:
            # Step 3: Select coagulant
            coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
            if index >= len(coagulants):
                self.add_message("No coagulant at that slot!")
                return
            self.transmute_coagulant = coagulants[index]
            self.transmute_step = 4
            max_amt = self.transmute_coagulant.get('quantity', 0)
            self.add_message(f"Coagulant: {self.transmute_coagulant['name']} ({max_amt}ml)")
            self.add_message(f"Select amount: 1-9 for 10-90ml, 0 for 100ml (max {max_amt}ml)")

        elif self.transmute_step == 4:
            # Step 4: Select coagulant amount
            amount = (index + 1) * 10
            if index == 9:
                amount = 100
            max_amt = self.transmute_coagulant.get('quantity', 0)
            if amount > max_amt:
                amount = max_amt
            if amount <= 0:
                self.add_message("No coagulant available!")
                return
            self.transmute_coagulant_amount = amount
            self.transmute_step = 5
            self.add_message(f"Using {amount}ml coagulant")
            self.add_message("Select spell pattern from Spell Book (1-9)")

        elif self.transmute_step == 5:
            # Step 5: Select spell pattern from spell book
            entries = list(self.spell_book.values())
            if index >= len(entries):
                self.add_message("No pattern at that slot!")
                return
            self.transmute_pattern = entries[index]
            self.add_message(f"Pattern: {self.transmute_pattern['name']}")
            # Now perform the transmutation!
            self.perform_transmutation()

    def perform_transmutation(self):
        """Execute the transmutation - extract essence and form spell in one action"""
        player = self.world.player
        inv = player.inventory

        # Get solvent and coagulant properties
        solvent_key = self.transmute_solvent.get('solvent_type', 'alkahest')
        solvent_data = SOLVENTS.get(solvent_key, SOLVENTS['alkahest'])
        coag_key = self.transmute_coagulant.get('coagulant_type', 'prima_ite')
        coag_data = COAGULANTS.get(coag_key, COAGULANTS['prima_ite'])

        # Calculate essence extracted from item based on solvent amount and type
        # Solvent extracts specific elements based on its affinity
        item_type = self.transmute_item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])

        extracted_essence = {}
        solvent_strength = solvent_data.get('strength', 1.0)
        solvent_extracts = solvent_data.get('extracts', [])

        # More solvent = more essence extracted (10ml = 1x, 100ml = 10x)
        extraction_multiplier = self.transmute_solvent_amount / 10.0

        for elem in solvent_extracts:
            base_amount = base_essence.get(elem, 10)
            extracted = base_amount * solvent_strength * extraction_multiplier
            extracted_essence[elem] = extracted

        # Get the pattern requirements
        pattern_comp = self.transmute_pattern.get('composition', {})

        # Coagulant binds essence to form the pattern
        # Coagulant with matching affinity is more efficient
        coag_affinity = coag_data.get('affinity', [])
        coag_strength = coag_data.get('strength', 1.0)

        # More coagulant = better binding efficiency (10ml = 50%, 100ml = 100%)
        binding_efficiency = min(1.0, 0.5 + (self.transmute_coagulant_amount / 200.0))

        # Calculate how much of each element we can bind
        bound_essence = {}
        for elem, required in pattern_comp.items():
            available = extracted_essence.get(elem, 0)
            # Affinity bonus
            if elem in coag_affinity:
                effective_available = available * (1.0 + coag_strength * 0.5)
            else:
                effective_available = available * 0.7  # Penalty for non-affinity

            bound = min(required, effective_available * binding_efficiency)
            bound_essence[elem] = bound

        # Calculate completion percentage
        total_required = sum(pattern_comp.values())
        total_bound = sum(bound_essence.values())
        completion = total_bound / total_required if total_required > 0 else 0

        # Consume resources
        self.transmute_solvent['quantity'] -= self.transmute_solvent_amount
        self.transmute_coagulant['quantity'] -= self.transmute_coagulant_amount

        # Remove empty containers
        if self.transmute_solvent['quantity'] <= 0:
            inv.objects.remove(self.transmute_solvent)
        if self.transmute_coagulant['quantity'] <= 0:
            inv.objects.remove(self.transmute_coagulant)

        # Check if this is a known spell pattern
        spell_name = None
        for name, spell_def in self.spell_defs.items():
            if spell_def.get('synset') == self.transmute_pattern.get('synset'):
                spell_name = name
                break

        # Need at least 70% completion to succeed
        if completion >= 0.7:
            if spell_name:
                # Add the spell to the spell book so player can cast it!
                spell = self.spell_defs[spell_name]
                synset = spell.get('synset')

                # Create spell book entry with the transmuted spell
                spell_entry = {
                    'name': spell_name.capitalize(),
                    'synset': synset,
                    'definition': spell.get('definition', 'A magical spell'),
                    'composition': spell.get('composition', {}),
                    'type': 'spell',
                    'spell_effect': spell.get('spell_effect'),
                    'power': completion,  # Power level based on transmutation quality
                    'castable': True,  # Mark as a castable spell
                }

                # Add to spell book
                self.spell_book[synset] = spell_entry

                self.add_message(f"TRANSMUTE SUCCESS! Learned {spell_name.upper()}!")
                self.add_message(f"Power: {int(completion*100)}% - Check Spell Book (B) to cast!")

                self.log_action('transmute_spell', {
                    'spell': spell_name,
                    'item': self.transmute_item['name'],
                    'solvent': self.transmute_solvent['name'],
                    'solvent_amount': self.transmute_solvent_amount,
                    'coagulant': self.transmute_coagulant['name'],
                    'coagulant_amount': self.transmute_coagulant_amount,
                    'completion': completion
                })
            else:
                # Create transmuted item and add to spell book
                synset = self.transmute_pattern.get('synset')
                new_entry = {
                    'name': f"Transmuted {self.transmute_pattern['name']}",
                    'synset': synset,
                    'definition': self.transmute_pattern.get('definition', 'A transmuted object'),
                    'composition': self.transmute_pattern.get('composition', {}),
                    'type': self.transmute_pattern.get('type', 'misc'),
                    'power': completion,
                    'transmuted': True,
                }
                self.spell_book[synset] = new_entry
                self.add_message(f"TRANSMUTE SUCCESS! Created {new_entry['name']}!")
                self.add_message(f"Power: {int(completion*100)}% - Added to Spell Book!")

            self.turn += 1
            self.monster_turns()
        else:
            # Failed transmutation
            self.add_message(f"TRANSMUTE FAILED! Only {int(completion*100)}% power (need 70%)")
            self.add_message("Try using more solvent/coagulant or matching affinities")

        # Reset transmute mode
        self.transmute_mode = False
        self.reset_transmute_state()

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
        self.drop_mode = not self.drop_mode
        if self.drop_mode:
            self.add_message("Select item to drop (X to cancel)")
        
    
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
            self.dissolve_mode = False
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

        # Reset dissolve mode
        self.dissolve_mode = False
        self.selected_item = None
        self.selected_solvent = None
    
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
        self.show_inventory_overlay = not getattr(self, 'show_inventory_overlay', False)
        if self.show_inventory_overlay:
            self.inventory_content = self.build_inventory_content()
    
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
        self.game_surface.fill(COLORS['black'])

        self.update_camera()

        # Draw game area
        self.render_dungeon()
        self.render_entities()
        self.render_items()

        # Draw UI
        self.render_sidebar()
        self.render_messages()
        self.render_controls()

        # Note: spell book and inventory overlays are now handled by imgui
    
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
                    pygame.draw.rect(self.game_surface, color, rect)
                    
                    # Draw wall borders
                    if tile == DungeonGenerator.WALL:
                        pygame.draw.rect(self.game_surface, COLORS['dark_gray'], rect, 1)
                    
                    # Draw path if in pathfinding mode
                    if self.path_mode and (world_x, world_y) in self.path:
                        pygame.draw.rect(self.game_surface, COLORS['yellow'], rect, 2)
                    
                    # Draw target position
                    if self.target_pos and (world_x, world_y) == self.target_pos:
                        pygame.draw.rect(self.game_surface, COLORS['green'], rect, 3)
    
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
            pygame.draw.circle(self.game_surface, COLORS['player'], center, TILE_SIZE // 2 - 2)
            pygame.draw.circle(self.game_surface, COLORS['white'], center, TILE_SIZE // 2 - 2, 2)
            
            # @ symbol
            text = self.font.render("@", True, COLORS['white'])
            text_rect = text.get_rect(center=center)
            self.game_surface.blit(text, text_rect)
        
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
                pygame.draw.circle(self.game_surface, COLORS['monster'], center, TILE_SIZE // 2 - 2)
                pygame.draw.circle(self.game_surface, COLORS['dark_red'], center, TILE_SIZE // 2 - 2, 2)
                
                # First letter
                text = self.font.render(monster.name[0].upper(), True, COLORS['white'])
                text_rect = text.get_rect(center=center)
                self.game_surface.blit(text, text_rect)
                
                # Health bar above monster
                hp_pct = monster.stats.current_health / monster.stats.max_health
                bar_width = TILE_SIZE - 4
                bar_rect = pygame.Rect(screen_x + 2, screen_y - 4, int(bar_width * hp_pct), 3)
                bg_rect = pygame.Rect(screen_x + 2, screen_y - 4, bar_width, 3)
                pygame.draw.rect(self.game_surface, COLORS['dark_red'], bg_rect)
                pygame.draw.rect(self.game_surface, COLORS['red'], bar_rect)
    
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
                pygame.draw.polygon(self.game_surface, COLORS['item'], points)
                pygame.draw.polygon(self.game_surface, COLORS['orange'], points, 1)
    
    def render_sidebar(self):
        """Render right sidebar with stats"""
        sidebar_x = self.game_area_width + 20
        y = 10
        
        # Background
        sidebar_rect = pygame.Rect(sidebar_x, 0, self.sidebar_width, SCREEN_HEIGHT)
        pygame.draw.rect(self.game_surface, COLORS['ui_bg'], sidebar_rect)
        pygame.draw.rect(self.game_surface, COLORS['ui_border'], sidebar_rect, 2)
        
        player = self.world.player
        
        # Player name
        title = self.font_large.render(player.name, True, COLORS['white'])
        self.game_surface.blit(title, (sidebar_x + 10, y))
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
        self.game_surface.blit(essence_label, (sidebar_x + 10, y))
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
        self.game_surface.blit(stats_label, (sidebar_x + 10, y))
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
            self.game_surface.blit(text, (sidebar_x + 10, y))
            y += 18
        
        y += 20
        
        # Inventory
        inv_label = self.font.render("INVENTORY", True, COLORS['white'])
        self.game_surface.blit(inv_label, (sidebar_x + 10, y))
        y += 25
        
        if player.inventory.objects:
            # Separate items, solvents, and coagulants for display
            for i, item in enumerate(player.inventory.objects):
                item['index'] = i +1
            # items = [item['index']=i+1 for i, item in enumerate(player.inventory.objects)]
            items = [obj for obj in player.inventory.objects if not obj.get('is_solvent') and not obj.get('is_coagulant')]
            solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
            coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
            
            
            # Show regular items
            if items:
                for i, item in enumerate(items):  # Show first 8 items
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
                        item_text = f"> {item['index']}. {item['name']} <"
                        color = COLORS['yellow']
                    else:
                        item_text = f"{item['index']}. {item['name']}"
                    
                    text = self.font_small.render(item_text, True, color)
                    self.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
                
            # Show solvents
            if solvents:
                y += 5
                solvent_label = self.font_small.render("SOLVENTS:", True, COLORS['yellow'])
                self.game_surface.blit(solvent_label, (sidebar_x + 10, y))
                y += 18
                
                for i, solvent in enumerate(solvents):  # Show first 4 solvents
                    # Highlight if selected in dissolve mode
                    if self.dissolve_mode and self.selected_solvent == solvent:
                        solvent_text = f"> {solvent['index']}. {solvent['name']} <"
                        color = COLORS['yellow']
                    else:
                        solvent_text = f"{solvent['index']}. {solvent['name']}"
                        color = COLORS['yellow']
                    
                    text = self.font_small.render(solvent_text, True, color)
                    self.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
                
            # Show coagulants
            if coagulants:
                y += 5
                coag_label = self.font_small.render("COAGULANTS:", True, COLORS['cyan'])
                self.game_surface.blit(coag_label, (sidebar_x + 10, y))
                y += 18

                for i, coag in enumerate(coagulants):  # Show first 4 coagulants
                    # Highlight if selected in transmute mode
                    if self.transmute_mode and self.transmute_coagulant == coag:
                        coag_text = f"> {coag['index']}. {coag['name']} ({coag.get('quantity', 0)}ml) <"
                        color = COLORS['cyan']
                    else:
                        coag_text = f"{coag['index']}. {coag['name']} ({coag.get('quantity', 0)}ml)"
                        color = COLORS['cyan']

                    text = self.font_small.render(coag_text, True, color)
                    self.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
        else:
            empty_text = self.font_small.render("Empty", True, COLORS['gray'])
            self.game_surface.blit(empty_text, (sidebar_x + 10, y))
            y += 18
        
        y += 15
        
        # Movement mode
        if self.transmute_mode:
            mode_color = COLORS['cyan']
            step_names = ["Item", "Solvent", "Sol.Amt", "Coagulant", "Coag.Amt", "Pattern"]
            mode_text = f"MODE: TRANSMUTE ({step_names[self.transmute_step]})"
        elif self.meditate_mode:
            mode_color = COLORS['purple']
            mode_text = "MODE: MEDITATE"
        elif self.melee_target_mode:
            mode_color = COLORS['red']
            mode_text = "MODE: MELEE TARGET"
        elif self.spell_target_mode:
            player = self.world.player
            spell_range = 3 + int(player.stats.magic_power / 10)
            mode_color = COLORS['purple']
            mode_text = f"MODE: SPELL TARGET ({spell_range} tiles)"
        elif self.ranged_mode:
            mode_color = COLORS['orange']
            mode_text = f"MODE: RANGED ({self.ranged_range} tiles)"
        elif self.dissolve_mode:
            mode_color = COLORS['yellow']
            mode_text = "MODE: DISSOLVE"
        elif self.path_mode:
            mode_color = COLORS['green']
            mode_text = "MODE: PATHFINDING"
        else:
            mode_color = COLORS['white']
            mode_text = "MODE: WASD"

        # Autotarget indicator
        if self.autotarget_mode:
            mode_text += " [AUTO]"
            mode_color = COLORS['cyan']
        mode_label = self.font.render(mode_text, True, mode_color)
        self.game_surface.blit(mode_label, (sidebar_x + 10, y))
        y += 25
        
        # Path info
        if self.path_mode and self.path:
            path_text = f"Path: {len(self.path)} steps"
            path_label = self.font_small.render(path_text, True, COLORS['yellow'])
            self.game_surface.blit(path_label, (sidebar_x + 10, y))
            y += 20
        
        # Visible entities (using FOV system)
        visible = self.get_visible_info(radius=10)
        
        # Monsters with relative positions
        monsters_label = self.font.render("VISIBLE", True, COLORS['white'])
        self.game_surface.blit(monsters_label, (sidebar_x + 10, y))
        y += 25
        
        if visible['monsters']:
            for m in visible['monsters'][:4]:
                # Format: "Goblin:n3e2 (HP)"
                hp_text = f"{m['formatted']} ({m['hp']}/{m['max_hp']})"
                color = COLORS['orange'] if m['adjacent'] else COLORS['red']
                text = self.font_small.render(hp_text, True, color)
                self.game_surface.blit(text, (sidebar_x + 10, y))
                y += 18
        else:
            text = self.font_small.render("No enemies visible", True, COLORS['gray'])
            self.game_surface.blit(text, (sidebar_x + 10, y))
            y += 18
        
        y += 10
        
        # Visible items with relative positions
        items_label = self.font.render("ITEMS", True, COLORS['white'])
        self.game_surface.blit(items_label, (sidebar_x + 10, y))
        y += 25
        
        if visible['items']:
            for item in visible['items'][:5]:
                # Format: "Sword:n2w1"
                item_text = f"{item['formatted']}"
                color = COLORS['yellow'] if item['type'] == 'solvent' else COLORS['item']
                text = self.font_small.render(item_text, True, color)
                self.game_surface.blit(text, (sidebar_x + 10, y))
                y += 16
        else:
            text = self.font_small.render("No items visible", True, COLORS['gray'])
            self.game_surface.blit(text, (sidebar_x + 10, y))
    
    def render_bar(self, x: int, y: int, label: str, 
                   current: float, maximum: float,
                   fg_color, bg_color, bar_width: int = 180):
        """Render a status bar"""
        # Label
        label_text = self.font_small.render(label, True, COLORS['white'])
        self.game_surface.blit(label_text, (x, y))
        
        # Bar background
        bar_x = x + 35
        bar_rect = pygame.Rect(bar_x, y + 2, bar_width, 14)
        pygame.draw.rect(self.game_surface, bg_color, bar_rect)
        
        # Bar fill
        fill_width = int(bar_width * (current / maximum)) if maximum > 0 else 0
        fill_rect = pygame.Rect(bar_x, y + 2, fill_width, 14)
        pygame.draw.rect(self.game_surface, fg_color, fill_rect)
        
        # Border
        pygame.draw.rect(self.game_surface, COLORS['ui_border'], bar_rect, 1)
        
        # Value text
        value_text = self.font_small.render(f"{int(current)}/{int(maximum)}", True, COLORS['white'])
        text_rect = value_text.get_rect(center=(bar_x + bar_width // 2, y + 9))
        self.game_surface.blit(value_text, text_rect)
    
    def render_messages(self):
        """Render message log at bottom"""
        msg_y = self.game_area_height + 30
        
        # Background
        msg_rect = pygame.Rect(10, msg_y - 5, self.game_area_width, 100)
        pygame.draw.rect(self.game_surface, COLORS['ui_bg'], msg_rect)
        pygame.draw.rect(self.game_surface, COLORS['ui_border'], msg_rect, 1)
        
        # Messages
        for i, msg in enumerate(self.messages[-6:]):
            alpha = 128 + int(127 * (i / 6))
            text = self.font_small.render(msg, True, COLORS['light_gray'])
            self.game_surface.blit(text, (15, msg_y + i * 15))
    
    def render_overlay(self, overlay_title, render_text):
         # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(COLORS['black'])
        overlay.set_alpha(200)
        self.game_surface.blit(overlay, (0, 0))

        # Overlay window
        overlay_width = 600
        overlay_height = 500
        overlay_x = (SCREEN_WIDTH - overlay_width) // 2
        overlay_y = (SCREEN_HEIGHT - overlay_height) // 2

        # Background
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.game_surface, COLORS['ui_bg'], overlay_rect)
        pygame.draw.rect(self.game_surface, COLORS['purple'], overlay_rect, 3)

        # Title
        title = self.font_large.render(overlay_title, True, COLORS['purple'])
        title_rect = title.get_rect(centerx=overlay_x + overlay_width // 2, top=overlay_y + 15)
        self.game_surface.blit(title, title_rect)
        
        y = overlay_y + 60
        
        # Render content if provided
        if render_text:
            for line in render_text:
                if line["type"]=="header":
                    header = self.font_large.render(line["text"], True, COLORS[line["color"]])       
                    self.game_surface.blit(header, (overlay_x + 20, y))
                    y += 35
                elif line["type"]=="text":
                    content = self.font.render(line["text"], True, COLORS[line["color"]])
                    self.game_surface.blit(content, (overlay_x + 20, y))
                    y += 25
                elif line["type"]=="seperator":
                    y += 15
                    pygame.draw.line(self.screen, COLORS['ui_border'], (overlay_x + 15, y), (overlay_x + overlay_width - 15, y))
                    y += 15
        else:
            # Show placeholder text when no content provided
            placeholder = self.font.render("No content to display", True, COLORS['gray'])
            self.game_surface.blit(placeholder, (overlay_x + 20, y))

    def render_spell_book(self):

        """Render spell book overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(COLORS['black'])
        overlay.set_alpha(200)
        self.game_surface.blit(overlay, (0, 0))

        # Spell book window
        book_width = 600
        book_height = 500
        book_x = (SCREEN_WIDTH - book_width) // 2
        book_y = (SCREEN_HEIGHT - book_height) // 2

        # Background
        book_rect = pygame.Rect(book_x, book_y, book_width, book_height)
        pygame.draw.rect(self.game_surface, COLORS['ui_bg'], book_rect)
        pygame.draw.rect(self.game_surface, COLORS['purple'], book_rect, 3)

        # Title
        title = self.font_large.render("SPELL BOOK", True, COLORS['purple'])
        title_rect = title.get_rect(centerx=book_x + book_width // 2, top=book_y + 15)
        self.game_surface.blit(title, title_rect)

        # Instructions
        instr = self.font_small.render("Press B to close", True, COLORS['gray'])
        self.game_surface.blit(instr, (book_x + book_width - 120, book_y + 20))

        y = book_y + 60

        if not self.spell_book:
            empty_text = self.font.render("No entries yet. Meditate (Q) on items to learn their essence.", True, COLORS['gray'])
            self.game_surface.blit(empty_text, (book_x + 20, y))
        else:
            # Column headers
            header_color = COLORS['cyan']
            self.game_surface.blit(self.font_small.render("NAME", True, header_color), (book_x + 20, y))
            self.game_surface.blit(self.font_small.render("SYNSET", True, header_color), (book_x + 180, y))
            self.game_surface.blit(self.font_small.render("ESSENCE (F/W/E/A)", True, header_color), (book_x + 350, y))
            y += 25

            # Draw separator line
            pygame.draw.line(self.screen, COLORS['ui_border'], (book_x + 15, y), (book_x + book_width - 15, y))
            y += 10

            # List entries (scrollable area - show first 15)
            entries = list(self.spell_book.values())
            for i, entry in enumerate(entries[:15]):
                # Alternate row colors
                if i % 2 == 0:
                    row_rect = pygame.Rect(book_x + 15, y - 2, book_width - 30, 22)
                    pygame.draw.rect(self.game_surface, (40, 40, 50), row_rect)

                # Name (truncate if too long)
                name = entry['name'][:20] + "..." if len(entry['name']) > 20 else entry['name']
                name_text = self.font_small.render(name, True, COLORS['white'])
                self.game_surface.blit(name_text, (book_x + 20, y))

                # Synset
                synset = entry['synset'][:20] if len(entry['synset']) > 20 else entry['synset']
                synset_text = self.font_small.render(synset, True, COLORS['light_gray'])
                self.game_surface.blit(synset_text, (book_x + 180, y))

                # Essence composition
                comp = entry['composition']
                essence_str = f"F:{comp.get('fire', 0)} W:{comp.get('water', 0)} E:{comp.get('earth', 0)} A:{comp.get('air', 0)}"
                essence_text = self.font_small.render(essence_str, True, COLORS['yellow'])
                self.game_surface.blit(essence_text, (book_x + 350, y))

                y += 22

            # Show count if more entries
            if len(entries) > 15:
                more_text = self.font_small.render(f"...and {len(entries) - 15} more entries", True, COLORS['gray'])
                self.game_surface.blit(more_text, (book_x + 20, y + 10))

        # Footer with total count
        footer_y = book_y + book_height - 30
        pygame.draw.line(self.screen, COLORS['ui_border'], (book_x + 15, footer_y - 10), (book_x + book_width - 15, footer_y - 10))
        count_text = self.font_small.render(f"Total entries: {len(self.spell_book)}", True, COLORS['light_gray'])
        self.game_surface.blit(count_text, (book_x + 20, footer_y))

    def render_controls(self):
        """Render controls help"""
        controls_y = SCREEN_HEIGHT - 30
        if self.show_spell_book:
            controls = "B: Close Spell Book"
        elif self.transmute_mode:
            step_hints = [
                "1-9: Select item | ESC: Cancel",
                "1-9: Select solvent | ESC: Cancel",
                "1-9: Amount (10-90ml), 0: 100ml | ESC: Cancel",
                "1-9: Select coagulant | ESC: Cancel",
                "1-9: Amount (10-90ml), 0: 100ml | ESC: Cancel",
                "1-9: Select pattern | ESC: Cancel | B: View Spell Book",
            ]
            controls = step_hints[self.transmute_step]
        elif self.meditate_mode:
            controls = "1-9: Select item to meditate on | ESC: Cancel | B: View Spell Book"
        elif self.melee_target_mode:
            controls = "LEFT CLICK: Select adjacent enemy to attack | ESC: Cancel"
        elif self.spell_target_mode:
            player = self.world.player
            spell_range = 3 + int(player.stats.magic_power / 10)
            controls = f"LEFT CLICK: Target enemy (range: {spell_range}) | ESC: Cancel spell"
        elif self.dissolve_mode:
            controls = "1-9: Select item/solvent | ESC: Cancel | F: Exit dissolve mode"
        elif self.ranged_mode:
            controls = f"LEFT CLICK: Target enemy (range: {self.ranged_range}) | R: Exit ranged mode | ESC: Cancel"
        elif self.path_mode:
            controls = "LEFT CLICK: Set target | ENTER: Auto-move | RIGHT CLICK/P: Toggle mode | T: Autotarget | ESC: Quit"
        else:
            auto_status = "[AUTO ON]" if self.autotarget_mode else ""
            controls = f"WASD: Move | SPACE: Attack | Q: Meditate | B: Spell Book | T: Auto {auto_status} | ESC: Quit"
        text = self.font_small.render(controls, True, COLORS['gray'])
        self.game_surface.blit(text, (10, controls_y))
    
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
    
    game = PygameGame(seed=seed)
    game.run()


if __name__ == "__main__":
    main()
