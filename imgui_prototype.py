"""
Prototype: Transmutation UI with Dear ImGui + Pygame

This demonstrates how the alchemy/transmutation interface would work
using imgui instead of hand-rolled pygame UI.

Now uses the core.alchemy module for game logic.

Run this standalone to see the UI in action.
"""

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
import imgui
from imgui.integrations.pygame import PygameRenderer
import OpenGL.GL as gl

# Import core game logic
from core.alchemy import AlchemySystem, SpellBookEntry, SOLVENTS, COAGULANTS

# Mock game data for the prototype
MOCK_INVENTORY = [
    {'name': 'Iron Sword', 'synset': 'sword.n.01', 'type': 'weapon'},
    {'name': 'Leather Armor', 'synset': 'armor.n.01', 'type': 'armor'},
    {'name': 'Health Potion', 'synset': 'potion.n.01', 'type': 'potion'},
    {'name': 'Fire Scroll', 'synset': 'scroll.n.01', 'type': 'scroll'},
    {'name': 'Ruby Gem', 'synset': 'gem.n.01', 'type': 'gem'},
]

MOCK_SOLVENTS = [
    {'name': 'Alkahest', 'solvent_type': 'alkahest', 'quantity': 500, 'is_solvent': True},
    {'name': 'Aqua Ignis', 'solvent_type': 'aqua_ignis', 'quantity': 200, 'is_solvent': True},
    {'name': 'Oleum Terra', 'solvent_type': 'oleum_terra', 'quantity': 150, 'is_solvent': True},
]

MOCK_COAGULANTS = [
    {'name': 'Prima Ite', 'coagulant_type': 'prima_ite', 'quantity': 300, 'is_coagulant': True},
    {'name': 'Ite Ignis', 'coagulant_type': 'ite_ignis', 'quantity': 150, 'is_coagulant': True},
    {'name': 'Ite Aqua', 'coagulant_type': 'ite_aqua', 'quantity': 100, 'is_coagulant': True},
]


