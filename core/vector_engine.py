"""
Vector Engine - Spoken spell casting system with Light and Dark alphabets.

Players speak spells using elemental syllables from two phonetic alphabets:
- LIGHT alphabet: Additive (+) - adds elemental power
- DARK alphabet: Subtractive (-) - removes elemental power

Each syllable has an element (earth/water/fire/air) and a power value (1-16).
The combined phrase creates an elemental vector that transforms items.

The LOAD/STRAIN system governs safety:
    STRAIN = sum of abs(value) for all words (magnitude of change)
    LOAD = STRAIN * object_weight
    If LOAD > caster's conduit_limit, excess becomes BURN damage.

Key insight: The universe charges you for the MAGNITUDE of the shift,
regardless of direction. Subtracting 16 air costs the same as adding 16 air.
"""



import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any


@dataclass
class SpokenPhrase:
    """Result of parsing a spoken phrase"""
    phrase: str
    words: List[str]
    vectors: Dict[str, float]  # {'fire': 0, 'water': 0, 'earth': 0, 'air': 0}
    total_strain: float  # Sum of abs(values) - the cost
    total_power: float  # Sum of signed values - the net effect
    unknown_words: List[str]

    @property
    def dominant_element(self) -> Optional[str]:
        """Get the element with highest absolute power, or None if tied/empty"""
        if not self.vectors or self.total_strain == 0:
            return None
        # Use absolute values for dominance
        max_val = max(abs(v) for v in self.vectors.values())
        if max_val == 0:
            return None
        dominants = [e for e, v in self.vectors.items() if abs(v) == max_val]
        return dominants[0] if len(dominants) == 1 else None


@dataclass
class CastResult:
    """Result of casting a spoken spell"""
    success: bool
    message: str
    load: float = 0
    strain: float = 0
    overload: float = 0
    burn_damage: int = 0
    vectors: Dict[str, float] = field(default_factory=dict)
    item_before: Optional[Dict] = None
    item_after: Optional[Dict] = None


