#!/usr/bin/env python3
"""
Analyze the extracted WordNet objects
"""

import json
from collections import defaultdict

def analyze():
    with open('game_objects_wordnet.json', 'r') as f:
        objects = json.load(f)
    
    print("\n" + "=" * 70)
    print(f"WORDNET OBJECT DATABASE ANALYSIS")
    print(f"Total Objects: {len(objects)}")
    print("=" * 70)
    
    # Interesting examples from each category
    categories = defaultdict(list)
    for obj in objects:
        categories[obj['type']].append(obj)
    
    print("\n🗡️  WEAPONS (sample):")
    weapons = [o for o in categories['weapons'] if 'sword' in o['name'] or 'axe' in o['name'] or 'bow' in o['name']]
    for w in weapons[:10]:
        print(f"  • {w['name']:25s} - {w['material']:10s}")
    
    print("\n🌳 TREES (sample):")
    trees = categories['trees'][:15]
    for t in trees:
        print(f"  • {t['name']:25s} - {t['material']:10s}")
    
    print("\n🪑 FURNITURE (sample):")
    furniture = categories['furniture'][:15]
    for f in furniture:
        print(f"  • {f['name']:25s} - {f['material']:10s}")
    
    print("\n📦 CONTAINERS (sample):")
    containers = categories['containers'][:15]
    for c in containers:
        print(f"  • {c['name']:25s} - {c['material']:10s}")
    
    print("\n🍎 FOOD (sample):")
    food = categories['food'][:15]
    for item in food:
        print(f"  • {item['name']:25s} - {item['material']:10s}")
    
    print("\n💎 GEMS:")
    gems = categories['gems']
    for g in gems:
        print(f"  • {g['name']:25s}")
    
    print("\n🪨 STONES:")
    stones = categories['stones']
    for s in stones:
        print(f"  • {s['name']:25s}")
    
    # Material distribution
    materials = defaultdict(int)
    for obj in objects:
        materials[obj['material']] += 1
    
    print("\n" + "=" * 70)
    print("MATERIAL DISTRIBUTION:")
    print("=" * 70)
    for mat, count in sorted(materials.items(), key=lambda x: -x[1]):
        bar = "█" * (count // 50)
        print(f"  {mat:15s} {count:4d} {bar}")
    
    # Size distribution
    sizes = defaultdict(int)
    for obj in objects:
        sizes[obj['size']] += 1
    
    print("\n" + "=" * 70)
    print("SIZE DISTRIBUTION:")
    print("=" * 70)
    for size in ['tiny', 'small', 'medium', 'large', 'huge']:
        count = sizes[size]
        bar = "█" * (count // 50)
        print(f"  {size:10s} {count:4d} {bar}")

if __name__ == '__main__':
    analyze()
