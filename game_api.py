"""
Elemental RPG - RESTful Game API

Provides HTTP endpoints for game control and state.
Can be used by game_pygame, LLMs, or other clients.

Run: python game_api.py
API: http://localhost:5000

Endpoints:
  GET  /state          - Get full game state
  POST /action         - Perform action (move, attack, etc.)
  GET  /visible        - Get visible entities/items with relative positions
  GET  /inventory      - Get player inventory
  POST /cast/<spell>   - Cast a spell
  POST /use/<item_id>  - Use an inventory item
  POST /pickup         - Pick up items at current position
  POST /dissolve       - Dissolve item with solvent
  POST /reset          - Reset game
"""

import sys
import os
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'seed'))

from game import GameWorld
from seed.dungeon_generator import DungeonGenerator

# Solvent definitions
SOLVENTS = {
    "aqua_ignis": {"name": "Aqua Ignis", "extracts": ["fire", "air"], "strength": 0.8},
    "oleum_terra": {"name": "Oleum Terra", "extracts": ["earth", "water"], "strength": 0.9},
    "alkahest": {"name": "Alkahest", "extracts": ["fire", "water", "earth", "air"], "strength": 1.0},
}

MATERIAL_ESSENCES = {
    'weapons': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'tools': {'fire': 20, 'water': 10, 'earth': 35, 'air': 10},
    'gems': {'fire': 30, 'water': 20, 'earth': 30, 'air': 20},
    'food': {'fire': 5, 'water': 30, 'earth': 20, 'air': 10},
    'liquids': {'fire': 10, 'water': 40, 'earth': 5, 'air': 15},
    'default': {'fire': 15, 'water': 15, 'earth': 15, 'air': 15},
}


