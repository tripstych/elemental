# ============================================================================
# IMGUI UI CLASS
# ============================================================================
import imgui

from constants import *

class ImguiUI:
    """Handles all imgui-based overlay rendering"""

    def __init__(self, game):
        self.game = game
        # Selection indices for keyboard navigation (per menu)
        self._selection_indices = {}
        # List selection state
        self._list_selection_indices = {}

        # Transmutation state
        self._transmute_step = 0  # 0=item, 1=pattern (auto-calc amounts)
        self._transmute_item = None
        self._transmute_solvent = None
        self._transmute_solvent_amount = 0
        self._transmute_coagulant = None
        self._transmute_coagulant_amount = 0
        self._transmute_pattern = None

        # Spell speaking state
        self._speak_mode = False
        self._speak_step = 0  # 0=select item, 1=compose phrase
        self._speak_item = None
        self._speak_phrase = ""
        self._speak_element_filter = None  # None or element name

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

    def render_list_selection(self, items, title="Select an item", prompt="Use number keys to select", 
                            list_id="default", show_cancel=True, show_spell_book=True,
                            on_select=None, on_close=None):
        """Abstracted ImGui function to render a list selection interface
        
        Args:
            items: List of items to display (can be strings or objects with str representation)
            title: Title to display above the list
            prompt: Prompt text to display below the list
            list_id: Unique identifier for this list (for selection tracking)
            show_cancel: Whether to show cancel option
            show_spell_book: Whether to show spell book option
            on_select: Callback function when item is selected (index, item)
            on_close: Callback function when window is closed
        """
        imgui.set_next_window_size(400, 350, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 175,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin(title, True)
        if not opened:
            if on_close:
                on_close()
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        imgui.text_colored(prompt, 0.4, 0.8, 1.0)
        imgui.text_colored("(Arrow keys to navigate, ENTER to select, or click)", 0.5, 0.5, 0.5)
        imgui.separator()
        imgui.spacing()

        if not items:
            imgui.text_colored("No items available!", 0.8, 0.3, 0.3)
        else:
            # Get or initialize selection index for this list
            if list_id not in self._list_selection_indices:
                self._list_selection_indices[list_id] = 0
            selected_index = self._list_selection_indices[list_id]
            
            # Arrow key navigation
            if imgui.is_key_pressed(imgui.KEY_UP_ARROW) and selected_index > 0:
                selected_index -= 1
                self._list_selection_indices[list_id] = selected_index
            elif imgui.is_key_pressed(imgui.KEY_DOWN_ARROW) and selected_index < len(items) - 1:
                selected_index += 1
                self._list_selection_indices[list_id] = selected_index
            elif imgui.is_key_pressed(imgui.KEY_ENTER) and on_select:
                try:
                    if items[selected_index]:
                        on_select(selected_index, items[selected_index])
                except IndexError:
                        print("> < what's up doc?")
                        traceback.print_exc()
            
            for i, item in enumerate(items):
                item_str = str(item)
                if len(item_str) > 40:  # Truncate long items
                    item_str = item_str
                
                label = f"{i+1}: {item_str}"
                if i == selected_index:
                    label = f"> {label} <"
                
                clicked, _ = imgui.selectable(label, i == selected_index)
                if clicked and on_select:
                    self._list_selection_indices[list_id] = i
                    on_select(i, items[i])

        imgui.spacing()
        imgui.separator()
        
        # Buttons
        if show_cancel:
            if imgui.button("Cancel [ESC]") or imgui.is_key_pressed(imgui.KEY_ESCAPE):
                if on_close:
                    on_close()
        
        if show_spell_book:
            imgui.same_line()
            if imgui.button("Spell Book [B]"):
                self.game.show_spell_book = True

        imgui.end()

    def render(self):
        """Render all active imgui windows"""
        if self.game.show_spell_book:
            self._render_spell_book()
        if self.game.meditate_mode:
            self._render_meditate()
        if self.game.show_drop_menu:
            self._render_drop_menu()
        if self.game.show_inventory_ui:
            self._render_inventory()
        if self._speak_mode:
            self._render_speak_spell()

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
                comp = entry.composition
                name = entry.name
                synset = entry.synset

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
        """Render meditation item selection using abstracted list selection"""
        if not self.game.meditate_mode:
            return
            
        player = self.game.world.player
        
        # Get non-reagent items
        items = [obj for obj in player.inventory.objects
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]

        if not items:
            self.game.add_message("No items to meditate on!")
            self.game.meditate_mode = False
            return

        # Create display names for items
        def get_item_display(obj, i):
            synset = obj.get('synset')
            is_known = synset and synset in self.game.spell_book
            suffix = " (known)" if is_known else ""
            return f"{obj['name']}{suffix}"
        
        display_items = [get_item_display(obj, i) for i, obj in enumerate(items)]
        
        def on_meditate_select(index, display_item):
            # Get the actual item object (use same items list, no limit)
            if index < len(items):
                self._do_meditate(items[index])
        
        def on_meditate_close():
            self.game.meditate_mode = False
            self.reset_selection("meditate")
        
        # Use the abstracted list selection function
        self.render_list_selection(
            items=display_items,
            title="Meditate",
            prompt="Select an item to study its essence:",
            list_id="meditate",
            show_cancel=True,
            show_spell_book=True,
            on_select=on_meditate_select,
            on_close=on_meditate_close
        )

    def _render_drop_menu(self):
        """Render drop item selection using abstracted list selection"""
        if not self.game.show_drop_menu:
            return

        player = self.game.world.player

        # Get all items from inventory (no limit)
        items = player.inventory.objects

        if not items:
            self.game.add_message("No items to drop!")
            self.game.show_drop_menu = False
            return

        # Create display names for items
        display_items = [f"{obj['name']}" for obj in items]

        def on_drop_select(index, display_item):
            # Drop item by its index in the list
            if index < len(items):
                self.game.drop_item(items[index].get('index', index + 1))
        
        def on_drop_close():
            self.game.show_drop_menu = False
        
        # Use the abstracted list selection function
        self.render_list_selection(
            items=display_items,
            title="Drop Item",
            prompt="Select an item to drop:",
            list_id="drop",
            show_cancel=True,
            show_spell_book=False,
            on_select=on_drop_select,
            on_close=on_drop_close
        )

    def _render_inventory(self):
        """Render detailed inventory using ImGui"""
        if not self.game.show_inventory_ui:
            return
            
        imgui.set_next_window_size(600, 500, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT // 2 - 250,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Inventory", True)
        if not opened:
            self.game.show_inventory_ui = False
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        player = self.game.world.player
        inv = player.inventory

        # Player stats header
        imgui.text_colored(f"Player: {player.name}", 0.8, 0.8, 1.0)
        total_weight = inv.get_total_weight()
        imgui.text(f"Weight: {total_weight:.1f}/{inv.max_weight:.1f}")
        imgui.separator()
        imgui.spacing()

        # Separate items by type
        items = [obj for obj in inv.objects if not obj.get('is_solvent') and not obj.get('is_coagulant') and obj.get('type') not in ['weapon', 'weapons']]
        weapons = [obj for obj in inv.objects if obj.get('type') in ['weapon', 'weapons']]
        solvents = [obj for obj in inv.objects if obj.get('is_solvent')]
        coagulants = [obj for obj in inv.objects if obj.get('is_coagulant')]

        # Items section
        if items:
            imgui.text_colored("ITEMS", 1.0, 1.0, 1.0)
            imgui.separator()
            for i, item in enumerate(items):
                imgui.text(f"{i+1}. {item['name']}")
                if imgui.is_item_hovered():
                    imgui.set_tooltip(f"Type: {item.get('type', 'unknown')}")
        else:
            imgui.text_colored("No items", 0.5, 0.5, 0.5)

        # Weapons section
        if weapons:
            imgui.spacing()
            imgui.text_colored("WEAPONS", 1.0, 0.6, 0.2)
            imgui.separator()
            for i, weapon in enumerate(weapons):
                imgui.text(f"{i+1}. {weapon['name']}")
                if imgui.is_item_hovered():
                    imgui.set_tooltip(f"Type: {weapon.get('type', 'unknown')}")
        
        # Solvents section
        if solvents:
            imgui.spacing()
            imgui.text_colored("SOLVENTS", 1.0, 1.0, 0.2)
            imgui.separator()
            for i, solvent in enumerate(solvents):
                qty = solvent.get('quantity', 0)
                imgui.text(f"{i+1}. {solvent['name']} ({qty}ml)")
                if imgui.is_item_hovered():
                    imgui.set_tooltip(f"Quantity: {qty}ml")
        
        # Coagulants section
        if coagulants:
            imgui.spacing()
            imgui.text_colored("COAGULANTS", 0.2, 1.0, 1.0)
            imgui.separator()
            for i, coag in enumerate(coagulants):
                qty = coag.get('quantity', 0)
                imgui.text(f"{i+1}. {coag['name']} ({qty}ml)")
                if imgui.is_item_hovered():
                    imgui.set_tooltip(f"Quantity: {qty}ml")

        # Essences section
        imgui.spacing()
        imgui.text_colored("ESSENCES", 0.6, 0.2, 1.0)
        imgui.separator()
        for elem, amount in inv.essences.items():
            imgui.text(f"{elem.upper()}: {amount}")

        imgui.spacing()
        imgui.separator()
        
        if imgui.button("Close [I]"):
            self.game.show_inventory_ui = False

        imgui.end()

    def _do_meditate(self, obj):
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

    def _render_essence_inline(self, comp):
        """Render essence values inline with colors"""
        imgui.text_colored(f"F:{comp.get('fire', 0)}", 1.0, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"W:{comp.get('water', 0)}", 0.2, 0.6, 1.0)
        imgui.same_line()
        imgui.text_colored(f"E:{comp.get('earth', 0)}", 0.6, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"A:{comp.get('air', 0)}", 0.7, 0.7, 1.0)

    # =========================================================================
    # SPELL SPEAKING MODE
    # =========================================================================

    @property
    def speak_mode(self):
        """Check if speak mode is active"""
        return self._speak_mode

    def toggle_speak_mode(self):
        """Toggle spell speaking mode"""
        self._speak_mode = not self._speak_mode
        if self._speak_mode:
            self._reset_speak()
            self.game.add_message("SPEAK: Select an item to enchant")
        else:
            self.game.add_message("Spell speaking cancelled")

    def _reset_speak(self):
        """Reset spell speaking state"""
        self._speak_step = 0
        self._speak_item = None
        self._speak_phrase = ""
        self._speak_element_filter = None
        self.reset_selection("speak_item")

    def _render_speak_spell(self):
        """Render the spell speaking interface"""
        imgui.set_next_window_size(800, 650, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 400, SCREEN_HEIGHT // 2 - 275,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Speak Spell", True)
        if not opened:
            self._speak_mode = False
            self._reset_speak()
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        # Two-column layout
        imgui.columns(2, "speak_cols", True)
        imgui.set_column_width(0, 450)

        # Left panel: composition or item selection
        if self._speak_step == 0:
            self._render_speak_item_select()
        else:
            self._render_speak_compose()

        imgui.next_column()

        # Right panel: syllable reference
        self._render_syllable_reference()

        imgui.columns(1)

        # Bottom bar
        imgui.separator()
        if imgui.button("Cancel [ESC]") or imgui.is_key_pressed(imgui.KEY_ESCAPE):
            self._speak_mode = False
            self._reset_speak()

        if self._speak_step > 0:
            imgui.same_line()
            if imgui.button("< Back"):
                self._speak_step = 0
                self._speak_phrase = ""

        # Cast buttn
        if self._speak_item and self._speak_phrase.strip():
            imgui.same_line(imgui.get_window_width() - 250)
            if imgui.button("SPEAK SPELL!"):
                self._do_speak_spell()

        imgui.end()

    def _render_speak_item_select(self):
        """Step 0: Select target item"""
        imgui.text_colored("Select an item to enchant:", 0.4, 0.8, 1.0)
        imgui.text_colored("(Click or use arrow keys + ENTER)", 0.5, 0.5, 0.5)
        imgui.separator()
        imgui.spacing()

        player = self.game.world.player
        items = [obj for obj in player.inventory.objects
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]

        if not items:
            imgui.text_colored("No items available!", 0.8, 0.3, 0.3)
            return

        def select_item(item):
            self._speak_item = item
            self._speak_step = 1
            self.reset_selection("speak_item")

        def label_fn(item, i):
            weight = item.get('weight', 1.0)
            return f"{i+1}. {item['name']} ({weight:.1f}kg)"

        self._render_selectable_list(
            list_id="speak_item",
            items=items,
            label_fn=label_fn,
            on_select=select_item
        )

    def _render_speak_compose(self):
        """Step 1: Compose the spoken phrase"""
        imgui.text_colored("Compose your spell phrase:", 0.4, 0.8, 1.0)
        imgui.separator()

        # Show selected item
        if self._speak_item:
            weight = self._speak_item.get('weight', 1.0)
            imgui.text(f"Target: {self._speak_item['name']} ({weight:.1f}kg)")

            # Show conduit limit
            conduit = self.game.controller.get_player_conduit_limit()
            imgui.same_line()
            imgui.text_colored(f"Conduit: {conduit}", 0.7, 0.7, 1.0)

        imgui.spacing()

        # Text input for phrase
        imgui.text("Speak:")
        imgui.same_line()
        changed, self._speak_phrase = imgui.input_text(
            "##phrase", self._speak_phrase, 256
        )

        # Parse and preview
        if self._speak_phrase.strip():
            preview = self.game.controller.parse_spoken_phrase(self._speak_phrase)
            imgui.spacing()

            # Show vectors
            imgui.text("Elemental Power:")
            imgui.same_line()
            self._render_vector_inline(preview['vectors'])

            # Calculate load
            item_weight = self._speak_item.get('weight', 1.0) if self._speak_item else 1.0
            load = self.game.controller.calculate_spell_load(self._speak_phrase, item_weight)
            conduit = self.game.controller.get_player_conduit_limit()

            imgui.text(f"Load: {int(load)}/{conduit}")
            if load > conduit:
                overload = int(load - conduit)
                imgui.same_line()
                imgui.text_colored(f"OVERLOAD! -{overload} HP", 1.0, 0.3, 0.3)

            # Unknown words warning
            if preview['unknown_words']:
                imgui.text_colored(
                    f"Unknown: {', '.join(preview['unknown_words'])}",
                    1.0, 0.5, 0.2
                )

            # Dominant element
            if preview['dominant_element']:
                imgui.text(f"Dominant: {preview['dominant_element'].upper()}")

        imgui.spacing()
        imgui.separator()

        # Quick add buttons by element
        imgui.text("Quick add syllables:")
        elements = ['earth', 'water', 'fire', 'air']
        element_colors = {
            'earth': (0.6, 0.4, 0.2),
            'water': (0.2, 0.6, 1.0),
            'fire': (1.0, 0.4, 0.2),
            'air': (0.7, 0.7, 1.0)
        }

        for elem in elements:
            color = element_colors[elem]
            syllables = self.game.controller.get_elemental_syllables(elem)

            imgui.text_colored(f"{elem.upper()}:", *color)
            imgui.same_line()

            # Show first 6 syllables as buttons
            for i, syl in enumerate(syllables[:6]):
                if i > 0:
                    imgui.same_line()
                if imgui.small_button(f"{syl['spelling']}({syl['value']})##{elem}{i}"):
                    if self._speak_phrase:
                        self._speak_phrase += " " + syl['spelling']
                    else:
                        self._speak_phrase = syl['spelling']

        # Clear button
        imgui.spacing()
        if imgui.button("Clear Phrase"):
            self._speak_phrase = ""

    def _render_syllable_reference(self):
        """Render syllable reference panel"""
        imgui.text_colored("Elemental Syllables", 0.8, 0.4, 1.0)
        imgui.separator()

        # Filter buttons
        imgui.text("Filter:")
        if imgui.small_button("All"):
            self._speak_element_filter = None
        imgui.same_line()
        if imgui.small_button("Earth"):
            self._speak_element_filter = 'earth'
        imgui.same_line()
        if imgui.small_button("Water"):
            self._speak_element_filter = 'water'
        imgui.same_line()
        if imgui.small_button("Fire"):
            self._speak_element_filter = 'fire'
        imgui.same_line()
        if imgui.small_button("Air"):
            self._speak_element_filter = 'air'

        imgui.separator()

        # Scrollable list
        imgui.begin_child("syllables", 0, 350, True)

        elements_to_show = [self._speak_element_filter] if self._speak_element_filter else ['earth', 'water', 'fire', 'air']

        element_colors = {
            'earth': (0.6, 0.4, 0.2),
            'water': (0.2, 0.6, 1.0),
            'fire': (1.0, 0.4, 0.2),
            'air': (0.7, 0.7, 1.0)
        }

        for elem in elements_to_show:
            color = element_colors.get(elem, (1, 1, 1))
            syllables = self.game.controller.get_elemental_syllables(elem)

            imgui.text_colored(f"--- {elem.upper()} ---", *color)

            for syl in syllables:
                # Clickable syllable
                clicked, _ = imgui.selectable(
                    f"  {syl['spelling']:8} ({syl['value']:2}) - {syl['quality'][:30]}..."
                )
                if clicked:
                    if self._speak_phrase:
                        self._speak_phrase += " " + syl['spelling']
                    else:
                        self._speak_phrase = syl['spelling']

        imgui.end_child()

    def _render_vector_inline(self, vectors):
        """Render elemental vectors inline with colors"""
        imgui.text_colored(f"F:{int(vectors.get('fire', 0))}", 1.0, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"W:{int(vectors.get('water', 0))}", 0.2, 0.6, 1.0)
        imgui.same_line()
        imgui.text_colored(f"E:{int(vectors.get('earth', 0))}", 0.6, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"A:{int(vectors.get('air', 0))}", 0.7, 0.7, 1.0)

    def _do_speak_spell(self):
        """Execute the spoken spell"""
        if not self._speak_item or not self._speak_phrase.strip():
            return

        result = self.game.controller.speak_spell(
            phrase=self._speak_phrase,
            target_item=self._speak_item
        )

        self.game.add_message(result.message)

        if result.success:
            # Show item transformation
            data = result.data or {}
            if data.get('burn_damage', 0) > 0:
                self.game.add_message(f"You take {data['burn_damage']} burn damage from overload!")

        self._speak_mode = False
        self._reset_speak()

