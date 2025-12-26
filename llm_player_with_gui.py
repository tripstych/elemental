"""
LLM Player with GUI - Shows LLM playing the game in real-time Pygame interface

This runs the game with Pygame GUI while an LLM makes decisions.
You can watch the LLM explore, fight, and manage inventory visually.

Usage:
    python llm_player_with_gui.py [--api-key YOUR_KEY] [--provider openai] [--model qwen3-coder]
"""

import sys
import os
import json
import argparse
import time
import re
from typing import Optional, Tuple

# Add path for imports
sys.path.insert(0, os.path.dirname(__file__))

from game_api import GameSession, GameAPIClient
import pygame

# Import Pygame game class
from game_pygame import ElementalGame, COLORS, SCREEN_WIDTH, SCREEN_HEIGHT

# Load the prompt
PROMPT_FILE = os.path.join(os.path.dirname(__file__), 'llm_player_prompt.md')


def load_system_prompt() -> str:
    """Load the LLM player prompt"""
    try:
        with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback prompt if file doesn't exist
        return """
You are playing Elemental RPG, a dungeon crawler with combat, spells, and alchemy.
You interact with the game via a REST API.

Your goal: Explore the dungeon, defeat monsters, collect items, and level up.

Available actions:
- Move: n, s, e, w (north, south, east, west)
- Attack: attack (adjacent monsters)
- Wait: wait (skip turn)
- Pickup: pickup (items at your position)
- Spells: fireball, heal
- Use: use <item_id>
- Drop: drop <item_id>
- Dissolve: dissolve item with solvent for essences

Position format: n3e2 means 3 north, 2 east from you
Adjacent means distance ≤ 1.5 (can attack)

Respond with:
OBSERVATION: <what you see>
REASONING: <why you're taking this action>
ACTION: <the action to take>
"""


def format_state_for_llm(state: dict) -> str:
    """Format game state as a message for the LLM"""
    player = state['player']
    visible = state.get('visible', {})
    
    lines = [
        f"=== TURN {state['turn']} ===",
        f"",
        f"PLAYER STATUS:",
        f"  Position: ({player['position']['x']}, {player['position']['y']})",
        f"  HP: {player['hp']}/{player['max_hp']}",
        f"  Level: {player['level']} | XP: {player['xp']}/{player['xp_next']}",
        f"  Essences: F:{player['essences']['fire']} W:{player['essences']['water']} E:{player['essences']['earth']} A:{player['essences']['air']} (max: {player['max_essence']})",
        f"",
        f"SURROUNDINGS:",
    ]
    
    for direction, what in state.get('surroundings', {}).items():
        lines.append(f"  {direction}: {what}")
    
    lines.append("")
    lines.append("VISIBLE MONSTERS:")
    if visible.get('monsters'):
        for m in visible['monsters']:
            adj = " [ADJACENT]" if m.get('adjacent') else ""
            formatted = f"{m['name']}:{m['pos']}"
            lines.append(f"  {formatted} (HP: {m['hp']}/{m['max_hp']}){adj}")
    else:
        lines.append("  None")
    
    lines.append("")
    lines.append("VISIBLE ITEMS:")
    if visible.get('items'):
        for item in visible['items']:
            formatted = f"{item['name']}:{item['pos']}"
            lines.append(f"  {formatted} ({item['type']})")
    else:
        lines.append("  None")
    
    if state.get('messages'):
        lines.append("")
        lines.append("MESSAGES:")
        for msg in state['messages']:
            lines.append(f"  > {msg}")
    
    lines.append("")
    lines.append("What is your next action? Respond with OBSERVATION, REASONING, and ACTION.")
    
    return "\n".join(lines)


