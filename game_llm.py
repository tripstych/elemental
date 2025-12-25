"""
Elemental RPG - LLM Text Interface
Run this for LLM-friendly turn-based gameplay via stdin/stdout.

Commands:
  Movement: n, s, e, w (or north, south, east, west)
  Actions: look, pickup, attack, wait
  Spells: cast fireball, cast heal
  Items: inventory, use <#>, drop <#>, dissolve
  Info: stats, map, help
  Meta: quit

The game outputs structured state after each command.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'seed'))

from game import GameWorld
from seed.dungeon_generator import DungeonGenerator


class LLMGameInterface:
    """Clean text interface for LLM interaction"""
    
    def __init__(self, seed: int = None):
        self.world = GameWorld(width=40, height=20, seed=seed)
        self.world.spawn_player("Hero")
        
        # Spawn fewer monsters for cleaner testing
        for _ in range(3):
            self.world.spawn_monster(near_player=True)
        
        self.world.scatter_items(8)
        
        # Spawn some solvents
        self._spawn_solvents()
        
        self.turn = 0
        self.messages = []
        self.running = True
        
        # Spell definitions
        self.spell_defs = {
            'fireball': {
                'synset': 'fireball.n.01',
                'word': 'krata',
                'composition': {'fire': 30, 'water': 5, 'earth': 5, 'air': 10},
                'definition': 'a ball of fire (30 fire damage)',
                'spell_effect': {'type': 'damage', 'element': 'fire'}
            },
            'heal': {
                'synset': 'heal.v.01',
                'word': 'lumno',
                'composition': {'fire': 5, 'water': 30, 'earth': 10, 'air': 5},
                'definition': 'restore health (30 HP)',
                'spell_effect': {'type': 'heal', 'amount': 30}
            }
        }
    
    def _spawn_solvents(self):
        """Add some solvents to the dungeon"""
        from seed.dungeon_generator import DungeonGenerator
        floors = self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR)
        
        solvents = [
            {'name': 'Aqua Ignis', 'type': 'solvent', 'solvent_type': 'aqua_ignis', 'weight': 0.5},
            {'name': 'Alkahest', 'type': 'solvent', 'solvent_type': 'alkahest', 'weight': 0.5},
        ]
        
        import random
        for solvent in solvents:
            if floors:
                pos = random.choice(floors)
                if pos not in self.world.items_on_ground:
                    self.world.items_on_ground[pos] = []
                self.world.items_on_ground[pos].append(solvent.copy())
    
    def msg(self, text: str):
        """Add a message"""
        self.messages.append(text)
    
    def get_state(self) -> dict:
        """Get current game state as structured data"""
        player = self.world.player
        pos = (player.x, player.y)
        
        # Items at current position
        items_here = []
        if pos in self.world.items_on_ground:
            items_here = [i['name'] for i in self.world.items_on_ground[pos]]
        
        # Nearby monsters
        nearby_monsters = []
        for m in self.world.monsters:
            if m.stats.is_alive():
                dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                if dist <= 10:
                    dx = m.x - player.x
                    dy = m.y - player.y
                    direction = []
                    if dy < 0: direction.append("north")
                    if dy > 0: direction.append("south")
                    if dx > 0: direction.append("east")
                    if dx < 0: direction.append("west")
                    nearby_monsters.append({
                        'name': m.name,
                        'hp': f"{m.stats.current_health}/{m.stats.max_health}",
                        'distance': round(dist, 1),
                        'direction': '-'.join(direction) if direction else 'here',
                        'adjacent': dist <= 1.5
                    })
        
        # What's around in each direction
        surroundings = {}
        for dir_name, (dx, dy) in [('north', (0,-1)), ('south', (0,1)), ('east', (1,0)), ('west', (-1,0))]:
            nx, ny = player.x + dx, player.y + dy
            if self.world.is_walkable(nx, ny):
                entity = self.world.get_entity_at(nx, ny)
                if entity and entity != player:
                    surroundings[dir_name] = f"monster ({entity.name})"
                elif (nx, ny) in self.world.items_on_ground:
                    surroundings[dir_name] = "item"
                else:
                    surroundings[dir_name] = "open"
            else:
                surroundings[dir_name] = "wall"
        
        # Inventory summary
        inv_items = [f"{i+1}. {obj['name']} ({obj.get('type', '?')})" 
                     for i, obj in enumerate(player.inventory.objects[:10])]
        
        state = {
            'turn': self.turn,
            'player': {
                'hp': f"{player.stats.current_health}/{player.stats.max_health}",
                'level': player.level,
                'xp': f"{player.experience}/{player.level * 100}",
                'position': f"({player.x}, {player.y})",
                'essences': {k: int(v) for k, v in player.inventory.essences.items()},
                'max_essence': int(player.inventory.max_essence),
            },
            'surroundings': surroundings,
            'items_here': items_here,
            'nearby_monsters': nearby_monsters,
            'inventory': inv_items,
            'inventory_count': len(player.inventory.objects),
            'messages': self.messages[-5:],  # Last 5 messages
            'available_commands': self._get_contextual_commands(),
        }
        
        return state
    
    def _get_contextual_commands(self) -> list:
        """Get commands that make sense right now"""
        player = self.world.player
        pos = (player.x, player.y)
        cmds = ['n', 's', 'e', 'w', 'look', 'stats', 'inventory', 'map', 'wait']
        
        # Can pickup?
        if pos in self.world.items_on_ground and self.world.items_on_ground[pos]:
            cmds.append('pickup')
        
        # Can attack?
        for m in self.world.monsters:
            if m.stats.is_alive():
                dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                if dist <= 1.5:
                    cmds.append('attack')
                    break
        
        # Can cast?
        ess = player.inventory.essences
        if ess['fire'] >= 30:
            cmds.append('cast fireball')
        if ess['water'] >= 30:
            cmds.append('cast heal')
        
        # Has items?
        if player.inventory.objects:
            cmds.append('use <#>')
            cmds.append('drop <#>')
            # Check for solvent + item combo
            has_solvent = any(o.get('type') == 'solvent' for o in player.inventory.objects)
            has_dissolvable = any(o.get('type') != 'solvent' for o in player.inventory.objects)
            if has_solvent and has_dissolvable:
                cmds.append('dissolve')
        
        return cmds
    
    def process(self, command: str) -> dict:
        """Process a command and return new state"""
        self.messages = []
        cmd = command.strip().lower()
        
        if not cmd:
            self.msg("Enter a command. Type 'help' for options.")
            return self.get_state()
        
        player = self.world.player
        parts = cmd.split()
        action = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Movement
        dir_map = {
            'n': (0, -1), 'north': (0, -1),
            's': (0, 1), 'south': (0, 1),
            'e': (1, 0), 'east': (1, 0),
            'w': (-1, 0), 'west': (-1, 0),
        }
        
        if action in dir_map:
            dx, dy = dir_map[action]
            new_x, new_y = player.x + dx, player.y + dy
            
            entity = self.world.get_entity_at(new_x, new_y)
            if entity and entity != player:
                self.msg(f"Blocked by {entity.name}!")
            elif not self.world.is_walkable(new_x, new_y):
                self.msg("Wall.")
            else:
                player.x, player.y = new_x, new_y
                self.turn += 1
                self.msg(f"Moved {action}.")
                self._check_position()
                self._monster_turns()
        
        elif action == 'look':
            self._describe_location()
        
        elif action == 'attack':
            self._do_attack()
        
        elif action == 'cast':
            spell = args[0] if args else None
            self._do_cast(spell)
        
        elif action in ['pickup', 'get', 'take']:
            self._do_pickup()
        
        elif action in ['inventory', 'inv', 'i']:
            self._show_inventory()
        
        elif action == 'use':
            num = int(args[0]) if args else None
            self._do_use(num)
        
        elif action == 'drop':
            num = int(args[0]) if args else None
            self._do_drop(num)
        
        elif action == 'dissolve':
            self._do_dissolve()
        
        elif action == 'stats':
            self._show_stats()
        
        elif action == 'map':
            self._show_map()
        
        elif action == 'wait':
            self.turn += 1
            self.msg("Waited.")
            self._monster_turns()
        
        elif action == 'help':
            self.msg("Commands: n/s/e/w, look, attack, cast <spell>, pickup, inventory, use <#>, drop <#>, dissolve, stats, map, wait, quit")
        
        elif action in ['quit', 'exit', 'q']:
            self.running = False
            self.msg("Game ended.")
        
        else:
            self.msg(f"Unknown: {action}. Type 'help'.")
        
        # Check death
        if not player.stats.is_alive():
            self.msg("YOU DIED! Resurrecting...")
            player.stats.current_health = player.stats.max_health
            entrance = self.world.dungeon.find_positions(DungeonGenerator.ENTRANCE)
            if entrance:
                player.x, player.y = entrance[0]
        
        return self.get_state()
    
    def _check_position(self):
        """Check what's at current position"""
        player = self.world.player
        pos = (player.x, player.y)
        
        if pos in self.world.items_on_ground and self.world.items_on_ground[pos]:
            items = self.world.items_on_ground[pos]
            self.msg(f"Items here: {', '.join(i['name'] for i in items)}")
        
        tile = self.world.dungeon.grid[player.y, player.x]
        if tile == DungeonGenerator.EXIT:
            self.msg("You found the exit!")
    
    def _describe_location(self):
        """Describe current location"""
        player = self.world.player
        self.msg(f"Position: ({player.x}, {player.y})")
        self._check_position()
        
        for m in self.world.monsters:
            if m.stats.is_alive():
                dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                if dist <= 5:
                    self.msg(f"{m.name} nearby (HP: {m.stats.current_health}/{m.stats.max_health}, dist: {dist:.1f})")
    
    def _do_attack(self):
        """Attack adjacent monster"""
        player = self.world.player
        target = None
        
        for dx, dy in [(0,-1), (1,0), (0,1), (-1,0)]:
            entity = self.world.get_entity_at(player.x + dx, player.y + dy)
            if entity and entity != player and entity.stats.is_alive():
                target = entity
                break
        
        if not target:
            self.msg("No adjacent enemy.")
            return
        
        result = player.attack(target)
        if result['success']:
            self.msg(f"Hit {target.name} for {result['damage']} damage!")
            if not result['target_alive']:
                self.msg(f"{target.name} defeated!")
                xp = 25
                lvl_result = player.gain_xp(xp)
                self.msg(f"+{xp} XP!")
                if lvl_result['leveled_up']:
                    self.msg(f"LEVEL UP! Now level {lvl_result['new_level']}!")
            
            self.turn += 1
            self._monster_turns()
    
    def _do_cast(self, spell_name: str):
        """Cast a spell"""
        if not spell_name or spell_name not in self.spell_defs:
            self.msg(f"Spells: {', '.join(self.spell_defs.keys())}")
            return
        
        player = self.world.player
        spell = self.spell_defs[spell_name]
        
        # Check essence
        cost = spell['composition']
        if not player.inventory.has_essence(cost):
            self.msg(f"Not enough essence! Need: {cost}")
            return
        
        # Find target for damage
        target = None
        if spell['spell_effect']['type'] == 'damage':
            for m in self.world.monsters:
                if m.stats.is_alive():
                    dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                    if dist <= 8:
                        target = m
                        break
            if not target:
                self.msg("No target in range!")
                return
        
        # Pay cost
        for elem, amt in cost.items():
            player.inventory.remove_essence(elem, amt)
        
        # Apply effect
        if spell['spell_effect']['type'] == 'damage' and target:
            damage = 30 + player.stats.magic_power // 2
            target.stats.take_damage(damage)
            self.msg(f"FIREBALL hits {target.name} for {damage}!")
            if not target.stats.is_alive():
                self.msg(f"{target.name} destroyed!")
                xp = 30
                lvl_result = player.gain_xp(xp)
                self.msg(f"+{xp} XP!")
                if lvl_result['leveled_up']:
                    self.msg(f"LEVEL UP! Level {lvl_result['new_level']}!")
        
        elif spell['spell_effect']['type'] == 'heal':
            amount = spell['spell_effect']['amount']
            player.stats.heal(amount)
            self.msg(f"Healed {amount} HP! Now: {player.stats.current_health}/{player.stats.max_health}")
        
        self.turn += 1
        self._monster_turns()
    
    def _do_pickup(self):
        """Pick up items"""
        player = self.world.player
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground or not self.world.items_on_ground[pos]:
            self.msg("Nothing to pick up.")
            return
        
        items = self.world.items_on_ground[pos]
        for item in items[:]:
            if player.inventory.add_object(item):
                items.remove(item)
                self.msg(f"Picked up: {item['name']}")
        
        if not items:
            del self.world.items_on_ground[pos]
    
    def _show_inventory(self):
        """Show inventory"""
        player = self.world.player
        inv = player.inventory
        
        if not inv.objects:
            self.msg("Inventory empty.")
        else:
            for i, obj in enumerate(inv.objects[:10]):
                self.msg(f"  {i+1}. {obj['name']} ({obj.get('type', '?')})")
        
        self.msg(f"Essences: F:{int(inv.essences['fire'])} W:{int(inv.essences['water'])} E:{int(inv.essences['earth'])} A:{int(inv.essences['air'])} (max: {int(inv.max_essence)})")
    
    def _do_use(self, num: int):
        """Use an item"""
        player = self.world.player
        inv = player.inventory
        
        if not num or num < 1 or num > len(inv.objects):
            self.msg("Use which item? (use <number>)")
            return
        
        item = inv.objects[num - 1]
        
        if item.get('type') == 'food':
            heal = 20
            player.stats.heal(heal)
            inv.objects.pop(num - 1)
            self.msg(f"Ate {item['name']}, healed {heal} HP.")
        elif item.get('type') == 'gems':
            import random
            elem = random.choice(['fire', 'water', 'earth', 'air'])
            amt = 15
            added = inv.add_essence(elem, amt)
            inv.objects.pop(num - 1)
            self.msg(f"Gem gave +{int(added)} {elem} essence.")
        else:
            self.msg(f"Can't use {item['name']}.")
    
    def _do_drop(self, num: int):
        """Drop an item"""
        player = self.world.player
        inv = player.inventory
        
        if not num or num < 1 or num > len(inv.objects):
            self.msg("Drop which? (drop <number>)")
            return
        
        item = inv.objects.pop(num - 1)
        pos = (player.x, player.y)
        if pos not in self.world.items_on_ground:
            self.world.items_on_ground[pos] = []
        self.world.items_on_ground[pos].append(item)
        self.msg(f"Dropped {item['name']}.")
    
    def _do_dissolve(self):
        """Dissolve item with solvent (simplified)"""
        player = self.world.player
        inv = player.inventory
        
        solvents = [(i, o) for i, o in enumerate(inv.objects) if o.get('type') == 'solvent']
        items = [(i, o) for i, o in enumerate(inv.objects) if o.get('type') != 'solvent']
        
        if not solvents:
            self.msg("No solvent in inventory.")
            return
        if not items:
            self.msg("No items to dissolve.")
            return
        
        # Use first solvent on first item
        solvent_idx, solvent = solvents[0]
        item_idx, item = items[0]
        
        # Extract essence based on item type
        essence_map = {
            'weapons': {'fire': 20, 'earth': 30},
            'tools': {'earth': 25, 'fire': 15},
            'gems': {'fire': 20, 'water': 20, 'earth': 20, 'air': 20},
            'food': {'water': 25, 'earth': 15},
        }
        
        gains = essence_map.get(item.get('type'), {'fire': 10, 'water': 10, 'earth': 10, 'air': 10})
        
        for elem, amt in gains.items():
            added = inv.add_essence(elem, amt)
            if added > 0:
                self.msg(f"+{int(added)} {elem}")
        
        # Remove items (higher index first)
        if item_idx > solvent_idx:
            inv.objects.pop(item_idx)
            inv.objects.pop(solvent_idx)
        else:
            inv.objects.pop(solvent_idx)
            inv.objects.pop(item_idx)
        
        self.msg(f"Dissolved {item['name']} with {solvent['name']}!")
    
    def _show_stats(self):
        """Show player stats"""
        player = self.world.player
        s = player.stats
        self.msg(f"Level {player.level} | XP: {player.experience}/{player.level * 100}")
        self.msg(f"HP: {s.current_health}/{s.max_health} | ATK: {s.attack_power} | DEF: {s.defense}")
        self.msg(f"Magic: {s.magic_power} | Essence cap: {int(player.inventory.max_essence)}")
    
    def _show_map(self):
        """Show mini-map"""
        self.msg("Map: @ = you, M = monster, ! = item, # = wall")
        self.msg(self.world.render())
    
    def _monster_turns(self):
        """Monster AI"""
        player = self.world.player
        
        for monster in self.world.monsters:
            if not monster.stats.is_alive():
                continue
            
            dist = monster.distance_to(player)
            
            if dist <= 1.5:
                result = monster.attack(player)
                if result['success']:
                    self.msg(f"{monster.name} hits you for {result['damage']}! HP: {player.stats.current_health}/{player.stats.max_health}")
            elif dist < 8:
                # Move toward player
                dx = 1 if player.x > monster.x else -1 if player.x < monster.x else 0
                dy = 1 if player.y > monster.y else -1 if player.y < monster.y else 0
                new_x, new_y = monster.x + dx, monster.y + dy
                if self.world.is_walkable(new_x, new_y) and not self.world.get_entity_at(new_x, new_y):
                    monster.x, monster.y = new_x, new_y


def main():
    """Main game loop for LLM interaction"""
    print("=" * 60)
    print("ELEMENTAL RPG - LLM Test Interface")
    print("=" * 60)
    print("Type commands. Game state is returned as JSON after each turn.")
    print("Commands: n/s/e/w, look, attack, cast <spell>, pickup,")
    print("          inventory, use <#>, drop <#>, dissolve, stats, map, help, quit")
    print("=" * 60)
    
    game = LLMGameInterface(seed=42)  # Fixed seed for reproducibility
    
    # Print initial state
    state = game.get_state()
    print("\n--- INITIAL STATE ---")
    print(json.dumps(state, indent=2))
    
    while game.running:
        try:
            cmd = input("\n> ").strip()
        except EOFError:
            break
        
        state = game.process(cmd)
        print("\n--- STATE ---")
        print(json.dumps(state, indent=2))
    
    print("\nGame ended.")


if __name__ == "__main__":
    main()
