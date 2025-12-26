"""
Alchemy System - Pure game logic for transmutation, dissolution, and meditation.

No pygame or UI dependencies. Can be tested standalone.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


# =============================================================================
# ALCHEMY DATA
# =============================================================================

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

COAGULANTS = {
    "ite_ignis": {
        "name": "Ite Ignis",
        "affinity": ["fire"],
        "strength": 0.9,
        "description": "Fire powder",
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
        "description": "Earth powder",
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

MATERIAL_ESSENCES = {
    'weapon': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'armor': {'fire': 10, 'water': 10, 'earth': 50, 'air': 5},
    'tool': {'fire': 20, 'water': 10, 'earth': 35, 'air': 10},
    'gem': {'fire': 30, 'water': 20, 'earth': 30, 'air': 20},
    'potion': {'fire': 10, 'water': 40, 'earth': 20, 'air': 5},
    'scroll': {'fire': 15, 'water': 10, 'earth': 20, 'air': 30},
    'food': {'fire': 10, 'water': 40, 'earth': 20, 'air': 5},
    'default': {'fire': 15, 'water': 15, 'earth': 15, 'air': 15},
}

ELEMENTS = ['fire', 'water', 'earth', 'air']


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Essence:
    """Represents elemental essence quantities"""
    fire: float = 0.0
    water: float = 0.0
    earth: float = 0.0
    air: float = 0.0

    def __getitem__(self, key: str) -> float:
        return getattr(self, key, 0.0)

    def __setitem__(self, key: str, value: float):
        setattr(self, key, value)

    def to_dict(self) -> Dict[str, float]:
        return {'fire': self.fire, 'water': self.water, 'earth': self.earth, 'air': self.air}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> 'Essence':
        return cls(
            fire=d.get('fire', 0.0),
            water=d.get('water', 0.0),
            earth=d.get('earth', 0.0),
            air=d.get('air', 0.0)
        )

    def total(self) -> float:
        return self.fire + self.water + self.earth + self.air

    def add(self, other: 'Essence'):
        self.fire += other.fire
        self.water += other.water
        self.earth += other.earth
        self.air += other.air


@dataclass
class SpellBookEntry:
    """An entry in the spell book - learned essence pattern"""
    name: str
    synset: str
    composition: Dict[str, float]
    definition: str = ""
    item_type: str = "misc"
    power: float = 1.0
    castable: bool = False
    spell_effect: Optional[str] = None


@dataclass
class AlchemyResult:
    """Result of an alchemy operation"""
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# ALCHEMY SYSTEM
# =============================================================================

class AlchemySystem:
    """
    Core alchemy logic - handles transmutation, dissolution, and meditation.

    This class is pure logic with no UI dependencies. It operates on game
    objects passed to it and returns results that the UI can display.
    """

    def __init__(self):
        self.spell_book: Dict[str, SpellBookEntry] = {}
        self.stored_essence = Essence()

    def get_material_essence(self, item_type: str) -> Dict[str, float]:
        """Get base essence composition for an item type"""
        return MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default']).copy()

    def get_solvent_data(self, solvent_type: str) -> Dict:
        """Get solvent properties by type key"""
        return SOLVENTS.get(solvent_type, SOLVENTS['alkahest'])

    def get_coagulant_data(self, coagulant_type: str) -> Dict:
        """Get coagulant properties by type key"""
        return COAGULANTS.get(coagulant_type, COAGULANTS['prima_ite'])

    # -------------------------------------------------------------------------
    # MEDITATION - Learn item essences
    # -------------------------------------------------------------------------

    def meditate(self, item: Dict) -> AlchemyResult:
        """
        Meditate on an item to learn its essence pattern.

        Args:
            item: Item dict with 'name', 'synset', 'type', 'definition' keys

        Returns:
            AlchemyResult with success status and entry if successful
        """
        synset = item.get('synset')
        if not synset:
            return AlchemyResult(
                success=False,
                message=f"Cannot meditate on {item.get('name', 'item')} - no essence pattern!"
            )

        # Already known?
        if synset in self.spell_book:
            return AlchemyResult(
                success=False,
                message=f"'{item.get('name')}' is already in your Spell Book!"
            )

        # Calculate essence
        item_type = item.get('type', 'default')
        composition = self.get_material_essence(item_type)

        # Create entry
        entry = SpellBookEntry(
            name=item.get('name', 'Unknown'),
            synset=synset,
            composition=composition,
            definition=item.get('definition', 'Unknown'),
            item_type=item_type
        )

        self.spell_book[synset] = entry

        essence_str = ", ".join(f"{e[0].upper()}:{v}" for e, v in composition.items())

        return AlchemyResult(
            success=True,
            message=f"Recorded '{entry.name}' to Spell Book! Essence: {essence_str}",
            details={'entry': entry, 'composition': composition}
        )

    # -------------------------------------------------------------------------
    # DISSOLUTION - Extract essence from items
    # -------------------------------------------------------------------------

    def dissolve(
        self,
        item: Dict,
        solvent: Dict,
        solvent_amount: int = 10
    ) -> AlchemyResult:
        """
        Dissolve an item to extract its essence.

        Args:
            item: Item to dissolve (dict with 'name', 'type')
            solvent: Solvent to use (dict with 'solvent_type', 'quantity')
            solvent_amount: Amount of solvent to use in ml

        Returns:
            AlchemyResult with extracted essence amounts
        """
        # Check solvent quantity
        current_qty = solvent.get('quantity', 0)
        if current_qty < solvent_amount:
            return AlchemyResult(
                success=False,
                message=f"Not enough solvent! Need {solvent_amount}ml, have {current_qty}ml"
            )

        # Get solvent properties
        solvent_key = solvent.get('solvent_type', 'alkahest')
        solvent_data = self.get_solvent_data(solvent_key)

        # Get item essence
        item_type = item.get('type', 'default')
        base_essence = self.get_material_essence(item_type)

        # Calculate extraction based on solvent affinity and amount
        extraction_multiplier = solvent_amount / 10.0
        extracted = {}

        for elem in solvent_data['extracts']:
            amount = base_essence.get(elem, 10) * solvent_data['strength'] * extraction_multiplier
            extracted[elem] = amount
            # Add to stored essence
            self.stored_essence[elem] += amount

        # Calculate solvent consumption
        solvent_consumed = solvent_amount
        remaining = current_qty - solvent_consumed

        extracted_str = ", ".join(f"{elem[:1].upper()}:{int(amt)}" for elem, amt in extracted.items())

        return AlchemyResult(
            success=True,
            message=f"Extracted essence from {item.get('name')}! Got: {extracted_str}",
            details={
                'extracted': extracted,
                'solvent_consumed': solvent_consumed,
                'solvent_remaining': remaining,
                'solvent_empty': remaining <= 0
            }
        )

    # -------------------------------------------------------------------------
    # TRANSMUTATION - Create new items/spells from essence
    # -------------------------------------------------------------------------

    def transmute(
        self,
        item: Dict,
        solvent: Dict,
        solvent_amount: int,
        coagulant: Dict,
        coagulant_amount: int,
        pattern: SpellBookEntry,
        spell_defs: Optional[Dict] = None
    ) -> AlchemyResult:
        """
        Transmute an item using a pattern from the spell book.

        Args:
            item: Source item to extract essence from
            solvent: Solvent to use for extraction
            solvent_amount: Amount of solvent (ml)
            coagulant: Coagulant to use for binding
            coagulant_amount: Amount of coagulant (ml)
            pattern: Target pattern from spell book
            spell_defs: Optional spell definitions to check for castable spells

        Returns:
            AlchemyResult with transmutation outcome
        """
        # Get reagent properties
        solvent_key = solvent.get('solvent_type', 'alkahest')
        solvent_data = self.get_solvent_data(solvent_key)
        coag_key = coagulant.get('coagulant_type', 'prima_ite')
        coag_data = self.get_coagulant_data(coag_key)

        # Calculate essence extraction
        item_type = item.get('type', 'default')
        base_essence = self.get_material_essence(item_type)

        extracted_essence = {}
        solvent_strength = solvent_data.get('strength', 1.0)
        solvent_extracts = solvent_data.get('extracts', [])
        extraction_multiplier = solvent_amount / 10.0

        for elem in solvent_extracts:
            base_amount = base_essence.get(elem, 10)
            extracted = base_amount * solvent_strength * extraction_multiplier
            extracted_essence[elem] = extracted

        # Get pattern requirements
        pattern_comp = pattern.composition

        # Calculate binding with coagulant
        coag_affinity = coag_data.get('affinity', [])
        coag_strength = coag_data.get('strength', 1.0)
        binding_efficiency = min(1.0, 0.5 + (coagulant_amount / 200.0))

        bound_essence = {}
        for elem, required in pattern_comp.items():
            available = extracted_essence.get(elem, 0)
            # Affinity bonus/penalty
            if elem in coag_affinity:
                effective_available = available * (1.0 + coag_strength * 0.5)
            else:
                effective_available = available * 0.7
            bound = min(required, effective_available * binding_efficiency)
            bound_essence[elem] = bound

        # Calculate completion
        total_required = sum(pattern_comp.values())
        total_bound = sum(bound_essence.values())
        completion = total_bound / total_required if total_required > 0 else 0

        # Check for known spell
        spell_name = None
        spell_data = None
        if spell_defs:
            for name, spell_def in spell_defs.items():
                if spell_def.get('synset') == pattern.synset:
                    spell_name = name
                    spell_data = spell_def
                    break

        # Resource consumption
        solvent_remaining = solvent.get('quantity', 0) - solvent_amount
        coagulant_remaining = coagulant.get('quantity', 0) - coagulant_amount

        details = {
            'extracted_essence': extracted_essence,
            'bound_essence': bound_essence,
            'completion': completion,
            'solvent_consumed': solvent_amount,
            'solvent_remaining': solvent_remaining,
            'solvent_empty': solvent_remaining <= 0,
            'coagulant_consumed': coagulant_amount,
            'coagulant_remaining': coagulant_remaining,
            'coagulant_empty': coagulant_remaining <= 0,
        }

        # Need at least 70% completion
        if completion >= 0.7:
            if spell_name and spell_data:
                # Create castable spell
                new_entry = SpellBookEntry(
                    name=spell_name.capitalize(),
                    synset=pattern.synset,
                    composition=pattern.composition,
                    definition=spell_data.get('definition', 'A magical spell'),
                    item_type='spell',
                    power=completion,
                    castable=True,
                    spell_effect=spell_data.get('spell_effect')
                )
                self.spell_book[pattern.synset] = new_entry
                details['new_entry'] = new_entry
                details['is_spell'] = True

                return AlchemyResult(
                    success=True,
                    message=f"TRANSMUTE SUCCESS! Learned {spell_name.upper()}! Power: {int(completion*100)}%",
                    details=details
                )
            else:
                # Create transmuted item
                new_entry = SpellBookEntry(
                    name=f"Transmuted {pattern.name}",
                    synset=pattern.synset,
                    composition=pattern.composition,
                    definition=pattern.definition,
                    item_type=pattern.item_type,
                    power=completion
                )
                self.spell_book[pattern.synset] = new_entry
                details['new_entry'] = new_entry
                details['is_spell'] = False

                return AlchemyResult(
                    success=True,
                    message=f"TRANSMUTE SUCCESS! Created {new_entry.name}! Power: {int(completion*100)}%",
                    details=details
                )
        else:
            return AlchemyResult(
                success=False,
                message=f"TRANSMUTE FAILED! Only {int(completion*100)}% power (need 70%). Try more reagents or matching affinities.",
                details=details
            )

    # -------------------------------------------------------------------------
    # SPELL BOOK QUERIES
    # -------------------------------------------------------------------------

    def get_known_essences(self) -> List[SpellBookEntry]:
        """Get all known essence patterns"""
        return list(self.spell_book.values())

    def get_castable_spells(self) -> List[SpellBookEntry]:
        """Get all castable spells"""
        return [e for e in self.spell_book.values() if e.castable]

    def knows_essence(self, synset: str) -> bool:
        """Check if an essence pattern is known"""
        return synset in self.spell_book

    def get_essence_for_item(self, item: Dict) -> Optional[Dict[str, float]]:
        """Get known essence composition for an item, if we've meditated on it"""
        synset = item.get('synset', '')
        if synset in self.spell_book:
            return self.spell_book[synset].composition
        return None