class TransmuteUI:
    """Handles the transmutation interface using imgui"""

    def __init__(self, alchemy: AlchemySystem):
        self.active = False
        self.step = 0  # 0=item, 1=solvent, 2=solvent_amt, 3=coagulant, 4=coag_amt, 5=pattern

        # Core alchemy system (game logic)
        self.alchemy = alchemy

        # Selections
        self.selected_item_idx = -1
        self.selected_solvent_idx = -1
        self.selected_coagulant_idx = -1
        self.selected_pattern_idx = -1

        # Amounts (as integers for input)
        self.solvent_amount = 50
        self.coagulant_amount = 50

        # Data references (would come from game state)
        self.inventory = MOCK_INVENTORY
        self.solvents = MOCK_SOLVENTS
        self.coagulants = MOCK_COAGULANTS

        # Result messages
        self.last_result_message = ""
        self.last_result_success = False

    def reset(self):
        self.step = 0
        self.selected_item_idx = -1
        self.selected_solvent_idx = -1
        self.selected_coagulant_idx = -1
        self.selected_pattern_idx = -1
        self.solvent_amount = 50
        self.coagulant_amount = 50

    def get_item_essence(self, item):
        """Get essence composition for an item if known (uses alchemy system)"""
        return self.alchemy.get_essence_for_item(item)

    def render(self):
        """Render the transmutation window"""
        if not self.active:
            return

        imgui.set_next_window_size(700, 500, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(100, 100, imgui.FIRST_USE_EVER)

        expanded, self.active = imgui.begin("Transmutation", True)
        if not expanded:
            imgui.end()
            return

        # Split into two columns
        imgui.columns(2, "transmute_columns", True)
        imgui.set_column_width(0, 380)

        # === LEFT COLUMN: Current Step ===
        self._render_left_panel()

        imgui.next_column()

        # === RIGHT COLUMN: Known Essences ===
        self._render_right_panel()

        imgui.columns(1)

        # Bottom bar with action buttons
        imgui.separator()
        if imgui.button("Cancel [ESC]"):
            self.active = False
            self.reset()

        imgui.same_line()

        # Show transmute button when all selections are made
        if self._can_transmute():
            imgui.same_line(imgui.get_window_width() - 120)
            if imgui.button("TRANSMUTE!"):
                self._do_transmute()

        imgui.end()

    def _render_left_panel(self):
        """Render the left panel with current step and selections"""
        step_names = ["Select Item", "Select Solvent", "Solvent Amount",
                      "Select Coagulant", "Coagulant Amount", "Select Pattern"]

        imgui.text_colored(f"Step {self.step + 1}/6: {step_names[self.step]}", 0.4, 0.8, 1.0)
        imgui.separator()

        # Show current selections
        imgui.text("Current Selections:")

        if self.selected_item_idx >= 0:
            item = self.inventory[self.selected_item_idx]
            imgui.bullet_text(f"Item: {item['name']}")
            essence = self.get_item_essence(item)
            if essence:
                imgui.same_line()
                self._render_essence_inline(essence)
            else:
                imgui.same_line()
                imgui.text_colored("(unknown essence)", 1.0, 0.3, 0.3)

        if self.selected_solvent_idx >= 0:
            solvent = self.solvents[self.selected_solvent_idx]
            imgui.bullet_text(f"Solvent: {solvent['name']} ({self.solvent_amount}ml)")

        if self.selected_coagulant_idx >= 0:
            coag = self.coagulants[self.selected_coagulant_idx]
            imgui.bullet_text(f"Coagulant: {coag['name']} ({self.coagulant_amount}ml)")

        if self.selected_pattern_idx >= 0:
            patterns = self.alchemy.get_known_essences()
            if self.selected_pattern_idx < len(patterns):
                imgui.bullet_text(f"Pattern: {patterns[self.selected_pattern_idx].name}")

        imgui.spacing()
        imgui.separator()
        imgui.spacing()

        # Render current step options
        if self.step == 0:
            self._render_item_selection()
        elif self.step == 1:
            self._render_solvent_selection()
        elif self.step == 2:
            self._render_solvent_amount()
        elif self.step == 3:
            self._render_coagulant_selection()
        elif self.step == 4:
            self._render_coagulant_amount()
        elif self.step == 5:
            self._render_pattern_selection()

    def _render_item_selection(self):
        """Render item selection list"""
        imgui.text("Select an item to transmute:")
        imgui.spacing()

        for i, item in enumerate(self.inventory):
            # Show essence preview if known
            essence = self.get_item_essence(item)
            label = f"{item['name']}"

            clicked, _ = imgui.selectable(label, self.selected_item_idx == i)
            if clicked:
                self.selected_item_idx = i
                self.step = 1

            if essence:
                imgui.same_line(200)
                self._render_essence_inline(essence)

    def _render_solvent_selection(self):
        """Render solvent selection list"""
        imgui.text("Select a solvent:")
        imgui.spacing()

        for i, solvent in enumerate(self.solvents):
            label = f"{solvent['name']} ({solvent['quantity']}ml available)"
            clicked, _ = imgui.selectable(label, self.selected_solvent_idx == i)
            if clicked:
                self.selected_solvent_idx = i
                self.solvent_amount = min(50, solvent['quantity'])
                self.step = 2

    def _render_solvent_amount(self):
        """Render solvent amount input"""
        if self.selected_solvent_idx < 0:
            return

        solvent = self.solvents[self.selected_solvent_idx]
        max_amt = solvent['quantity']

        imgui.text(f"Enter solvent amount (max {max_amt}ml):")
        imgui.spacing()

        # Slider for amount
        changed, self.solvent_amount = imgui.slider_int(
            "##solvent_amt", self.solvent_amount, 1, max_amt, f"{self.solvent_amount}ml"
        )

        # Quick buttons
        imgui.spacing()
        if imgui.button("25ml"):
            self.solvent_amount = min(25, max_amt)
        imgui.same_line()
        if imgui.button("50ml"):
            self.solvent_amount = min(50, max_amt)
        imgui.same_line()
        if imgui.button("100ml"):
            self.solvent_amount = min(100, max_amt)
        imgui.same_line()
        if imgui.button("Max"):
            self.solvent_amount = max_amt

        imgui.spacing()
        if imgui.button("Confirm Amount"):
            self.step = 3

    def _render_coagulant_selection(self):
        """Render coagulant selection list"""
        imgui.text("Select a coagulant:")
        imgui.spacing()

        for i, coag in enumerate(self.coagulants):
            label = f"{coag['name']} ({coag['quantity']}ml available)"
            clicked, _ = imgui.selectable(label, self.selected_coagulant_idx == i)
            if clicked:
                self.selected_coagulant_idx = i
                self.coagulant_amount = min(50, coag['quantity'])
                self.step = 4

    def _render_coagulant_amount(self):
        """Render coagulant amount input"""
        if self.selected_coagulant_idx < 0:
            return

        coag = self.coagulants[self.selected_coagulant_idx]
        max_amt = coag['quantity']

        imgui.text(f"Enter coagulant amount (max {max_amt}ml):")
        imgui.spacing()

        changed, self.coagulant_amount = imgui.slider_int(
            "##coag_amt", self.coagulant_amount, 1, max_amt, f"{self.coagulant_amount}ml"
        )

        imgui.spacing()
        if imgui.button("25ml##c"):
            self.coagulant_amount = min(25, max_amt)
        imgui.same_line()
        if imgui.button("50ml##c"):
            self.coagulant_amount = min(50, max_amt)
        imgui.same_line()
        if imgui.button("100ml##c"):
            self.coagulant_amount = min(100, max_amt)
        imgui.same_line()
        if imgui.button("Max##c"):
            self.coagulant_amount = max_amt

        imgui.spacing()
        if imgui.button("Confirm Amount##c"):
            self.step = 5

    def _render_pattern_selection(self):
        """Render pattern (essence) selection from spell book"""
        imgui.text("Select target pattern from known essences:")
        imgui.spacing()

        patterns = self.alchemy.get_known_essences()
        for i, entry in enumerate(patterns):
            comp = entry.composition
            label = f"{entry.name}"

            clicked, _ = imgui.selectable(label, self.selected_pattern_idx == i)
            if clicked:
                self.selected_pattern_idx = i

            imgui.same_line(180)
            self._render_essence_inline(comp)

    def _render_right_panel(self):
        """Render the right panel with known essences"""
        imgui.text_colored("Known Essences (Spell Book)", 0.8, 0.4, 1.0)
        imgui.separator()

        known = self.alchemy.get_known_essences()
        if not known:
            imgui.text_colored("No essences known!", 0.5, 0.5, 0.5)
            imgui.text("Meditate (Q) on items")
            imgui.text("to learn their essence.")
            return

        # Table header
        imgui.columns(5, "essence_table", True)
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
        return (self.selected_item_idx >= 0 and
                self.selected_solvent_idx >= 0 and
                self.selected_coagulant_idx >= 0 and
                self.selected_pattern_idx >= 0)

    def _do_transmute(self):
        """Execute the transmutation using the alchemy system"""
        item = self.inventory[self.selected_item_idx]
        solvent = self.solvents[self.selected_solvent_idx]
        coagulant = self.coagulants[self.selected_coagulant_idx]
        patterns = self.alchemy.get_known_essences()
        pattern = patterns[self.selected_pattern_idx]

        # Call the core alchemy system
        result = self.alchemy.transmute(
            item=item,
            solvent=solvent,
            solvent_amount=self.solvent_amount,
            coagulant=coagulant,
            coagulant_amount=self.coagulant_amount,
            pattern=pattern
        )

        # Store result for display
        self.last_result_message = result.message
        self.last_result_success = result.success

        # Update reagent quantities (in real game, inventory would handle this)
        if result.success:
            solvent['quantity'] = result.details.get('solvent_remaining', 0)
            coagulant['quantity'] = result.details.get('coagulant_remaining', 0)

        print(f"Transmutation: {result.message}")

        self.active = False
        self.reset()


def main():
    """Run the prototype"""
    pygame.init()

    # Need OpenGL context for imgui
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
    pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
    screen = pygame.display.set_mode((900, 600), DOUBLEBUF | OPENGL | pygame.RESIZABLE)
    pygame.display.set_caption("Elemental - ImGui Prototype")
    clock = pygame.time.Clock()

    # Initialize imgui
    imgui.create_context()
    impl = PygameRenderer()

    io = imgui.get_io()
    io.display_size = screen.get_size()

    # Create alchemy system (core game logic)
    alchemy = AlchemySystem()

    # Pre-populate spell book by "meditating" on items
    for item in MOCK_INVENTORY:
        alchemy.meditate(item)

    # Create UI with alchemy system
    transmute_ui = TransmuteUI(alchemy)
    transmute_ui.active = True  # Start with it open for demo

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if transmute_ui.active:
                        transmute_ui.active = False
                        transmute_ui.reset()
                    else:
                        running = False
                elif event.key == pygame.K_g:
                    transmute_ui.active = not transmute_ui.active
                    if transmute_ui.active:
                        transmute_ui.reset()
                elif event.key == pygame.K_q:
                    # Demo: meditate on a random item
                    import random
                    item = random.choice(MOCK_INVENTORY)
                    result = alchemy.meditate(item)
                    print(f"Meditate: {result.message}")

            impl.process_event(event)

        impl.process_inputs()

        imgui.new_frame()

        # Demo window with instructions
        imgui.set_next_window_position(10, 10, imgui.FIRST_USE_EVER)
        imgui.begin("Controls", False)
        imgui.text("Press G to toggle Transmutation UI")
        imgui.text("Press Q to meditate on random item")
        imgui.text("Press ESC to close/exit")
        imgui.separator()
        imgui.text_colored("Now using core.alchemy module!", 0.4, 1.0, 0.4)
        imgui.text_colored(f"Known essences: {len(alchemy.get_known_essences())}", 0.7, 0.7, 0.7)
        imgui.end()

        # Render transmute UI
        transmute_ui.render()

        # Render
        gl.glClearColor(0.12, 0.12, 0.16, 1.0)  # Dark background
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        imgui.render()
        impl.render(imgui.get_draw_data())

        pygame.display.flip()
        clock.tick(60)

    impl.shutdown()
    pygame.quit()


if __name__ == "__main__":
    main()
