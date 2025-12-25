"""
Advanced Spell Transformation Examples
Demonstrates spell discovery, crafting, and counter-magic
"""

from spell_system import SpellDictionary, SpellExecutor, Creature, TerrainObject
import json


def example_1_spell_discovery():
    """Example: Player discovers new spells through experimentation"""
    print("=" * 80)
    print("EXAMPLE 1: SPELL DISCOVERY")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    print("Player knows 'kata' (ignite): fire=45, water=5, earth=10, air=8")
    print()
    
    # Player experiments
    experiments = [
        ("Add 13 fire", {"fire": 13}),
        ("Add 20 earth", {"earth": 20}),
        ("Swap fire↔air", "swap_fe"),
    ]
    
    for description, transform in experiments:
        print(f"🔮 {description}")
        
        if isinstance(transform, dict):
            new_word = dictionary.transform_spell("kata", **transform)
        else:
            new_word = dictionary.permute_spell("kata", transform)
        
        if new_word and new_word != "undefined":
            spell_data = dictionary.get_spell(new_word)
            if spell_data:
                print(f"   ✨ Discovered: '{new_word}' - {spell_data['definition']}")
                print(f"   Composition: {spell_data['composition']}")
            else:
                print(f"   ❓ New word: '{new_word}' (not in dictionary)")
        else:
            print(f"   ❌ No spell at this vector")
        print()


def example_2_spell_crafting():
    """Example: Multi-step transformation to create specific spell"""
    print("=" * 80)
    print("EXAMPLE 2: SPELL CRAFTING - CREATING METEOR")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    print("Goal: Create 'meteor' (fire=60, earth=50)")
    print()
    
    # Start with fireball
    current = "krata"
    print(f"Step 1: Start with '{current}' (fireball)")
    spell = dictionary.get_spell(current)
    print(f"        Composition: {spell['composition']}")
    print()
    
    # Add earth to make it heavier
    print("Step 2: Add 40 earth (make it solid)")
    current = dictionary.transform_spell(current, earth=40)
    if current and current != "undefined":
        spell = dictionary.get_spell(current)
        if spell:
            print(f"        Result: '{current}'")
            print(f"        Composition: {spell['composition']}")
        else:
            print(f"        Vector exists but no spell assigned yet")
    print()
    
    # Check if we got meteor
    meteor_spell = dictionary.get_spell("kratgod")
    print(f"Target spell 'kratgod' (meteor): {meteor_spell['composition']}")
    print()
    
    if current == "kratgod":
        print("✅ Successfully crafted meteor!")
    else:
        print("❌ Didn't get meteor - would need different path")


def example_3_counter_magic():
    """Example: Transforming enemy spells mid-flight"""
    print("=" * 80)
    print("EXAMPLE 3: COUNTER-MAGIC")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    player = Creature("Hero", hp=100)
    enemy = Creature("Dark Mage", hp=100)
    
    print("🧙 Dark Mage casts 'brudo' (earth shield)")
    shield_spell = dictionary.get_spell("brudo")
    print(f"   Shield: {shield_spell['composition']}")
    print(f"   Will block: {shield_spell['spell_effect']['properties']['hp']} damage")
    print()
    
    # Counter by adding fire
    print("⚡ Hero counters by adding 43 fire to the spell mid-flight!")
    transformed = dictionary.transform_spell("brudo", fire=43)
    
    if transformed and transformed != "undefined":
        counter_spell = dictionary.get_spell(transformed)
        if counter_spell:
            print(f"   Shield transforms into '{transformed}'!")
            print(f"   New composition: {counter_spell['composition']}")
            print(f"   Effect: {counter_spell['definition']}")
            print()
            
            # Execute the transformed spell on the enemy
            executor = SpellExecutor(counter_spell)
            messages = executor.cast(player, [enemy], {})
            for msg in messages:
                print(f"   {msg}")
        else:
            print(f"   Transformed to unknown spell: {transformed}")
    else:
        print("   Transformation failed!")
    print()


def example_4_anagram_opposites():
    """Example: Finding opposite spells through permutation"""
    print("=" * 80)
    print("EXAMPLE 4: ANAGRAM OPPOSITES")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    # Try different permutations to find relationships
    test_spells = ["heysa", "krata", "lumno", "brudo"]
    
    for spell_word in test_spells:
        base_spell = dictionary.get_spell(spell_word)
        if not base_spell:
            continue
        
        print(f"📖 {spell_word} ({base_spell['definition']})")
        print(f"   Composition: {base_spell['composition']}")
        
        # Try all permutations
        permutations = ["swap_fw", "swap_ea", "reverse", "rotate_left"]
        
        found_any = False
        for perm in permutations:
            result = dictionary.permute_spell(spell_word, perm)
            if result and result != "undefined" and result != spell_word:
                result_spell = dictionary.get_spell(result)
                if result_spell:
                    print(f"   {perm:15s} → {result:10s} ({result_spell['definition']})")
                    found_any = True
        
        if not found_any:
            print("   (No valid permutations found)")
        print()


