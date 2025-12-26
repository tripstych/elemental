# ============================================================================
# TRANSMUTATION ENGINE CLASS
# ============================================================================
import pygame

from constants import *

class TransmutationEngine:
    """Handles all transmutation logic and state management"""

    def __init__(self, game):
        self.game = game
        
        # Transmutation mode - single action: item + solvent + coagulant + spell pattern -> cast
        self.transmute_mode = False
        self.transmute_step = 0  # 0=select item, 1=select solvent, 2=solvent amount, 3=select coagulant, 4=coagulant amount, 5=select pattern
        self.transmute_item = None
        self.transmute_solvent = None
        self.transmute_solvent_amount = 0
        self.transmute_coagulant = None
        self.transmute_coagulant_amount = 0
        self.transmute_pattern = None  # Spell book entry to create

    def reset_state(self):
        """Reset all transmutation state"""
        self.transmute_step = 0
        self.transmute_item = None
        self.transmute_solvent = None
        self.transmute_solvent_amount = 0
        self.transmute_coagulant = None
        self.transmute_coagulant_amount = 0
        self.transmute_pattern = None

    def toggle_mode(self):
        """Toggle transmutation mode - single action spell casting"""
        player = self.game.world.player

        # Check if player has any items to transmute
        items = [obj for obj in player.inventory.objects
                 if not obj.get('is_solvent') and not obj.get('is_coagulant')]
        if not items:
            self.game.add_message("No items to transmute!")
            return

        # Check if player has solvents
        solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
        if not solvents:
            self.game.add_message("No solvents in inventory!")
            return

        # Check if player has coagulants
        coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
        if not coagulants:
            self.game.add_message("No coagulants in inventory!")
            return

        self.transmute_mode = not self.transmute_mode
        if self.transmute_mode:
            self.reset_state()
            self.game.add_message("TRANSMUTE: Select source item (1-9)")
        else:
            self.game.add_message("Transmutation cancelled")

    def handle_input(self, event):
        """Handle keyboard input during transmutation"""
        player = self.game.world.player

        # ESC cancels
        if event.key == pygame.K_ESCAPE:
            self.transmute_mode = False
            self.reset_state()
            self.game.add_message("Transmutation cancelled")
            return

        # Number key selection
        if pygame.K_0 <= event.key <= pygame.K_9:
            index = event.key - pygame.K_0
            self.handle_selection(index)
            return

    def handle_selection(self, index: int):
        """Handle selection at current transmutation step"""
        player = self.game.world.player

        if self.transmute_step == 0:
            # Step 0: Select item
            items = [obj for obj in player.inventory.objects
                     if not obj.get('is_solvent') and not obj.get('is_coagulant')]
            if index >= len(items):
                self.game.add_message("No item at that slot!")
                return
            self.transmute_item = items[index]
            self.transmute_step = 1
            self.game.add_message(f"Item: {self.transmute_item['name']}")
            self.game.add_message("Select solvent (1-9)")

        elif self.transmute_step == 1:
            # Step 1: Select solvent
            solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
            if index >= len(solvents):
                self.game.add_message("No solvent at that slot!")
                return
            self.transmute_solvent = solvents[index]
            self.transmute_step = 2
            max_amt = self.transmute_solvent.get('quantity', 0)
            self.game.add_message(f"Solvent: {self.transmute_solvent['name']} ({max_amt}ml)")
            self.game.add_message(f"Select amount: 1-9 for 10-90ml, 0 for 100ml (max {max_amt}ml)")

        elif self.transmute_step == 2:
            # Step 2: Select solvent amount (1-9 = 10-90ml, 0 = 100ml)
            amount = (index + 1) * 10  # 1->10, 2->20, ..., 9->90, 0->100
            if index == 9:
                amount = 100
            max_amt = self.transmute_solvent.get('quantity', 0)
            if amount > max_amt:
                amount = max_amt
            if amount <= 0:
                self.game.add_message("No solvent available!")
                return
            self.transmute_solvent_amount = amount
            self.transmute_step = 3
            self.game.add_message(f"Using {amount}ml solvent")
            self.game.add_message("Select coagulant (1-9)")

        elif self.transmute_step == 3:
            # Step 3: Select coagulant
            coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
            if index >= len(coagulants):
                self.game.add_message("No coagulant at that slot!")
                return
            self.transmute_coagulant = coagulants[index]
            self.transmute_step = 4
            max_amt = self.transmute_coagulant.get('quantity', 0)
            self.game.add_message(f"Coagulant: {self.transmute_coagulant['name']} ({max_amt}ml)")
            self.game.add_message(f"Select amount: 1-9 for 10-90ml, 0 for 100ml (max {max_amt}ml)")

        elif self.transmute_step == 4:
            # Step 4: Select coagulant amount
            amount = (index + 1) * 10
            if index == 9:
                amount = 100
            max_amt = self.transmute_coagulant.get('quantity', 0)
            if amount > max_amt:
                amount = max_amt
            if amount <= 0:
                self.game.add_message("No coagulant available!")
                return
            self.transmute_coagulant_amount = amount
            self.transmute_step = 5
            self.game.add_message(f"Using {amount}ml coagulant")
            self.game.add_message("Select spell pattern from Spell Book (1-9)")

        elif self.transmute_step == 5:
            # Step 5: Select spell pattern from spell book
            entries = list(self.game.spell_book.values())
            if index >= len(entries):
                self.game.add_message("No pattern at that slot!")
                return
            self.transmute_pattern = entries[index]
            self.game.add_message(f"Pattern: {self.transmute_pattern['name']}")
            # Now perform the transmutation!
            self.perform_transmutation()

    def perform_transmutation(self):
        """Execute the transmutation - extract essence and form spell in one action"""
        player = self.game.world.player
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

        # Coagulant affects binding efficiency and has elemental affinity
        coag_strength = coag_data.get('strength', 1.0)
        coag_affinity = coag_data.get('affinity', [])

        # Calculate how much of each element we can bind
        bound_essence = {}
        for elem, required in pattern_comp.items():
            available = extracted_essence.get(elem, 0)
            # Affinity bonus
            if elem in coag_affinity:
                effective_available = available * (1.0 + coag_strength * 0.5)
            else:
                effective_available = available * coag_strength

            bound_amount = min(effective_available, required)
            bound_essence[elem] = bound_amount

        # Check if we have enough essence to create the spell
        can_create = all(
            bound_essence.get(elem, 0) >= required
            for elem, required in pattern_comp.items()
        )

        if not can_create:
            self.game.add_message("Insufficient essence to create this pattern!")
            self.game.add_message("Try using more solvent or different materials.")
            return

        # Consume materials
        inv.remove_object(self.transmute_item)
        inv.remove_quantity(self.transmute_solvent, self.transmute_solvent_amount)
        inv.remove_quantity(self.transmute_coagulant, self.transmute_coagulant_amount)

        # Add the new spell to the spell book if not already known
        pattern_name = self.transmute_pattern['name']
        if pattern_name not in self.game.spell_book:
            self.game.spell_book[pattern_name] = self.transmute_pattern.copy()

        # Award experience for successful transmutation
        xp_reward = 50 + sum(pattern_comp.values()) * 2
        player.gain_experience(xp_reward)

        self.game.add_message(f"Successfully transmuted {self.transmute_item['name']} into {pattern_name}!")
        self.game.add_message(f"Gained {xp_reward} experience!")

        # Reset transmutation state
        self.transmute_mode = False
        self.reset_state()