class GameSession:
    """Manages a single game session"""
    
    def __init__(self, seed: int = None):
        self.reset(seed)
    
    def reset(self, seed: int = None):
        """Reset/initialize game"""
        self.world = GameWorld(width=60, height=30, seed=seed)
        self.world.spawn_player("Hero")
        
        # Spawn monsters
        for _ in range(5):
            self.world.spawn_monster(near_player=True)
        
        # Scatter items and solvents
        self.world.scatter_items(15)
        self._spawn_solvents()
        
        self.turn = 0
        self.messages = []
        
        # Spell definitions
        self.spell_defs = {
            'fireball': {
                'synset': 'fireball.n.01',
                'composition': {'fire': 30, 'water': 5, 'earth': 5, 'air': 10},
                'effect': {'type': 'damage', 'element': 'fire', 'power': 30}
            },
            'heal': {
                'synset': 'heal.v.01',
                'composition': {'fire': 5, 'water': 30, 'earth': 10, 'air': 5},
                'effect': {'type': 'heal', 'amount': 30}
            },
            'lightning': {
                'synset': 'lightning.n.01',
                'composition': {'fire': 15, 'water': 5, 'earth': 5, 'air': 35},
                'effect': {'type': 'damage', 'element': 'air', 'power': 40}
            },
            'shield': {
                'synset': 'shield.n.01',
                'composition': {'fire': 5, 'water': 10, 'earth': 35, 'air': 10},
                'effect': {'type': 'buff', 'stat': 'defense', 'amount': 10, 'duration': 5}
            }
        }
    
    def _spawn_solvents(self):
        """Spawn solvents in dungeon"""
        floors = self.world.dungeon.find_positions(DungeonGenerator.ROOM_FLOOR)
        import random
        
        solvents = [
            {'name': 'Aqua Ignis', 'type': 'solvent', 'solvent_type': 'aqua_ignis', 'weight': 0.5},
            {'name': 'Oleum Terra', 'type': 'solvent', 'solvent_type': 'oleum_terra', 'weight': 0.5},
            {'name': 'Alkahest', 'type': 'solvent', 'solvent_type': 'alkahest', 'weight': 0.5},
        ]
        
        for solvent in solvents:
            if floors:
                pos = random.choice(floors)
                if pos not in self.world.items_on_ground:
                    self.world.items_on_ground[pos] = []
                self.world.items_on_ground[pos].append(solvent.copy())
    
    def msg(self, text: str):
        """Add message"""
        self.messages.append(text)
    
    def clear_messages(self):
        """Clear and return messages"""
        msgs = self.messages.copy()
        self.messages = []
        return msgs
    
    # =========================================================================
    # POSITION HELPERS
    # =========================================================================
    
    def relative_pos(self, from_x: int, from_y: int, to_x: int, to_y: int) -> str:
        """
        Get relative position string like 'n3e4' (3 north, 4 east).
        Returns empty string if same position.
        """
        dx = to_x - from_x
        dy = to_y - from_y
        
        if dx == 0 and dy == 0:
            return "here"
        
        parts = []
        if dy < 0:
            parts.append(f"n{abs(dy)}")
        elif dy > 0:
            parts.append(f"s{dy}")
        
        if dx > 0:
            parts.append(f"e{dx}")
        elif dx < 0:
            parts.append(f"w{abs(dx)}")
        
        return "".join(parts)
    
    def parse_direction(self, direction: str) -> Tuple[int, int]:
        """Parse direction string to dx, dy"""
        dir_map = {
            'n': (0, -1), 'north': (0, -1), 'up': (0, -1),
            's': (0, 1), 'south': (0, 1), 'down': (0, 1),
            'e': (1, 0), 'east': (1, 0), 'right': (1, 0),
            'w': (-1, 0), 'west': (-1, 0), 'left': (-1, 0),
            'ne': (1, -1), 'nw': (-1, -1),
            'se': (1, 1), 'sw': (-1, 1),
        }
        return dir_map.get(direction.lower(), (0, 0))
    
    # =========================================================================
    # STATE
    # =========================================================================
    
    def get_state(self) -> dict:
        """Get full game state"""
        player = self.world.player
        
        return {
            'turn': self.turn,
            'player': self._player_state(),
            'visible': self.get_visible(),
            'surroundings': self._get_surroundings(),
            'messages': self.clear_messages(),
        }
    
    def _player_state(self) -> dict:
        """Get player state"""
        player = self.world.player
        s = player.stats
        inv = player.inventory
        
        return {
            'name': player.name,
            'position': {'x': player.x, 'y': player.y},
            'hp': s.current_health,
            'max_hp': s.max_health,
            'stamina': s.current_stamina,
            'max_stamina': s.max_stamina,
            'level': player.level,
            'xp': player.experience,
            'xp_next': player.level * 100,
            'essences': {k: int(v) for k, v in inv.essences.items()},
            'max_essence': int(inv.max_essence),
            'attack': s.attack_power,
            'defense': s.defense,
            'magic': s.magic_power,
        }
    
    def _get_surroundings(self) -> dict:
        """Get what's in each direction"""
        player = self.world.player
        result = {}
        
        for dir_name, (dx, dy) in [('n', (0,-1)), ('s', (0,1)), ('e', (1,0)), ('w', (-1,0))]:
            nx, ny = player.x + dx, player.y + dy
            
            if not self.world.is_walkable(nx, ny):
                result[dir_name] = 'wall'
            else:
                entity = self.world.get_entity_at(nx, ny)
                if entity and entity != player:
                    result[dir_name] = f'monster:{entity.name}'
                elif (nx, ny) in self.world.items_on_ground:
                    items = self.world.items_on_ground[(nx, ny)]
                    result[dir_name] = f'items:{len(items)}'
                else:
                    result[dir_name] = 'open'
        
        return result
    
    # =========================================================================
    # VISIBILITY
    # =========================================================================
    
    def get_visible(self, radius: int = 10) -> dict:
        """
        Get all visible entities and items with relative positions.
        Format: "item_name:n3e4" means 3 north, 4 east of player
        """
        player = self.world.player
        fov = self.world.get_player_fov(radius)
        
        # Visible monsters
        monsters = []
        for m in self.world.monsters:
            if m.stats.is_alive() and (m.x, m.y) in fov:
                rel = self.relative_pos(player.x, player.y, m.x, m.y)
                dist = ((m.x - player.x)**2 + (m.y - player.y)**2)**0.5
                monsters.append({
                    'name': m.name,
                    'pos': rel,
                    'hp': m.stats.current_health,
                    'max_hp': m.stats.max_health,
                    'distance': round(dist, 1),
                    'adjacent': dist <= 1.5,
                    'x': m.x,
                    'y': m.y,
                })
        
        # Visible items
        items = []
        for pos, item_list in self.world.items_on_ground.items():
            if pos in fov and item_list:
                rel = self.relative_pos(player.x, player.y, pos[0], pos[1])
                dist = ((pos[0] - player.x)**2 + (pos[1] - player.y)**2)**0.5
                for item in item_list:
                    items.append({
                        'name': item['name'],
                        'type': item.get('type', 'misc'),
                        'pos': rel,
                        'distance': round(dist, 1),
                        'x': pos[0],
                        'y': pos[1],
                    })
        
        # Visible tiles (for map rendering)
        tiles = [(x, y) for x, y in fov if 0 <= x < self.world.width and 0 <= y < self.world.height]
        
        return {
            'monsters': monsters,
            'items': items,
            'tile_count': len(tiles),
            'fov_radius': radius,
        }
    
    def get_visible_formatted(self, radius: int = 10) -> List[str]:
        """
        Get visible things in compact format: "type:name:pos"
        Examples: "monster:Goblin:n3e2", "item:Sword:s1w4"
        """
        visible = self.get_visible(radius)
        result = []
        
        for m in visible['monsters']:
            result.append(f"monster:{m['name']}:{m['pos']}")
        
        for i in visible['items']:
            result.append(f"item:{i['name']}:{i['pos']}")
        
        return result
    
    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def do_action(self, action: str, **kwargs) -> dict:
        """
        Perform an action. Returns result dict.
        
        Actions:
            move <direction>  - Move in direction (n/s/e/w)
            attack            - Attack adjacent enemy
            wait              - Skip turn
            look              - Get detailed look info
        """
        action = action.lower().strip()
        parts = action.split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        result = {'success': False, 'action': cmd}
        
        if cmd in ['n', 's', 'e', 'w', 'north', 'south', 'east', 'west', 'move']:
            direction = args[0] if args else cmd
            result = self._do_move(direction)
        
        elif cmd == 'attack':
            target_pos = kwargs.get('target')
            result = self._do_attack(target_pos)
        
        elif cmd == 'wait':
            self.turn += 1
            self.msg("Waited.")
            self._monster_turns()
            result = {'success': True, 'action': 'wait'}
        
        elif cmd == 'look':
            result = {'success': True, 'action': 'look', 'visible': self.get_visible_formatted()}
        
        elif cmd == 'pickup':
            result = self._do_pickup()
        
        else:
            result = {'success': False, 'error': f'Unknown action: {cmd}'}
        
        # Always include updated state
        result['state'] = self.get_state()
        return result
    
    def _do_move(self, direction: str) -> dict:
        """Move player in direction"""
        player = self.world.player
        dx, dy = self.parse_direction(direction)
        
        if dx == 0 and dy == 0:
            return {'success': False, 'error': f'Invalid direction: {direction}'}
        
        new_x, new_y = player.x + dx, player.y + dy
        
        # Check for entity
        entity = self.world.get_entity_at(new_x, new_y)
        if entity and entity != player:
            return {'success': False, 'error': f'Blocked by {entity.name}', 'blocked_by': entity.name}
        
        # Check walkable
        if not self.world.is_walkable(new_x, new_y):
            return {'success': False, 'error': 'Wall'}
        
        # Move
        player.x, player.y = new_x, new_y
        self.turn += 1
        self.msg(f"Moved {direction}.")
        
        # Check for items
        if (new_x, new_y) in self.world.items_on_ground:
            items = self.world.items_on_ground[(new_x, new_y)]
            if items:
                self.msg(f"Items here: {', '.join(i['name'] for i in items)}")
        
        self._monster_turns()
        
        return {'success': True, 'action': 'move', 'direction': direction, 'position': {'x': new_x, 'y': new_y}}
    
    def _do_attack(self, target_pos: Tuple[int, int] = None) -> dict:
        """Attack adjacent monster"""
        player = self.world.player
        target = None
        
        # Find target
        if target_pos:
            target = self.world.get_entity_at(target_pos[0], target_pos[1])
        else:
            # Auto-target adjacent
            for dx, dy in [(0,-1), (1,0), (0,1), (-1,0)]:
                entity = self.world.get_entity_at(player.x + dx, player.y + dy)
                if entity and entity != player and entity.stats.is_alive():
                    target = entity
                    break
        
        if not target:
            return {'success': False, 'error': 'No adjacent enemy'}
        
        # Attack
        result = player.attack(target)
        
        if result['success']:
            self.msg(f"Hit {target.name} for {result['damage']} damage!")
            
            xp_gained = 0
            leveled_up = False
            
            if not result['target_alive']:
                self.msg(f"{target.name} defeated!")
                xp_gained = 25
                lvl_result = player.gain_xp(xp_gained)
                leveled_up = lvl_result['leveled_up']
                if leveled_up:
                    self.msg(f"LEVEL UP! Now level {lvl_result['new_level']}!")
            
            self.turn += 1
            self._monster_turns()
            
            return {
                'success': True,
                'action': 'attack',
                'target': target.name,
                'damage': result['damage'],
                'target_hp': target.stats.current_health,
                'target_alive': result['target_alive'],
                'xp_gained': xp_gained,
                'leveled_up': leveled_up,
            }
        
        return {'success': False, 'error': 'Attack failed'}
    
    def _do_pickup(self) -> dict:
        """Pick up items at player position"""
        player = self.world.player
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground or not self.world.items_on_ground[pos]:
            return {'success': False, 'error': 'Nothing here'}
        
        items = self.world.items_on_ground[pos]
        picked = []
        
        for item in items[:]:
            if player.inventory.add_object(item):
                items.remove(item)
                picked.append(item['name'])
                self.msg(f"Picked up: {item['name']}")
        
        if not items:
            del self.world.items_on_ground[pos]
        
        return {'success': True, 'action': 'pickup', 'picked': picked}
    
    # =========================================================================
    # SPELLS
    # =========================================================================
    
    def cast_spell(self, spell_name: str, target_pos: Tuple[int, int] = None) -> dict:
        """Cast a spell"""
        player = self.world.player
        
        if spell_name not in self.spell_defs:
            return {'success': False, 'error': f'Unknown spell: {spell_name}', 'available': list(self.spell_defs.keys())}
        
        spell = self.spell_defs[spell_name]
        cost = spell['composition']
        
        # Check essence
        if not player.inventory.has_essence(cost):
            return {'success': False, 'error': 'Not enough essence', 'cost': cost, 'have': dict(player.inventory.essences)}
        
        # Find target for damage spells
        target = None
        effect = spell['effect']
        
        if effect['type'] == 'damage':
            if target_pos:
                target = self.world.get_entity_at(target_pos[0], target_pos[1])
            else:
                # Auto-target nearest visible monster
                visible = self.world.get_visible_monsters(radius=8)
                if visible:
                    visible.sort(key=lambda m: ((m.x - player.x)**2 + (m.y - player.y)**2))
                    target = visible[0]
            
            if not target:
                return {'success': False, 'error': 'No target in range'}
        
        # Pay essence cost
        for elem, amt in cost.items():
            player.inventory.remove_essence(elem, amt)
        
        result = {
            'success': True,
            'action': 'cast',
            'spell': spell_name,
            'cost': cost,
        }
        
        # Apply effect
        if effect['type'] == 'damage' and target:
            damage = effect['power'] + player.stats.magic_power // 2
            target.stats.take_damage(damage)
            self.msg(f"{spell_name.upper()} hits {target.name} for {damage}!")
            
            result['target'] = target.name
            result['damage'] = damage
            result['target_alive'] = target.stats.is_alive()
            
            if not target.stats.is_alive():
                self.msg(f"{target.name} destroyed!")
                xp = 30
                lvl = player.gain_xp(xp)
                result['xp_gained'] = xp
                result['leveled_up'] = lvl['leveled_up']
        
        elif effect['type'] == 'heal':
            amount = effect['amount']
            player.stats.heal(amount)
            self.msg(f"Healed {amount} HP!")
            result['healed'] = amount
            result['hp'] = player.stats.current_health
        
        elif effect['type'] == 'buff':
            # Simplified buff
            self.msg(f"Gained {effect['stat']} buff!")
            result['buff'] = effect['stat']
        
        self.turn += 1
        self._monster_turns()
        
        result['state'] = self.get_state()
        return result
    
    # =========================================================================
    # INVENTORY
    # =========================================================================
    
    def get_inventory(self) -> dict:
        """Get player inventory"""
        player = self.world.player
        inv = player.inventory
        
        items = []
        for i, obj in enumerate(inv.objects):
            items.append({
                'id': i,
                'name': obj['name'],
                'type': obj.get('type', 'misc'),
                'weight': obj.get('weight', 1),
            })
        
        return {
            'items': items,
            'count': len(items),
            'max_objects': inv.max_objects,
            'weight': sum(o.get('weight', 0) for o in inv.objects),
            'max_weight': inv.max_weight,
            'essences': {k: int(v) for k, v in inv.essences.items()},
            'max_essence': int(inv.max_essence),
            'spells': list(inv.grimoire),
        }
    
    def use_item(self, item_id: int) -> dict:
        """Use an inventory item"""
        player = self.world.player
        inv = player.inventory
        
        if item_id < 0 or item_id >= len(inv.objects):
            return {'success': False, 'error': 'Invalid item ID'}
        
        item = inv.objects[item_id]
        item_type = item.get('type', 'misc')
        
        result = {'success': False, 'action': 'use', 'item': item['name']}
        
        if item_type == 'food':
            heal = 20
            player.stats.heal(heal)
            inv.objects.pop(item_id)
            self.msg(f"Ate {item['name']}, healed {heal} HP.")
            result = {'success': True, 'action': 'use', 'item': item['name'], 'healed': heal}
        
        elif item_type == 'gems':
            import random
            elem = random.choice(['fire', 'water', 'earth', 'air'])
            amt = 15
            added = inv.add_essence(elem, amt)
            inv.objects.pop(item_id)
            self.msg(f"Gem gave +{int(added)} {elem} essence.")
            result = {'success': True, 'action': 'use', 'item': item['name'], 'essence': {elem: int(added)}}
        
        elif item_type == 'liquids':
            player.stats.restore_stamina(25)
            inv.objects.pop(item_id)
            self.msg(f"Drank {item['name']}, restored stamina.")
            result = {'success': True, 'action': 'use', 'item': item['name'], 'stamina': 25}
        
        else:
            result = {'success': False, 'error': f"Can't use {item['name']}"}
        
        result['state'] = self.get_state()
        return result
    
    def drop_item(self, item_id: int) -> dict:
        """Drop an inventory item"""
        player = self.world.player
        inv = player.inventory
        
        if item_id < 0 or item_id >= len(inv.objects):
            return {'success': False, 'error': 'Invalid item ID'}
        
        item = inv.objects.pop(item_id)
        pos = (player.x, player.y)
        
        if pos not in self.world.items_on_ground:
            self.world.items_on_ground[pos] = []
        self.world.items_on_ground[pos].append(item)
        
        self.msg(f"Dropped {item['name']}.")
        return {'success': True, 'action': 'drop', 'item': item['name'], 'state': self.get_state()}
    
    def dissolve_item(self, item_id: int, solvent_id: int) -> dict:
        """Dissolve item with solvent to extract essences"""
        player = self.world.player
        inv = player.inventory
        
        if item_id < 0 or item_id >= len(inv.objects):
            return {'success': False, 'error': 'Invalid item ID'}
        if solvent_id < 0 or solvent_id >= len(inv.objects):
            return {'success': False, 'error': 'Invalid solvent ID'}
        if item_id == solvent_id:
            return {'success': False, 'error': 'Cannot dissolve item with itself'}
        
        item = inv.objects[item_id]
        solvent = inv.objects[solvent_id]
        
        if solvent.get('type') != 'solvent':
            return {'success': False, 'error': f"{solvent['name']} is not a solvent"}
        
        # Get solvent data
        solvent_key = solvent.get('solvent_type', 'alkahest')
        solvent_data = SOLVENTS.get(solvent_key, SOLVENTS['alkahest'])
        
        # Get item essence values
        item_type = item.get('type', 'default')
        base_essence = MATERIAL_ESSENCES.get(item_type, MATERIAL_ESSENCES['default'])
        
        # Extract essences
        extracted = {}
        for elem in solvent_data['extracts']:
            amount = base_essence.get(elem, 10) * solvent_data['strength']
            added = inv.add_essence(elem, amount)
            if added > 0:
                extracted[elem] = int(added)
        
        # Remove items (higher index first to preserve indices)
        if item_id > solvent_id:
            inv.objects.pop(item_id)
            inv.objects.pop(solvent_id)
        else:
            inv.objects.pop(solvent_id)
            inv.objects.pop(item_id)
        
        self.msg(f"Dissolved {item['name']} with {solvent['name']}!")
        for elem, amt in extracted.items():
            self.msg(f"+{amt} {elem}")
        
        return {
            'success': True,
            'action': 'dissolve',
            'item': item['name'],
            'solvent': solvent['name'],
            'extracted': extracted,
            'state': self.get_state()
        }
    
    # =========================================================================
    # MONSTER AI
    # =========================================================================
    
    def _monster_turns(self):
        """Process monster AI"""
        player = self.world.player
        
        for monster in self.world.monsters:
            if not monster.stats.is_alive():
                continue
            
            # Check if monster can see player
            if not self.world.can_see(monster, player, max_range=8):
                continue
            
            dist = monster.distance_to(player)
            
            if dist <= 1.5:
                result = monster.attack(player)
                if result['success']:
                    self.msg(f"{monster.name} hits you for {result['damage']}!")
            elif dist < 8:
                # Move toward player
                dx = 1 if player.x > monster.x else -1 if player.x < monster.x else 0
                dy = 1 if player.y > monster.y else -1 if player.y < monster.y else 0
                new_x, new_y = monster.x + dx, monster.y + dy
                if self.world.is_walkable(new_x, new_y) and not self.world.get_entity_at(new_x, new_y):
                    monster.x, monster.y = new_x, new_y