def example_5_elemental_progressions():
    """Example: Show elemental power progressions"""
    print("=" * 80)
    print("EXAMPLE 5: ELEMENTAL POWER PROGRESSIONS")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    # Group spells by primary element
    spells_by_element = {
        'fire': [],
        'water': [],
        'earth': [],
        'air': []
    }
    
    for spell_id, spell_data in dictionary.spell_data.items():
        spirit = spell_data.get('spirit', 'unknown')
        if spirit in spells_by_element:
            spells_by_element[spirit].append(spell_data)
    
    # Show progressions
    for element in ['fire', 'water', 'earth', 'air']:
        print(f"🔥💧🌍💨 {element.upper()} SPELLS:")
        spells = sorted(
            spells_by_element[element], 
            key=lambda s: s['composition'][element],
            reverse=True
        )
        
        for spell in spells[:5]:  # Top 5
            comp = spell['composition']
            power = comp[element]
            print(f"   {spell['word']:10s} ({power:2d} {element}) - {spell['definition']}")
        print()


def example_6_combo_transformations():
    """Example: Multiple transformations in sequence"""
    print("=" * 80)
    print("EXAMPLE 6: TRANSFORMATION CHAINS")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    print("Starting with 'lumno' (heal)")
    current = "lumno"
    spell = dictionary.get_spell(current)
    print(f"Base: {spell['composition']}")
    print()
    
    # Chain transformations
    steps = [
        ("Add 10 fire", {"fire": 10}),
        ("Add 10 more fire", {"fire": 10}),
        ("Add 10 more fire", {"fire": 10}),
        ("Add 10 more fire", {"fire": 10}),
    ]
    
    print("Transformation chain:")
    for i, (description, transform) in enumerate(steps, 1):
        current = dictionary.transform_spell(current, **transform)
        if current and current != "undefined":
            spell = dictionary.get_spell(current)
            if spell:
                print(f"  Step {i}: {description}")
                print(f"          → '{current}' ({spell['definition']})")
                print(f"          Composition: {spell['composition']}")
            else:
                print(f"  Step {i}: {description}")
                print(f"          → '{current}' (undefined spell)")
                break
        else:
            print(f"  Step {i}: {description}")
            print(f"          → Transformation invalid")
            break
    print()


def example_7_spell_components():
    """Example: Treating spells as components to combine"""
    print("=" * 80)
    print("EXAMPLE 7: SPELL COMPONENTS (Additive Magic)")
    print("=" * 80)
    print()
    
    dictionary = SpellDictionary('elemental_spells.json')
    
    print("Combining spell vectors to create new effects:")
    print()
    
    # Get some base spells
    fire = dictionary.get_spell("kata")  # ignite
    earth = dictionary.get_spell("brudo")  # shield
    
    print(f"Component 1: '{fire['word']}' (ignite)")
    print(f"             {fire['composition']}")
    print()
    print(f"Component 2: '{earth['word']}' (shield)")
    print(f"             {earth['composition']}")
    print()
    
    # Add them together
    combined_vector = tuple(
        fire['composition'][k] + earth['composition'][k]
        for k in ['fire', 'water', 'earth', 'air']
    )
    
    # Clamp to valid range
    combined_vector = tuple(min(63, max(0, v)) for v in combined_vector)
    
    print(f"Combined vector: {combined_vector}")
    
    # Look up what spell this is
    result_word = dictionary.elemental_dictionary.get(combined_vector)
    if result_word:
        result = dictionary.get_spell(result_word)
        print(f"Result: '{result_word}' ({result['definition']})")
        print(f"Effect: {result['spell_effect']['description']}")
    else:
        print("No spell exists at this vector (could be crafted!)")
    print()


if __name__ == "__main__":
    example_1_spell_discovery()
    print("\n" + "="*80 + "\n")
    
    example_2_spell_crafting()
    print("\n" + "="*80 + "\n")
    
    example_3_counter_magic()
    print("\n" + "="*80 + "\n")
    
    example_4_anagram_opposites()
    print("\n" + "="*80 + "\n")
    
    example_5_elemental_progressions()
    print("\n" + "="*80 + "\n")
    
    example_6_combo_transformations()
    print("\n" + "="*80 + "\n")
    
    example_7_spell_components()
