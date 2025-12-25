# Elemental Magic Spell System

A word-based magic system where:
- **Words ARE spells** - Each word has an elemental composition that determines its power
- **Transformations unlock new spells** - Add/subtract elements or permute to discover new magic
- **Phonetics match mechanics** - Fire spells sound sharp (k, t, sh), water spells flow (l, m, n), etc.

## 🎯 Core Concept

Every spell has a 4-dimensional elemental vector `(fire, water, earth, air)` where each value is 0-63:

```python
"krata" (fireball) = (58, 5, 10, 12)  # High fire, low others
"lumno" (heal)     = (8, 55, 15, 18)  # High water
"brudo" (shield)   = (12, 10, 60, 8)  # High earth
"heisef" (wind)    = (8, 10, 5, 58)   # High air
```

## 🔮 How Spells Work

### 1. Cast a Spell
```python
from spell_system import SpellDictionary, SpellExecutor, Creature

# Load spell dictionary
dictionary = SpellDictionary('elemental_spells.json')

# Create combatants
player = Creature("Hero", hp=100)
goblin = Creature("Goblin", hp=50)

# Cast fireball
spell_data = dictionary.get_spell("krata")
executor = SpellExecutor(spell_data)
messages = executor.cast(player, [goblin], {})

for msg in messages:
    print(msg)
# > "A blazing sphere of flame erupts from your hands, roaring through the air!"
# > "Goblin takes 46 fire damage! (4/50 HP)"
```

### 2. Transform Spells

**Add Elements:**
```python
# Transform "heal" by adding 40 fire
base = "lumno"  # heal: (8, 55, 15, 18)
new_word = dictionary.transform_spell(base, fire=40)
# Result: "tralum" (steam) = (48, 55, 15, 18)

# What was healing water becomes scalding steam!
```

**Permute Elements (Anagrams):**
```python
# Swap fire↔water elements
new_word = dictionary.permute_spell("krata", "swap_fw")
# fireball (58,5,10,12) → (5,58,10,12) → Different spell!

# Rotate elements left
new_word = dictionary.permute_spell("heysa", "rotate_left")
# abandon (40,36,30,58) → (36,30,58,40) → New combination!
```

## 🧪 Transformation Types

### Elemental Addition/Subtraction
```python
dictionary.transform_spell(word, fire=±N, water=±N, earth=±N, air=±N)
```

**Examples:**
- `"kata" + 20 earth` → Ignite becomes more solid/lasting
- `"lumno" + 40 fire` → Heal becomes Steam (damage instead!)
- `"brudo" - 30 earth + 30 fire` → Shield becomes Weapon

### Anagram Permutations
```python
dictionary.permute_spell(word, permutation)
```

**Available permutations:**
- `"swap_fw"` - Swap fire↔water
- `"swap_ea"` - Swap earth↔air
- `"swap_fe"` - Swap fire↔earth
- `"swap_wa"` - Swap water↔air
- `"rotate_left"` - (f,w,e,a) → (w,e,a,f)
- `"rotate_right"` - (f,w,e,a) → (a,f,w,e)
- `"reverse"` - (f,w,e,a) → (a,e,w,f)

## 📊 Spell Effect Types

### Damage
```json
{
  "type": "damage",
  "amount": "fire * 0.8",
  "element": "fire",
  "description": "A blazing fireball..."
}
```

### Heal
```json
{
  "type": "heal",
  "amount": "water * 0.7",
  "remove_status": ["burning", "poison"],
  "description": "Soothing waters..."
}
```

### Status Effects
```json
{
  "type": "apply_status",
  "status": "frozen",
  "duration": "water / 10",
  "effects": [
    {"type": "modify", "modify": "speed", "value": -999}
  ]
}
```

### Area Effects
```json
{
  "type": "area_effect",
  "radius": "earth / 10",
  "effects": [
    {"type": "damage", "amount": "fire", "to": "all"},
    {"type": "apply_status", "status": "burning", "to": "all"}
  ]
}
```

### Create Objects
```json
{
  "type": "create_object",
  "object_class": "Shield",
  "properties": {
    "hp": "earth",
    "blocks": "physical"
  }
}
```

### Summon Creatures
```json
{
  "type": "summon",
  "creature": "Fire Elemental",
  "hp": "fire * 0.6",
  "duration": "fire / 10"
}
```