# =============================================================================
# HTTP SERVER
# =============================================================================

# Global game session
game_session: Optional[GameSession] = None


class GameAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for game API"""
    
    def _send_json(self, data: dict, status: int = 200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def _get_body(self) -> dict:
        """Get JSON body from request"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            body = self.rfile.read(content_length)
            return json.loads(body)
        return {}
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        global game_session
        
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/state':
            self._send_json(game_session.get_state())
        
        elif path == '/visible':
            radius = int(query.get('radius', [10])[0])
            self._send_json({
                'visible': game_session.get_visible(radius),
                'formatted': game_session.get_visible_formatted(radius),
            })
        
        elif path == '/inventory':
            self._send_json(game_session.get_inventory())
        
        elif path == '/spells':
            self._send_json({'spells': game_session.spell_defs})
        
        elif path == '/map':
            self._send_json({'map': game_session.world.render()})
        
        elif path == '/help':
            self._send_json({
                'endpoints': {
                    'GET /state': 'Get full game state',
                    'GET /visible': 'Get visible entities/items',
                    'GET /inventory': 'Get player inventory',
                    'GET /spells': 'Get available spells',
                    'GET /map': 'Get ASCII map',
                    'POST /action': 'Perform action {action: "n/s/e/w/attack/wait/pickup"}',
                    'POST /cast/<spell>': 'Cast spell',
                    'POST /use/<id>': 'Use inventory item',
                    'POST /drop/<id>': 'Drop inventory item',
                    'POST /dissolve': 'Dissolve item {item_id, solvent_id}',
                    'POST /reset': 'Reset game {seed?: number}',
                }
            })
        
        else:
            self._send_json({'error': 'Not found', 'path': path}, 404)
    
    def do_POST(self):
        """Handle POST requests"""
        global game_session
        
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._get_body()
        
        if path == '/action':
            action = body.get('action', '')
            result = game_session.do_action(action, **body)
            self._send_json(result)
        
        elif path.startswith('/cast/'):
            spell = path[6:]  # Remove '/cast/'
            target = body.get('target')
            result = game_session.cast_spell(spell, target)
            self._send_json(result)
        
        elif path.startswith('/use/'):
            item_id = int(path[5:])
            result = game_session.use_item(item_id)
            self._send_json(result)
        
        elif path.startswith('/drop/'):
            item_id = int(path[6:])
            result = game_session.drop_item(item_id)
            self._send_json(result)
        
        elif path == '/dissolve':
            item_id = body.get('item_id')
            solvent_id = body.get('solvent_id')
            result = game_session.dissolve_item(item_id, solvent_id)
            self._send_json(result)
        
        elif path == '/pickup':
            result = game_session.do_action('pickup')
            self._send_json(result)
        
        elif path == '/reset':
            seed = body.get('seed')
            game_session.reset(seed)
            self._send_json({'success': True, 'state': game_session.get_state()})
        
        else:
            self._send_json({'error': 'Not found', 'path': path}, 404)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(host: str = 'localhost', port: int = 5000):
    """Run the API server"""
    global game_session
    game_session = GameSession(seed=42)
    
    server = HTTPServer((host, port), GameAPIHandler)
    print(f"Elemental RPG API running at http://{host}:{port}")
    print("Endpoints: GET /help for list")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


