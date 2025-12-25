import json
import requests
import time
import re
from pathlib import Path

# ============================================================================
# MATERIAL DETECTION
# ============================================================================

NAME_MATERIAL_OVERRIDES = {
    'candle': 'wax', 'torch': 'wood', 'lantern': 'iron', 'lamp': 'iron',
    'flask': 'glass', 'vial': 'glass', 'bottle': 'glass', 'potion': 'glass',
    'ink': 'glass', 'oil': 'glass', 'holy water': 'glass', 'acid': 'glass',
    'alchemist': 'glass', 'antitoxin': 'glass', 'perfume': 'glass',
    'rope': 'rope', 'chain': 'chain', 'manacles': 'iron', 'lock': 'iron',
    'bell': 'bronze', 'mirror': 'glass', 'spyglass': 'glass', 'hourglass': 'glass',
    'tent': 'cloth', 'bedroll': 'cloth', 'blanket': 'cloth', 'clothes': 'cloth',
    'robe': 'cloth', 'vestments': 'cloth', 'cloak': 'cloth', 'cape': 'cloth',
    'bag': 'leather', 'sack': 'cloth', 'backpack': 'leather', 'pouch': 'leather',
    'quiver': 'leather', 'case': 'leather', 'book': 'paper', 'tome': 'paper',
    'spellbook': 'paper', 'scroll': 'parchment', 'map': 'parchment',
    'paper': 'paper', 'parchment': 'parchment', 'arrow': 'wood', 'bolt': 'wood',
    'dart': 'wood', 'javelin': 'wood', 'net': 'rope', 'ladder': 'wood',
    'pole': 'wood', 'staff': 'wood', 'wand': 'wood', 'rod': 'wood',
    'flute': 'wood', 'horn': 'bone', 'drum': 'leather', 'lute': 'wood',
    'lyre': 'wood', 'pan flute': 'wood', 'shawm': 'wood', 'viol': 'wood',
    'boots': 'leather', 'gloves': 'leather', 'gauntlet': 'steel', 'helm': 'steel',
    'shield': 'wood', 'buckler': 'steel',
}

MATERIAL_PATTERNS = [
    (r'\badamantine\b', 'adamantine'), (r'\bmithril\b', 'mithril'),
    (r'\bplatinum\b', 'platinum'), (r'\bdragon(?:hide|scale|bone)?\b', 'dragon'),
    (r'\bcelestial\b', 'celestial'), (r'\binfernal\b', 'infernal'),
    (r'\bethereal\b', 'ethereal'), (r'\bsteel\b', 'steel'), (r'\biron\b', 'iron'),
    (r'\bsilver\b', 'silver'), (r'\bbronze\b', 'bronze'), (r'\bcopper\b', 'copper'),
    (r'\boak\b', 'oak'), (r'\byew\b', 'yew'), (r'\bebony\b', 'ebony'),
    (r'\bwood(?:en)?\b', 'wood'), (r'\bleather\b', 'leather'), (r'\bhide\b', 'hide'),
    (r'\bbone\b', 'bone'), (r'\bscale\b', 'scale'), (r'\bsilk\b', 'silk'),
    (r'\bwool\b', 'wool'), (r'\bfur\b', 'fur'), (r'\bcloth\b', 'cloth'),
    (r'\bgranite\b', 'granite'), (r'\bmarble\b', 'marble'), (r'\bcrystal\b', 'crystal'),
    (r'\bglass\b', 'glass'), (r'\bdiamond\b', 'diamond'), (r'\bruby\b', 'ruby'),
    (r'\bsapphire\b', 'sapphire'), (r'\bemerald\b', 'emerald'), (r'\bstone\b', 'stone'),
    (r'\bgold(?:en)?\b', 'gold'), (r'\bpaper\b', 'paper'), (r'\bparchment\b', 'parchment'),
    (r'\brope\b', 'rope'), (r'\bchain\b', 'chain'), (r'\bwax\b', 'wax'), (r'\bclay\b', 'clay'),
]