class VectorEngine:
    """
    Parses spoken phrases into elemental vectors for spell casting.

    Uses two alphabets:
    - Light (elemental_light_alphabet.json): Positive values, adds power
    - Dark (elemental_dark_alphabet.json): Negative values, subtracts power

    Each alphabet has 16 syllables per element (64 per alphabet, 128 total).

    Example:
        "OOM SHII" -> earth: +1, water: +1 (Light, additive)
        "GRAV- MAR-" -> earth: -1, water: -1 (Dark, subtractive)

    Strain is always abs(value), so "GRAV-" costs 1 strain just like "OOM".
    """

    def __init__(self, light_path: str = None, dark_path: str = None):
        """
        Initialize the vector engine with both alphabets.

        Args:
            light_path: Path to elemental_light_alphabet.json
            dark_path: Path to elemental_dark_alphabet.json
        """
        # word -> signed value (positive for light, negative for dark)
        self.lexicon: Dict[str, int] = {}
        # word -> element name
        self.element_map: Dict[str, str] = {}
        # word -> 'light' or 'dark'
        self.alphabet_map: Dict[str, str] = {}

        # Raw syllable data by element and type
        self.light_syllables: Dict[str, List[Dict]] = {}
        self.dark_syllables: Dict[str, List[Dict]] = {}

        # Find and load alphabets
        if light_path is None:
            light_path = self._find_file('elemental_light_alphabet.json')
        if dark_path is None:
            dark_path = self._find_file('elemental_dark_alphabet.json')

        if light_path and os.path.exists(light_path):
            self._load_alphabet(light_path, is_dark=False)
        if dark_path and os.path.exists(dark_path):
            self._load_alphabet(dark_path, is_dark=True)

    def _find_file(self, filename: str) -> Optional[str]:
        """Search for a file in common locations"""
        search_paths = [
            filename,
            f'../{filename}',
            os.path.join(os.path.dirname(__file__), '..', filename),
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path
        return None

    def _load_alphabet(self, path: str, is_dark: bool = False):
        """Load an alphabet from JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        storage = self.dark_syllables if is_dark else self.light_syllables
        alphabet_type = 'dark' if is_dark else 'light'

        for element, syllables in data.items():
            storage[element] = syllables

            for syllable in syllables:
                word = syllable['spelling'].upper()
                # Remove trailing dash for matching if present
                word_clean = word.rstrip('-')

                base_value = syllable['value']
                # Dark alphabet values are negative (subtractive)
                signed_value = -base_value if is_dark else base_value

                self.lexicon[word] = signed_value
                self.lexicon[word_clean] = signed_value  # Also match without dash
                self.element_map[word] = element
                self.element_map[word_clean] = element
                self.alphabet_map[word] = alphabet_type
                self.alphabet_map[word_clean] = alphabet_type

    def parse_phrase(self, phrase: str) -> SpokenPhrase:
        """
        Parse a spoken phrase into elemental vectors.

        Args:
            phrase: Space-separated syllables, e.g. "OOM SHII GRAV-"

        Returns:
            SpokenPhrase with vectors, strain, and power totals
        """
        words = phrase.upper().split()
        vectors = {'fire': 0.0, 'water': 0.0, 'earth': 0.0, 'air': 0.0}
        total_strain = 0.0  # Absolute cost
        total_power = 0.0   # Signed net effect
        unknown = []

        for word in words:
            # Try exact match first, then without trailing dash
            word_clean = word.rstrip('-')

            if word in self.lexicon:
                lookup = word
            elif word_clean in self.lexicon:
                lookup = word_clean
            else:
                unknown.append(word)
                continue

            signed_value = self.lexicon[lookup]
            element = self.element_map[lookup]

            # Vector gets the signed value (can go negative)
            vectors[element] += signed_value

            # Strain is always the absolute magnitude
            total_strain += abs(signed_value)
            total_power += signed_value

        return SpokenPhrase(
            phrase=phrase,
            words=words,
            vectors=vectors,
            total_strain=total_strain,
            total_power=total_power,
            unknown_words=unknown
        )

    def calculate_load(self, phrase: SpokenPhrase, item_weight: float) -> float:
        """
        Calculate the LOAD for a spell cast.

        LOAD = total_strain * object_weight

        Strain is the sum of absolute values, so subtracting costs
        the same as adding. Higher load = more strain on the caster.
        """
        return phrase.total_strain * item_weight

    def cast(
        self,
        phrase: str,
        item: Dict,
        caster_conduit: int,
        caster_hp: int
    ) -> CastResult:
        """
        Cast a spoken spell on an item.

        Args:
            phrase: The spoken syllables
            item: Item dict with at least 'weight' and optionally elemental stats
            caster_conduit: Caster's conduit limit (max safe load)
            caster_hp: Caster's current HP (for burn damage calculation)

        Returns:
            CastResult with transformation outcome
        """
        # Parse the phrase
        parsed = self.parse_phrase(phrase)

        # Check for unknown words (fizzle)
        if parsed.unknown_words:
            return CastResult(
                success=False,
                message=f"Spell fizzled! Unknown syllables: {', '.join(parsed.unknown_words)}",
                vectors=parsed.vectors,
                strain=parsed.total_strain
            )

        # Check for empty phrase
        if parsed.total_strain == 0:
            return CastResult(
                success=False,
                message="No elemental words spoken!",
                vectors=parsed.vectors,
                strain=0
            )

        # Get item weight
        item_weight = item.get('weight', 1.0)

        # Calculate load from strain (absolute values)
        load = self.calculate_load(parsed, item_weight)

        # Check for overload
        overload = max(0, load - caster_conduit)
        burn_damage = int(overload) if overload > 0 else 0

        # Store original item state
        item_before = {k: v for k, v in item.items()}

        # Apply transformation - add vector values to item stats
        # Values can be negative (dark alphabet subtracts)
        item_after = {k: v for k, v in item.items()}

        for element in ['fire', 'water', 'earth', 'air']:
            current = item_after.get(element, 0)
            delta = parsed.vectors.get(element, 0)
            new_value = current + delta
            # Prevent stats from going below 0
            item_after[element] = max(0, new_value)

        # Build result message
        if burn_damage > 0:
            message = f"OVERLOAD! Channeled {phrase.upper()} but took {burn_damage} burn damage!"
        else:
            message = f"Cast {phrase.upper()}! Strain: {int(parsed.total_strain)} Load: {int(load)}/{caster_conduit}"

        # Add transformation info
        changes = []
        for elem in ['fire', 'water', 'earth', 'air']:
            delta = parsed.vectors.get(elem, 0)
            if delta > 0:
                changes.append(f"{elem[:1].upper()}+{int(delta)}")
            elif delta < 0:
                changes.append(f"{elem[:1].upper()}{int(delta)}")

        if changes:
            message += f" [{', '.join(changes)}]"

        return CastResult(
            success=True,
            message=message,
            load=load,
            strain=parsed.total_strain,
            overload=overload,
            burn_damage=burn_damage,
            vectors=parsed.vectors,
            item_before=item_before,
            item_after=item_after
        )

    def get_syllables_for_element(self, element: str, alphabet: str = None) -> List[Dict]:
        """
        Get syllables for an element.

        Args:
            element: 'fire', 'water', 'earth', or 'air'
            alphabet: 'light', 'dark', or None for both

        Returns:
            List of syllable dicts with spelling, value, description/quality
        """
        result = []

        if alphabet in (None, 'light') and element in self.light_syllables:
            for syl in self.light_syllables[element]:
                syl_copy = syl.copy()
                syl_copy['alphabet'] = 'light'
                syl_copy['signed_value'] = syl['value']  # Positive
                # Normalize key names
                if 'quality' not in syl_copy and 'description' in syl_copy:
                    syl_copy['quality'] = syl_copy['description']
                result.append(syl_copy)

        if alphabet in (None, 'dark') and element in self.dark_syllables:
            for syl in self.dark_syllables[element]:
                syl_copy = syl.copy()
                syl_copy['alphabet'] = 'dark'
                syl_copy['signed_value'] = -syl['value']  # Negative
                # Normalize key names
                if 'quality' not in syl_copy and 'description' in syl_copy:
                    syl_copy['quality'] = syl_copy['description']
                result.append(syl_copy)

        return result

    def get_light_syllables(self, element: str) -> List[Dict]:
        """Get only light (additive) syllables for an element"""
        return self.get_syllables_for_element(element, 'light')

    def get_dark_syllables(self, element: str) -> List[Dict]:
        """Get only dark (subtractive) syllables for an element"""
        return self.get_syllables_for_element(element, 'dark')

    def get_all_elements(self) -> List[str]:
        """Get list of all elements"""
        elements = set(self.light_syllables.keys()) | set(self.dark_syllables.keys())
        return list(elements)

    def suggest_phrase(
        self,
        target_vectors: Dict[str, float],
        max_strain: float = None,
        prefer_dark: bool = False
    ) -> str:
        """
        Suggest a phrase to achieve target vectors within strain limit.

        Args:
            target_vectors: Desired element changes, e.g. {'fire': 10, 'earth': -5}
            max_strain: Optional maximum total strain to stay under
            prefer_dark: If True, prefer dark syllables for negative targets

        Returns:
            Suggested phrase string
        """
        phrase_parts = []
        total_strain = 0

        for element, target in sorted(target_vectors.items(), key=lambda x: -abs(x[1])):
            if target == 0:
                continue

            # Choose alphabet based on direction
            use_dark = target < 0
            syllables = self.get_syllables_for_element(element, 'dark' if use_dark else 'light')

            if not syllables:
                continue

            # Sort by value descending (absolute) for greedy approach
            sorted_syllables = sorted(syllables, key=lambda s: -s['value'])

            remaining = abs(target)
            for syl in sorted_syllables:
                if remaining <= 0:
                    break

                strain_cost = syl['value']  # Always positive for strain

                if max_strain and total_strain + strain_cost > max_strain:
                    continue

                while remaining > 0 and (max_strain is None or total_strain + strain_cost <= max_strain):
                    phrase_parts.append(syl['spelling'])
                    remaining -= syl['value']
                    total_strain += strain_cost
                    if remaining <= 0:
                        break

        return ' '.join(phrase_parts)