def parse_llm_action(response: str) -> Tuple[str, dict]:
    """
    Parse LLM response to extract the action.
    Returns (endpoint, body) tuple.
    """
    response_lower = response.lower()
    
    # Look for explicit ACTION: line
    action_match = re.search(r'action:\s*(.+)', response_lower)
    if action_match:
        action_line = action_match.group(1).strip()
    else:
        # Use the whole response
        action_line = response_lower
    
    # Parse common action patterns
    
    # Movement
    if 'move north' in action_line or '"n"' in action_line or "'n'" in action_line or action_line.strip() == 'n':
        return '/action', {'action': 'n'}
    if 'move south' in action_line or '"s"' in action_line or "'s'" in action_line or action_line.strip() == 's':
        return '/action', {'action': 's'}
    if 'move east' in action_line or '"e"' in action_line or "'e'" in action_line or action_line.strip() == 'e':
        return '/action', {'action': 'e'}
    if 'move west' in action_line or '"w"' in action_line or "'w'" in action_line or action_line.strip() == 'w':
        return '/action', {'action': 'w'}
    
    # Attack
    if 'attack' in action_line:
        return '/action', {'action': 'attack'}
    
    # Wait
    if 'wait' in action_line:
        return '/action', {'action': 'wait'}
    
    # Pickup
    if 'pickup' in action_line or 'pick up' in action_line:
        return '/pickup', {}
    
    # Spells
    if 'fireball' in action_line:
        return '/cast/fireball', {}
    if 'heal' in action_line:
        return '/cast/heal', {}
    
    # Dissolve
    dissolve_match = re.search(r'dissolve.*item[_\s]*(?:id)?[:\s]*(\d+).*solvent[_\s]*(?:id)?[:\s]*(\d+)', action_line)
    if dissolve_match:
        return '/dissolve', {'item_id': int(dissolve_match.group(1)), 'solvent_id': int(dissolve_match.group(2))}
    if 'dissolve' in action_line:
        # Default: first non-solvent with first solvent
        return '/dissolve', {'item_id': 1, 'solvent_id': 0}
    
    # Use item
    use_match = re.search(r'use[/\s]+(\d+)', action_line)
    if use_match:
        return f'/use/{use_match.group(1)}', {}
    
    # Default: wait
    return '/action', {'action': 'wait'}


class DummyLLM:
    """Simple rule-based 'LLM' for testing without API"""
    
    def __call__(self, system: str, user: str) -> str:
        # Parse state from user message
        lines = user.split('\n')
        
        hp = 100
        adjacent_monster = False
        items_here = False
        fire_essence = 100
        water_essence = 100
        
        for line in lines:
            if 'HP:' in line:
                match = re.search(r'HP:\s*(\d+)', line)
                if match:
                    hp = int(match.group(1))
            if '[ADJACENT]' in line:
                adjacent_monster = True
            if 'here' in line.lower() and 'item' in line.lower():
                items_here = True
            if 'F:' in line:
                match = re.search(r'F:(\d+)', line)
                if match:
                    fire_essence = int(match.group(1))
            if 'W:' in line:
                match = re.search(r'W:(\d+)', line)
                if match:
                    water_essence = int(match.group(1))
        
        # Decision logic
        if hp < 40 and water_essence >= 30:
            return "OBSERVATION: HP is low\nREASONING: Need to heal\nACTION: POST /cast/heal"
        
        if adjacent_monster:
            return "OBSERVATION: Monster adjacent\nREASONING: Attack it\nACTION: POST /action {\"action\": \"attack\"}"
        
        if items_here:
            return "OBSERVATION: Items here\nREASONING: Pick them up\nACTION: POST /pickup"
        
        # Random movement
        import random
        direction = random.choice(['n', 's', 'e', 'w'])
        return f"OBSERVATION: Exploring\nREASONING: Move to find enemies\nACTION: POST /action {{\"action\": \"{direction}\"}}"