MATERIAL_ESSENCES = {
    'iron': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'steel': {'fire': 30, 'water': 5, 'earth': 38, 'air': 5},
    'gold': {'fire': 35, 'water': 8, 'earth': 35, 'air': 8},
    'silver': {'fire': 20, 'water': 12, 'earth': 30, 'air': 10},
    'bronze': {'fire': 28, 'water': 6, 'earth': 38, 'air': 6},
    'copper': {'fire': 22, 'water': 8, 'earth': 35, 'air': 8},
    'mithril': {'fire': 30, 'water': 15, 'earth': 25, 'air': 40},
    'adamantine': {'fire': 40, 'water': 5, 'earth': 50, 'air': 5},
    'platinum': {'fire': 38, 'water': 10, 'earth': 32, 'air': 10},
    'wood': {'fire': 30, 'water': 10, 'earth': 15, 'air': 5},
    'oak': {'fire': 28, 'water': 12, 'earth': 18, 'air': 5},
    'yew': {'fire': 25, 'water': 15, 'earth': 15, 'air': 10},
    'ebony': {'fire': 35, 'water': 8, 'earth': 20, 'air': 5},
    'leather': {'fire': 18, 'water': 20, 'earth': 15, 'air': 8},
    'hide': {'fire': 20, 'water': 18, 'earth': 18, 'air': 6},
    'bone': {'fire': 8, 'water': 12, 'earth': 35, 'air': 8},
    'scale': {'fire': 15, 'water': 15, 'earth': 30, 'air': 8},
    'cloth': {'fire': 20, 'water': 15, 'earth': 8, 'air': 15},
    'silk': {'fire': 15, 'water': 20, 'earth': 5, 'air': 20},
    'wool': {'fire': 22, 'water': 18, 'earth': 10, 'air': 12},
    'fur': {'fire': 20, 'water': 16, 'earth': 12, 'air': 14},
    'stone': {'fire': 5, 'water': 5, 'earth': 50, 'air': 3},
    'granite': {'fire': 8, 'water': 5, 'earth': 55, 'air': 3},
    'marble': {'fire': 6, 'water': 8, 'earth': 48, 'air': 5},
    'crystal': {'fire': 15, 'water': 20, 'earth': 30, 'air': 25},
    'glass': {'fire': 20, 'water': 12, 'earth': 25, 'air': 20},
    'diamond': {'fire': 30, 'water': 20, 'earth': 30, 'air': 20},
    'ruby': {'fire': 45, 'water': 10, 'earth': 25, 'air': 15},
    'sapphire': {'fire': 10, 'water': 45, 'earth': 25, 'air': 15},
    'emerald': {'fire': 15, 'water': 30, 'earth': 35, 'air': 15},
    'dragon': {'fire': 50, 'water': 10, 'earth': 25, 'air': 30},
    'celestial': {'fire': 30, 'water': 25, 'earth': 15, 'air': 45},
    'infernal': {'fire': 55, 'water': 5, 'earth': 20, 'air': 25},
    'ethereal': {'fire': 15, 'water': 25, 'earth': 5, 'air': 55},
    'paper': {'fire': 35, 'water': 12, 'earth': 5, 'air': 20},
    'parchment': {'fire': 30, 'water': 15, 'earth': 8, 'air': 18},
    'rope': {'fire': 25, 'water': 18, 'earth': 10, 'air': 12},
    'chain': {'fire': 28, 'water': 6, 'earth': 40, 'air': 5},
    'wax': {'fire': 40, 'water': 5, 'earth': 10, 'air': 5},
    'clay': {'fire': 15, 'water': 25, 'earth': 45, 'air': 3},
}

TYPE_DEFAULTS = {
    'weapon': 'steel', 'armor': 'steel', 'shield': 'wood',
    'wondrous item': 'cloth', 'ring': 'gold', 'amulet': 'silver',
    'adventuring gear': 'wood', 'tools': 'iron', 'potion': 'glass',
    'scroll': 'parchment', 'staff': 'wood', 'wand': 'wood', 'rod': 'wood',
}

RARITY_MULTIPLIERS = {
    'common': 1.0, 'uncommon': 1.2, 'rare': 1.5,
    'very rare': 1.8, 'legendary': 2.2, 'artifact': 3.0,
}

def infer_material(name, desc, item_type):
    name_lower = name.lower()
    for key, material in NAME_MATERIAL_OVERRIDES.items():
        if key in name_lower:
            return material
    
    text = f"{name} {desc}".lower()
    for pattern, material in MATERIAL_PATTERNS:
        if re.search(pattern, text):
            return material
    
    item_type_lower = item_type.lower()
    for type_key, default_mat in TYPE_DEFAULTS.items():
        if type_key in item_type_lower:
            return default_mat
    return 'wood'

def estimate_size(name):
    name_lower = name.lower()
    if any(w in name_lower for w in ['ring', 'coin', 'gem', 'bead', 'needle', 'key', 'pin']):
        return 'tiny'
    if any(w in name_lower for w in ['dagger', 'potion', 'scroll', 'wand', 'amulet', 'vial', 'candle']):
        return 'small'
    if any(w in name_lower for w in ['greatsword', 'greataxe', 'pike', 'halberd', 'statue', 'chest']):
        return 'large'
    return 'medium'

