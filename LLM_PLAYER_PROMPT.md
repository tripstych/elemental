# Elemental RPG - LLM Player Prompt

You are playing **Elemental RPG**, a dungeon crawler with combat, spells, and alchemy. You interact with the game via a REST API.

## Your Goal
Explore the dungeon, defeat monsters, collect items, and level up. Use spells and alchemy wisely to manage your elemental essences.

---

## API Endpoints

Base URL: `http://localhost:5000`

### State (GET)
| Endpoint | Returns |
|----------|---------|
| `/state` | Full game state (player, visible entities, messages) |
| `/visible` | Visible monsters/items with relative positions |
| `/inventory` | Player inventory and essences |
| `/spells` | Available spells and costs |

### Actions (POST)
| Endpoint | Body | Effect |
|----------|------|--------|
| `/action` | `{"action": "n"}` | Move north (also: s, e, w) |
| `/action` | `{"action": "attack"}` | Attack adjacent monster |
| `/action` | `{"action": "wait"}` | Skip turn |
| `/pickup` | - | Pick up items at current position |
| `/cast/fireball` | - | Cast fireball (30 fire essence, damages nearest enemy) |
| `/cast/heal` | - | Cast heal (30 water essence, restores 30 HP) |
| `/use/<id>` | - | Use inventory item by index |
| `/drop/<id>` | - | Drop inventory item |
| `/dissolve` | `{"item_id": 0, "solvent_id": 1}` | Dissolve item with solvent for essences |
| `/reset` | `{"seed": 42}` | Reset game (optional seed) |

---

## Understanding Position Format

Positions are relative to you. Format: `<direction><distance>`

| Position | Meaning |
|----------|---------|
| `n3` | 3 tiles north of you |
| `s2e5` | 2 south, 5 east |
| `here` | Same tile as you |
| `n1` | 1 tile north (adjacent) |

**Adjacent** means distance ≤ 1.5 (can attack/bump into).

---

## Game State Response

When you call `/state`, you receive:

```json
{
  "turn": 5,
  "player": {
    "position": {"x": 15, "y": 10},
    "hp": 85,
    "max_hp": 100,
    "level": 1,
    "xp": 25,
    "xp_next": 100,
    "essences": {"fire": 70, "water": 100, "earth": 100, "air": 100},
    "max_essence": 100,
    "attack": 20,
    "defense": 12
  },
  "visible": {
    "monsters": [
      {"name": "Goblin", "pos": "n3e2", "hp": 25, "max_hp": 40, "adjacent": false}
    ],
    "items": [
      {"name": "Sword", "type": "weapons", "pos": "s1w4"}
    ]
  },
  "surroundings": {
    "n": "open",
    "s": "wall",
    "e": "monster:Goblin",
    "w": "items:2"
  },
  "messages": ["Goblin hits you for 8 damage!"]
}
```

---

## Combat Strategy

1. **Melee Attack**: Move into a monster OR use `/action {"action": "attack"}` when adjacent
2. **Spells**: Use `/cast/fireball` for ranged damage (costs 30 fire essence)
3. **Healing**: Use `/cast/heal` when HP is low (costs 30 water essence)

### Combat Tips
- Check `adjacent: true` to know if you can melee attack
- Monsters attack back if adjacent - don't stand next to them with low HP
- Killing monsters gives XP (25-30) and sometimes drops loot
- Level up increases HP, magic power, and **essence capacity**

---

## Essence & Alchemy

You have 4 essences: **fire, water, earth, air**

### Gaining Essences
1. **Dissolve items**: Pick up a **solvent** (Aqua Ignis, Alkahest, etc.) and an item, then dissolve
2. **Use gems**: Using a gem gives random essence
3. **Level up**: Increases max essence by 25

### Solvents
| Solvent | Extracts |
|---------|----------|
| Aqua Ignis | fire, air |
| Oleum Terra | earth, water |
| Alkahest | all four |

### Dissolve Example
```
POST /dissolve
{"item_id": 1, "solvent_id": 0}
```
This dissolves inventory item #1 using solvent #0.

---

## Decision Framework

Each turn, evaluate:

1. **Am I in danger?**
   - HP < 30? Consider `/cast/heal` or retreating
   - Monster adjacent? Attack or move away

2. **Can I attack?**
   - Monster adjacent (`adjacent: true`)? Attack!
   - Monster visible but not adjacent? Move toward it or use fireball

3. **Should I pick up items?**
   - Items at `here` or `pos: "here"`? Use `/pickup`
   - Solvents are valuable for alchemy

4. **Should I use alchemy?**
   - Have solvent + item? Dissolve to replenish essences
   - Low on fire essence? Prioritize dissolving

5. **Where should I explore?**
   - Check `surroundings` for open directions
   - Avoid walls

---

## Example Turn Sequence

```
1. GET /state
   → See Goblin at n2, HP at 85/100

2. POST /action {"action": "n"}
   → Move north, now Goblin at n1 (adjacent)

3. POST /action {"action": "attack"}
   → Hit Goblin for 15 damage, Goblin HP: 10/40

4. GET /state
   → Goblin hit you back for 8, your HP: 77/100

5. POST /action {"action": "attack"}
   → Goblin defeated! +25 XP, dropped Iron Sword

6. POST /pickup
   → Picked up Iron Sword

7. GET /inventory
   → See Iron Sword in inventory
```

---

## Response Format

After each action, respond with:

```
OBSERVATION: <what you learned from the state>
REASONING: <why you're taking this action>
ACTION: <the API call you're making>
```

Example:
```
OBSERVATION: Goblin at n1 (adjacent), my HP is 85/100, I have 70 fire essence
REASONING: Monster is adjacent so I can melee attack. My HP is good, no need to heal.
ACTION: POST /action {"action": "attack"}
```

---

## Win Condition

Survive, level up, and reach the exit (shown in surroundings or visible). Currently the game continues until you quit - focus on:
- Defeating all monsters
- Collecting items
- Reaching higher levels
- Managing your essence economy through alchemy

Good luck, adventurer!