# =============================================================================
# CLIENT HELPER (for game_pygame)
# =============================================================================

class GameAPIClient:
    """
    Client for connecting to the Game API.
    Use this in game_pygame to interface with the game.
    """
    
    def __init__(self, base_url: str = 'http://localhost:5000'):
        self.base_url = base_url
        self._session = None  # For local mode
    
    def use_local(self, session: GameSession):
        """Use local session instead of HTTP"""
        self._session = session
    
    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """Make HTTP request or use local session"""
        if self._session:
            # Local mode
            if method == 'GET':
                if path == '/state':
                    return self._session.get_state()
                elif path == '/visible':
                    return {'visible': self._session.get_visible(), 'formatted': self._session.get_visible_formatted()}
                elif path == '/inventory':
                    return self._session.get_inventory()
            elif method == 'POST':
                if path == '/action':
                    action = data.get('action', '')
                    return self._session.do_action(action)
                elif path.startswith('/cast/'):
                    return self._session.cast_spell(path[6:], data.get('target'))
                elif path.startswith('/use/'):
                    return self._session.use_item(int(path[5:]))
                elif path.startswith('/drop/'):
                    return self._session.drop_item(int(path[6:]))
                elif path == '/dissolve':
                    return self._session.dissolve_item(data['item_id'], data['solvent_id'])
                elif path == '/pickup':
                    return self._session.do_action('pickup')
                elif path == '/reset':
                    self._session.reset(data.get('seed'))
                    return {'success': True, 'state': self._session.get_state()}
            return {'error': 'Unknown path'}
        
        # HTTP mode
        import urllib.request
        url = self.base_url + path
        
        if method == 'GET':
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read())
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data or {}).encode(),
                headers={'Content-Type': 'application/json'},
                method=method
            )
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())
    
    # Convenience methods
    def get_state(self) -> dict:
        return self._request('GET', '/state')
    
    def get_visible(self) -> dict:
        return self._request('GET', '/visible')
    
    def get_inventory(self) -> dict:
        return self._request('GET', '/inventory')
    
    def move(self, direction: str) -> dict:
        return self._request('POST', '/action', {'action': direction})
    
    def attack(self, target: Tuple[int, int] = None) -> dict:
        return self._request('POST', '/action', {'action': 'attack', 'target': target})
    
    def wait(self) -> dict:
        return self._request('POST', '/action', {'action': 'wait'})
    
    def pickup(self) -> dict:
        return self._request('POST', '/pickup')
    
    def cast(self, spell: str, target: Tuple[int, int] = None) -> dict:
        return self._request('POST', f'/cast/{spell}', {'target': target})
    
    def use(self, item_id: int) -> dict:
        return self._request('POST', f'/use/{item_id}')
    
    def drop(self, item_id: int) -> dict:
        return self._request('POST', f'/drop/{item_id}')
    
    def dissolve(self, item_id: int, solvent_id: int) -> dict:
        return self._request('POST', '/dissolve', {'item_id': item_id, 'solvent_id': solvent_id})
    
    def reset(self, seed: int = None) -> dict:
        return self._request('POST', '/reset', {'seed': seed})


if __name__ == '__main__':
    run_server()
