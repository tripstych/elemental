# WordNet Object Extraction System

## Overview
Systematically extracted **3,803 physical objects** from WordNet to populate your game world with dissolvable items for the alchemy system.

**Key Design Decision:** No essence/composition values included - those come from your language system (glockblocks).

## What You Got

### Total Objects: 3,803

#### By Category:
- **Trees**: 736 (oak, pine, marblewood, lancewood, etc.)
- **Plants**: 729 (herbs, flowers, vines, etc.)
- **Containers**: 513 (barrels, vessels, bottles, chests)
- **Food**: 440 (all organic material)
- **Fabrics**: 267 (cloth, silk, wool, linen)
- **Buildings**: 240 (structures, dwellings, towers)
- **Tools**: 237 (hammers, saws, plows, chisels)
- **Furniture**: 156 (chairs, tables, beds, wardrobes)
- **Liquids**: 151 (water, oils, solutions)
- **Weapons**: 128 (swords, bows, axes, spears)
- **Metals**: 123 (iron, copper, bronze, steel)
- **Gems**: 52 (diamonds, rubies, sapphires, opals)
- **Stones**: 31 (granite, marble, pebbles, boulders)

#### By Material:
- Wood: 2,656 (70% - makes sense for natural world)
- Organic: 414 (food items)
- Cloth: 230
- Metal: 151
- Rope: 125
- Stone: 105
- Glass: 35
- Gold: 22
- Leather: 19
- Paper: 16
- Silver: 11
- Bone: 11
- Wax: 6
- Ceramic: 2

## File Structure

Each object has:
```json
{
  "name": "sword",
  "type": "weapons",
  "material": "metal",
  "size": "medium",
  "weight": 10.0,
  "definition": "a cutting or thrusting weapon...",
  "source": "wordnet",
  "synset": "sword.n.01"
}
```

**NO essence composition** - intentionally left out so your language system controls that.

## Files Included

1. **game_objects_wordnet.json** - The full database (3,803 objects)
2. **wordnet_object_extractor.py** - The extraction script
3. **analyze_objects.py** - Analysis/exploration tool

## Usage

### Running the Extractor
```bash
python3 wordnet_object_extractor.py
```

This will:
1. Query WordNet for each major category
2. Extract all hyponyms (subcategories)
3. Infer material, size, weight from definitions
4. Save to `game_objects_wordnet.json`

### Analyzing the Data
```bash
python3 analyze_objects.py
```

Shows breakdowns by category, material, size, plus interesting examples.

## Customization

### Adding New Categories
Edit the `MAJOR_CATEGORIES` dict in `wordnet_object_extractor.py`:

```python
MAJOR_CATEGORIES = {
    'trees': 'tree.n.01',
    'weapons': 'weapon.n.01',
    # Add new:
    'vehicles': 'vehicle.n.01',
    'musical_instruments': 'musical_instrument.n.01',
}
```

### Adjusting Depth
Change `max_depth` parameter to get more/fewer subcategories:
- `max_depth=2` → Fewer, broader items
- `max_depth=4` → More specific items (may include obscure things)

### Material Inference
The script infers materials from keywords and definitions. Edit these dicts:
- `MATERIAL_KEYWORDS` - Keyword → material mapping
- `TYPE_DEFAULT_MATERIALS` - Fallback by object type

## Integration with Your System

This database gives you **what exists** in the world. Your language/alchemy system provides:
1. **Elemental composition** (fire/water/earth/air values)
2. **Dissolution mechanics** (which solvents extract what)
3. **Spell transformation** (object → spell conversion)

## Examples of What You Can Now Do

### Dissolve a Tree
```python
object = find_object("oak")
# {name: "oak", material: "oak", ...}

# Your alchemy system provides essence values:
essence = get_essence_from_material("oak")
# {fire: 28, water: 12, earth: 18, air: 5}

# Dissolve with Aqua Ignis
extracted = dissolve(object, "aqua_ignis")
# Extracts fire + air
```

### Populate a Room
```python
furniture = get_objects_by_type("furniture")
# ['chair', 'table', 'bed', 'wardrobe', 'desk', ...]

# Room now has dissolvable furniture!
```

### Loot a Battlefield
```python
weapons = get_objects_by_type("weapons")
containers = get_objects_by_type("containers")

# Dead enemies drop swords, axes, etc.
# All can be dissolved for essences
```

## Cool Findings

### Gem Variety
52 different gems! Perfect for rare alchemy ingredients:
- Diamond, ruby, sapphire, emerald
- Moonstone, sunstone, bloodstone
- Fire opal, black opal
- Alexandrite, chrysoberyl
- Lapis lazuli, turquoise, jade

### Tree Diversity
736 different trees! From common (oak, pine) to exotic (marblewood, lancewood, ice-cream bean).

### Weapon Types
128 weapons from bows to swords to siege engines. All dissolvable!

### Container Variety
513 containers from tiny vials to massive barrels to bathtubs.

## Next Steps

1. **Connect to language system**: Map materials → elemental words
2. **Define dissolution rules**: Which solvents extract what from each material
3. **Create world generator**: Populate terrain with appropriate objects
4. **Design rare materials**: Special essence values for gems, dragon parts, etc.

## Notes

- Some weird materials detected (e.g., "wheelchair" → "rope") due to keyword matching
- Most objects defaulted to "medium" size - may want manual refinement
- Food items all marked "organic" - could subdivide (meat, grain, fruit)
- Buildings might be too large-scale for alchemy - consider filtering

## The Vision

Your game world now has 3,803 dissolvable objects. Every tree, weapon, piece of furniture, container, gem, and tool can be:
1. Found/gathered
2. Dissolved in solvents
3. Converted to elemental essences
4. Used to cast spells or transform other objects

**Magic is physical. Magic is costly. Magic is earned.**

🧪✨