def calculate_essence(material, rarity, is_magic):
    base = MATERIAL_ESSENCES.get(material, {'fire': 10, 'water': 10, 'earth': 10, 'air': 10})
    mult = RARITY_MULTIPLIERS.get(rarity, 1.0)
    if is_magic:
        mult *= 1.3
    return {k: min(63, int(v * mult)) for k, v in base.items()}

def convert_item(item):
    name = item.get('name', 'Unknown')
    desc = item.get('desc', '')
    
    # Handle category
    cat = item.get('category', {})
    item_type = cat.get('name', 'item') if isinstance(cat, dict) else str(cat or 'item')
    
    # Handle rarity
    rar = item.get('rarity', {})
    rarity = (rar.get('name', 'common') if isinstance(rar, dict) else str(rar or 'common')).lower()
    
    is_magic = item.get('is_magic_item', False) or item.get('requires_attunement', False)
    material = infer_material(name, desc, item_type)
    
    return {
        'name': name,
        'description': desc[:300] + '...' if len(desc) > 300 else desc,
        'type': item_type,
        'rarity': rarity,
        'material': material,
        'essence': calculate_essence(material, rarity, is_magic),
        'size': estimate_size(name),
        'weight': float(item.get('weight', 0) or 0),
        'magical': is_magic,
        'source': 'open5e',
    }

def fetch_paginated(base_url, name):
    """Fetch all pages from a paginated endpoint"""
    all_items = []
    url = f"{base_url}?format=json&limit=100"
    page = 1
    
    while url:
        print(f"  {name} page {page}...")
        response = requests.get(url, timeout=30)
        data = response.json()
        all_items.extend(data.get('results', []))
        url = data.get('next')
        page += 1
        time.sleep(0.2)
    
    return all_items

def main():
    print("Fetching from Open5e API...")
    
    # Fetch items
    print("\nFetching items...")
    items = fetch_paginated("https://api.open5e.com/v2/items/", "items")
    print(f"  Got {len(items)} items")
    
    # Fetch weapons for additional data
    print("\nFetching weapons...")
    weapons = fetch_paginated("https://api.open5e.com/v2/weapons/", "weapons")
    print(f"  Got {len(weapons)} weapons")
    
    # Fetch armor
    print("\nFetching armor...")
    armor = fetch_paginated("https://api.open5e.com/v2/armor/", "armor")
    print(f"  Got {len(armor)} armor pieces")
    
    # Convert items
    print("\nConverting items...")
    game_objects = []
    seen_names = set()
    
    for item in items:
        obj = convert_item(item)
        if obj['name'] not in seen_names:
            game_objects.append(obj)
            seen_names.add(obj['name'])
    
    # Add weapons as items (for base weapon stats)
    for weapon in weapons:
        name = weapon.get('name', 'Unknown')
        if name not in seen_names:
            obj = {
                'name': name,
                'description': f"Damage: {weapon.get('damage_dice', '1d4')} {weapon.get('damage_type', {}).get('name', 'bludgeoning')}",
                'type': 'Weapon',
                'rarity': 'common',
                'material': infer_material(name, '', 'weapon'),
                'essence': calculate_essence(infer_material(name, '', 'weapon'), 'common', False),
                'size': estimate_size(name),
                'weight': 0,
                'magical': False,
                'source': 'open5e',
            }
            game_objects.append(obj)
            seen_names.add(name)
    
    # Add armor
    for arm in armor:
        name = arm.get('name', 'Unknown')
        if name not in seen_names:
            obj = {
                'name': name,
                'description': f"AC: {arm.get('ac_display', 'unknown')}",
                'type': 'Armor',
                'rarity': 'common',
                'material': infer_material(name, '', 'armor'),
                'essence': calculate_essence(infer_material(name, '', 'armor'), 'common', False),
                'size': 'medium',
                'weight': float(arm.get('weight', 0) or 0),
                'magical': False,
                'source': 'open5e',
            }
            game_objects.append(obj)
            seen_names.add(name)
    
    # Save
    output_path = Path('game_objects_open5e.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(game_objects, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"SAVED {len(game_objects)} game objects to {output_path}")
    print('='*60)
    
    # Stats
    materials = {}
    types = {}
    for obj in game_objects:
        materials[obj['material']] = materials.get(obj['material'], 0) + 1
        types[obj['type']] = types.get(obj['type'], 0) + 1
    
    print("\nMaterials:")
    for m, c in sorted(materials.items(), key=lambda x: -x[1])[:15]:
        print(f"  {m}: {c}")
    
    print("\nTypes:")
    for t, c in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f"  {t}: {c}")

if __name__ == '__main__':
    main()