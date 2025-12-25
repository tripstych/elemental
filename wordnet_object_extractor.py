#!/usr/bin/env python3
"""
WordNet Object Extractor
Systematically extracts physical objects from WordNet for game world population.
NO essence composition - that comes from the language system.
"""

import json
from nltk.corpus import wordnet as wn
from collections import defaultdict

# ============================================================================
# MATERIAL INFERENCE (from your existing system)
# ============================================================================

MATERIAL_KEYWORDS = {
    'wood': ['wood', 'timber', 'oak', 'pine', 'birch', 'maple', 'cedar', 'willow', 'ash', 'elm'],
    'stone': ['stone', 'rock', 'granite', 'marble', 'limestone', 'sandstone', 'slate'],
    'metal': ['metal', 'iron', 'steel', 'bronze', 'copper', 'brass'],
    'glass': ['glass', 'crystal'],
    'leather': ['leather', 'hide'],
    'cloth': ['cloth', 'fabric', 'silk', 'wool', 'linen', 'cotton'],
    'bone': ['bone', 'ivory'],
    'paper': ['paper', 'parchment'],
    'ceramic': ['ceramic', 'clay', 'pottery'],
    'wax': ['wax', 'candle'],
    'rope': ['rope', 'cord', 'twine'],
    'gold': ['gold', 'golden'],
    'silver': ['silver'],
}

TYPE_DEFAULT_MATERIALS = {
    'tree': 'wood',
    'plant': 'wood',
    'weapon': 'steel',
    'tool': 'iron',
    'furniture': 'wood',
    'container': 'wood',
    'building': 'stone',
    'food': 'organic',
    'liquid': 'liquid',
    'liquids': 'liquid',
    'mineral': 'stone',
    'fabric': 'cloth',
    'fabrics': 'cloth',
}

def infer_material(name, obj_type, definition):
    """Infer material from name and definition"""
    text = f"{name} {definition}".lower()
    
    # Priority 1: Type-specific overrides (liquids should be liquid, food should be organic)
    if obj_type in ['liquids', 'food']:
        return TYPE_DEFAULT_MATERIALS.get(obj_type, 'organic')
    
    # Priority 2: Check for explicit material keywords
    for material, keywords in MATERIAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return material
    
    # Priority 3: Fall back to type defaults
    return TYPE_DEFAULT_MATERIALS.get(obj_type, 'wood')

def estimate_size(name, obj_type):
    """Estimate object size"""
    name_lower = name.lower()
    
    # Tiny objects
    if any(w in name_lower for w in ['coin', 'bead', 'needle', 'seed', 'pebble', 'gem', 'ring']):
        return 'tiny'
    
    # Small objects
    if any(w in name_lower for w in ['knife', 'dagger', 'cup', 'bottle', 'book', 'candle']):
        return 'small'
    
    # Large objects
    if any(w in name_lower for w in ['tree', 'boulder', 'statue', 'wagon', 'bed', 'table', 'wardrobe']):
        return 'large'
    
    # Huge objects
    if any(w in name_lower for w in ['building', 'house', 'tower', 'bridge', 'ship']):
        return 'huge'
    
    return 'medium'

def estimate_weight(size):
    """Estimate weight based on size"""
    weights = {
        'tiny': 0.1,
        'small': 1.0,
        'medium': 10.0,
        'large': 100.0,
        'huge': 1000.0,
    }
    return weights.get(size, 10.0)

# ============================================================================
# WORDNET CATEGORY EXTRACTION
# ============================================================================

MAJOR_CATEGORIES = {
    'trees': 'tree.n.01',
    'weapons': 'weapon.n.01',
    'tools': 'tool.n.01',
    'furniture': 'furniture.n.01',
    'containers': 'container.n.01',
    'plants': 'plant.n.02',
    'stones': 'rock.n.01',
    'buildings': 'building.n.01',
    'food': 'food.n.01',
    'fabrics': 'fabric.n.01',
    'liquids': 'liquid.n.01',
    'metals': 'metal.n.01',
    'gems': 'gem.n.02',
}

def get_hyponyms(synset, max_depth=3, current_depth=0):
    """Recursively get all hyponyms (subcategories) up to max_depth"""
    if current_depth >= max_depth:
        return []
    
    hyponyms = []
    for hyponym in synset.hyponyms():
        hyponyms.append(hyponym)
        hyponyms.extend(get_hyponyms(hyponym, max_depth, current_depth + 1))
    
    return hyponyms

def extract_category(category_name, synset_name, max_depth=3):
    """Extract all objects from a WordNet category"""
    try:
        synset = wn.synset(synset_name)
    except:
        print(f"⚠️  Could not find synset: {synset_name}")
        return []
    
    # Get all hyponyms
    all_synsets = [synset] + get_hyponyms(synset, max_depth)
    
    objects = []
    seen_names = set()
    
    for syn in all_synsets:
        # Get primary name (lemma)
        name = syn.lemmas()[0].name().replace('_', ' ')
        
        # Skip if already seen
        if name in seen_names:
            continue
        seen_names.add(name)
        
        # Get definition
        definition = syn.definition()
        
        # Infer properties
        material = infer_material(name, category_name, definition)
        size = estimate_size(name, category_name)
        weight = estimate_weight(size)
        
        obj = {
            'name': name,
            'type': category_name,
            'material': material,
            'size': size,
            'weight': weight,
            'definition': definition,
            'source': 'wordnet',
            'synset': syn.name(),
        }
        
        objects.append(obj)
    
    return objects

# ============================================================================
# MAIN EXTRACTION
# ============================================================================

def main():
    print("=" * 70)
    print("WORDNET OBJECT EXTRACTOR")
    print("=" * 70)
    print()
    
    all_objects = []
    stats = defaultdict(int)
    
    for category_name, synset_name in MAJOR_CATEGORIES.items():
        print(f"📦 Extracting {category_name}...")
        objects = extract_category(category_name, synset_name, max_depth=3)
        print(f"   Found {len(objects)} objects")
        
        all_objects.extend(objects)
        stats[category_name] = len(objects)
        stats['total'] += len(objects)
    
    print()
    print("=" * 70)
    print(f"EXTRACTED {stats['total']} TOTAL OBJECTS")
    print("=" * 70)
    print()
    
    # Category breakdown
    print("Category Breakdown:")
    for category, count in sorted(stats.items(), key=lambda x: -x[1]):
        if category != 'total':
            print(f"  {category:20s}: {count:4d}")
    
    print()
    
    # Material breakdown
    materials = defaultdict(int)
    for obj in all_objects:
        materials[obj['material']] += 1
    
    print("Material Breakdown:")
    for material, count in sorted(materials.items(), key=lambda x: -x[1])[:20]:
        print(f"  {material:20s}: {count:4d}")
    
    print()
    
    # Save to JSON
    output_file = 'game_objects_wordnet.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_objects, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved to {output_file}")
    print()
    
    # Show some examples
    print("=" * 70)
    print("SAMPLE OBJECTS:")
    print("=" * 70)
    
    # Show 3 examples from each category
    for category_name in list(MAJOR_CATEGORIES.keys())[:5]:
        category_objects = [o for o in all_objects if o['type'] == category_name][:3]
        if category_objects:
            print(f"\n{category_name.upper()}:")
            for obj in category_objects:
                print(f"  • {obj['name']:30s} ({obj['material']:10s}, {obj['size']:6s})")

if __name__ == '__main__':
    main()