### Buffs/Debuffs
```json
{
  "type": "buff",
  "stat": "speed",
  "amount": "air * 0.5",
  "duration": "air / 10"
}
```

### Transform
```json
{
  "type": "transform",
  "into": "Stone Statue",
  "description": "Target turns to stone!"
}
```

## 🎮 Game Design Patterns

### Spell Discovery
Players discover spells through experimentation:
```python
# Player has "stone" and knows adding fire makes things hot
stone_vector = (5, 5, 60, 5)
add_fire = (40, 0, 0, 0)
result = (45, 5, 60, 5)  # Look up in dictionary
# Discovers "magma" spell!
```

### Spell Crafting
Combine multiple transformation steps:
```python
base = "lumno"  # heal
step1 = transform(base, fire=40)      # → steam
step2 = transform(step1, air=20)      # → cloud
step3 = permute(step2, "rotate_left") # → ?
```

### Counter Spells
Use transformations in combat:
```python
# Enemy casts water shield
enemy_spell = "lumno" (8, 55, 15, 18)

# Player adds fire mid-flight
transformed = transform(enemy_spell, fire=40)
# Shield becomes "steam" - damages enemy instead!
```

### Recipe System
Hidden recipes for players to discover:
```python
RECIPES = {
    "phoenix": {
        "start": "death",
        "steps": [
            {"permute": "swap_fe"},  # Fire↔earth
            {"add": (0, 0, 0, 15)},  # Add air
        ]
    }
}
```

## 💡 Formula System

Spell effects can use formulas based on composition:

```json
{
  "amount": "fire * 0.8",           // 80% of fire value
  "duration": "water / 10",         // Water ÷ 10 turns
  "radius": "earth / 5 + air / 10", // Combined elements
  "hp": "fire + earth"              // Sum of elements
}
```

## 🔥 Example Spell Progressions

### Fire Damage Chain
```
"kata" (45,5,10,8)     → Small fire (ignite)
  +10 fire
"krata" (55,5,10,8)    → Fireball  
  +5 fire, +40 air
"kratsei" (60,5,10,48) → Lightning
  +40 earth
"kratgod" (60,5,50,8)  → Meteor
```

### Healing → Damage
```
"lumno" (8,55,15,18)   → Heal
  +40 fire
"tralum" (48,55,15,18) → Steam (damage!)
```

### Movement Spells
```
"heisef" (8,10,5,58)   → Wind (push)
  +7 fire
"seifya" (15,12,8,60)  → Teleport
  +40 fire
"yeisef" (20,10,8,55)  → Haste (speed buff)
```

## 🎯 Running the Demo

```bash
python spell_system.py
```

This will run a combat demo showing:
1. Basic spell casting (fireball)
2. Status effects (abandon)
3. Healing
4. Spell transformation (heal → steam)
5. Summoning

## 📁 Files

- `spell_system.py` - Core classes and combat demo
- `elemental_spells.json` - Spell database (20 spells)
- `elemental_template.json` - Language template for generating words

## 🔮 Extending the System

### Add New Spells
Edit `elemental_spells.json`:
```json
{
  "my_spell.v.01": {
    "word": "newword",
    "spirit": "fire",
    "composition": {"fire": 50, "water": 10, "earth": 20, "air": 15},
    "definition": "does something cool",
    "spell_effect": {
      "type": "damage",
      "amount": 30,
      "description": "Cool effect!"
    }
  }
}
```

### Add New Effect Types
Add handler to `SpellExecutor`:
```python
def _my_effect(self, caster, targets, context):
    messages = [self.effect['description']]
    # Your logic here
    return messages
```

### Create Transformation Puzzles
Design specific vector relationships:
```python
# Opposite spells (swap primary elements)
"create" = (10, 40, 30, 15)
"destroy" = (40, 10, 15, 30)  # Fire↔water, earth↔air

# Elemental ladder (incremental progression)
"ember"   = (20, 5, 5, 5)
"flame"   = (35, 5, 5, 5)  # +15 fire
"blaze"   = (50, 5, 5, 5)  # +15 fire
"inferno" = (63, 5, 5, 5)  # +13 fire (max)
```

## 🌟 The Beauty

**The language IS the magic system.**

- Words are reagents you combine
- Phonetics create atmosphere (fire spells SOUND aggressive)
- Transformations are puzzles
- Discovery is emergent gameplay

Cast well! 🔥💧🌍💨