class OpenAILLM:
    """OpenAI API wrapper (also works with Ollama)"""
    
    def __init__(self, api_key: str = "dummy", model: str = "gpt-4", base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
    
    def __call__(self, system: str, user: str) -> str:
        import urllib.request
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Add authorization for real OpenAI
        if "api.openai.com" in self.base_url:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(data).encode(),
            headers=headers
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result['choices'][0]['message']['content']


class LLMGameWithGUI(ElementalGame):
    """Pygame game with LLM player overlay"""
    
    def __init__(self, llm, max_turns: int = 100, delay: float = 1.0):
        # Initialize Pygame game normally
        super().__init__()
        
        # LLM settings
        self.llm = llm
        self.max_turns = max_turns
        self.delay = delay
        self.llm_turn = 0
        self.llm_active = True
        self.llm_response = ""
        self.llm_thinking = False
        self.llm_action = ""
        
        # Load prompt
        self.system_prompt = load_system_prompt()
        
        # Create API client for LLM
        self.session = GameSession(seed=self.world.seed)
        self.api_client = GameAPIClient()
        self.api_client.use_local(self.session)
        
        # Override the world with the session's world
        self.world = self.session.world
        self.player = self.world.player
        
        # Add LLM info to sidebar
        self.show_llm_info = True
    
    def get_llm_decision(self) -> Tuple[str, dict]:
        """Get LLM decision for current state"""
        state = self.api_client.get_state()
        state_text = format_state_for_llm(state)
        
        try:
            response = self.llm(self.system_prompt, state_text)
            self.llm_response = response
            endpoint, body = parse_llm_action(response)
            self.llm_action = f"{endpoint} {body if body else ''}"
            return endpoint, body
        except Exception as e:
            print(f"[LLM Error: {e}]")
            self.llm_response = f"Error: {e}"
            return '/action', {'action': 'wait'}
    
    def execute_llm_action(self, endpoint: str, body: dict):
        """Execute LLM action and sync with Pygame world"""
        # Execute via API
        result = self.api_client._request('POST', endpoint, body)
        
        if result.get('success'):
            # Add message about action
            if endpoint == '/action':
                action = body.get('action', 'wait')
                if action in ['n', 's', 'e', 'w']:
                    self.add_message(f"LLM moves {action.upper()}")
                elif action == 'attack':
                    self.add_message("LLM attacks!")
                elif action == 'wait':
                    self.add_message("LLM waits...")
            elif endpoint == '/pickup':
                self.add_message("LLM picks up items")
            elif endpoint == '/cast/fireball':
                self.add_message("LLM casts fireball!")
            elif endpoint == '/cast/heal':
                self.add_message("LLM casts heal!")
            elif endpoint == '/dissolve':
                self.add_message("LLM dissolves items")
            
            # Show details if any
            if result.get('details'):
                self.add_message(str(result.get('details')))
        else:
            self.add_message(f"LLM action failed: {result.get('error', 'unknown')}")
        
        # Sync Pygame world with session world
        self.world = self.session.world
        self.player = self.world.player
        
        # Increment turn
        self.llm_turn += 1
    
    def handle_events(self):
        """Handle pygame events - allow manual override"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                # Toggle LLM control with TAB
                if event.key == pygame.K_TAB:
                    self.llm_active = not self.llm_active
                    self.add_message(f"LLM control: {'ON' if self.llm_active else 'OFF'}")
                
                # Toggle LLM info display with I
                elif event.key == pygame.K_i:
                    self.show_llm_info = not self.show_llm_info
                
                # Manual control when LLM is off
                elif not self.llm_active:
                    self.handle_keydown(event)
    
    def run(self):
        """Main game loop with LLM player"""
        last_llm_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Handle events
            self.handle_events()
            
            # LLM turn (with delay)
            if self.llm_active and current_time - last_llm_time >= self.delay:
                if self.llm_turn < self.max_turns and self.player.stats.is_alive():
                    self.llm_thinking = True
                    
                    # Get and execute LLM action
                    endpoint, body = self.get_llm_decision()
                    self.execute_llm_action(endpoint, body)
                    
                    self.llm_thinking = False
                    last_llm_time = current_time
                else:
                    if self.llm_turn >= self.max_turns:
                        self.add_message("LLM reached max turns")
                    self.llm_active = False
            
            # Render
            self.render()
            self.clock.tick(60)
        
        # Save log
        self.save_log()
        print(f"Game log saved to {self.log_file}")
        pygame.quit()
    
    def render_sidebar(self):
        """Render sidebar with LLM info"""
        super().render_sidebar()
        
        if not self.show_llm_info:
            return
        
        # LLM info section
        sidebar_x = self.game_area_width + 20
        y = 750
        
        # LLM status
        status_color = COLORS['green'] if self.llm_active else COLORS['red']
        status_text = "ACTIVE" if self.llm_active else "PAUSED"
        if self.llm_thinking:
            status_text = "THINKING..."
            status_color = COLORS['yellow']
        
        llm_label = self.font_small.render(f"LLM: {status_text}", True, status_color)
        self.screen.blit(llm_label, (sidebar_x + 10, y))
        y += 20
        
        # Turn counter
        turn_text = self.font_small.render(f"Turn: {self.llm_turn}/{self.max_turns}", True, COLORS['white'])
        self.screen.blit(turn_text, (sidebar_x + 10, y))
        y += 20
        
        # Last action (if any)
        if self.llm_action:
            action_text = self.font_small.render(f"Action: {self.llm_action}", True, COLORS['light_gray'])
            self.screen.blit(action_text, (sidebar_x + 10, y))
            y += 20
        
        # LLM response (truncated)
        if self.llm_response:
            response_lines = self.llm_response.split('\n')
            for line in response_lines:
                if len(line) > 30:
                    line = line
                resp_text = self.font_small.render(line, True, COLORS['gray'])
                self.screen.blit(resp_text, (sidebar_x + 10, y))
                y += 16
        
        # Controls hint
        y += 10
        hint_text = self.font_small.render("TAB=toggle LLM, I=toggle info", True, COLORS['gray'])
        self.screen.blit(hint_text, (sidebar_x + 10, y))


def main():
    parser = argparse.ArgumentParser(description='Run Elemental RPG with LLM player and GUI')
    parser.add_argument('--api-key', help='API key for LLM service')
    parser.add_argument('--provider', choices=['openai', 'anthropic', 'dummy'], default='dummy',
                        help='LLM provider (default: dummy for testing)')
    parser.add_argument('--model', help='Model name')
    parser.add_argument('--base-url', help='Base URL for API (e.g., http://localhost:11434/v1 for Ollama)')
    parser.add_argument('--max-turns', type=int, default=100, help='Maximum turns for LLM')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between LLM turns (seconds)')
    
    args = parser.parse_args()
    
    # Select LLM
    if args.provider == 'openai':
        api_key = args.api_key or os.environ.get('OPENAI_API_KEY') or "dummy"
        model = args.model or 'gpt-4'
        base_url = args.base_url or ("https://api.openai.com/v1" if api_key != "dummy" else None)
        
        if args.base_url:
            print(f"Using OpenAI-compatible API at {args.base_url}")
        elif api_key == "dummy":
            print("Using OpenAI format (no auth)")
        else:
            print(f"Using OpenAI {model}")
        
        llm = OpenAILLM(api_key, model, base_url)
    
    elif args.provider == 'anthropic':
        api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("Error: Anthropic API key required")
            sys.exit(1)
        model = args.model or 'claude-3-sonnet-20240229'
        llm = AnthropicLLM(api_key, model)
        print(f"Using Anthropic {model}")
    
    else:
        llm = DummyLLM()
        print("Using dummy LLM (rule-based)")
    
    print()
    print("Starting game with LLM player...")
    print("Press TAB to toggle LLM control")
    print("Press I to toggle LLM info display")
    print()
    
    # Run game
    game = LLMGameWithGUI(llm, max_turns=args.max_turns, delay=args.delay)
    game.run()


if __name__ == '__main__':
    main()
