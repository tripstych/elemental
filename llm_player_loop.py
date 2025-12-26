"""
LLM Player Loop - Runs the game with an LLM making decisions each turn.

This script:
1. Gets game state from the API
2. Sends state to LLM with the player prompt
3. Parses LLM's action
4. Executes action via API
5. Repeats until game ends or max turns

Usage:
    python llm_player_loop.py [--api-key YOUR_KEY] [--max-turns 100]

Supports: OpenAI, Anthropic, or local models via API.
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

# Load the prompt
PROMPT_FILE = os.path.join(os.path.dirname(__file__), 'llm_player_prompt.md')


def load_system_prompt() -> str:
    """Load the LLM player prompt"""
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()


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


class AnthropicLLM:
    """Anthropic API wrapper"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
    
    def __call__(self, system: str, user: str) -> str:
        import urllib.request
        
        data = {
            "model": self.model,
            "max_tokens": 500,
            "system": system,
            "messages": [
                {"role": "user", "content": user}
            ]
        }
        
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result['content'][0]['text']


def run_game_loop(llm, max_turns: int = 100, delay: float = 0.5, verbose: bool = True):
    """
    Main game loop with LLM player.
    """
    # Load prompt
    system_prompt = load_system_prompt()
    
    # Create game session (local mode, no HTTP server needed)
    session = GameSession(seed=42)
    client = GameAPIClient()
    client.use_local(session)
    
    print("=" * 60)
    print("ELEMENTAL RPG - LLM PLAYER")
    print("=" * 60)
    print(f"Max turns: {max_turns}")
    print()
    
    # Initial state
    state = client.get_state()
    
    for turn in range(max_turns):
        # Check if player is dead
        if state['player']['hp'] <= 0:
            print("\n[GAME OVER - Player died]")
            break
        
        # Format state for LLM
        state_text = format_state_for_llm(state)
        
        if verbose:
            print(state_text)
            print()
        
        # Get LLM decision
        try:
            response = llm(system_prompt, state_text)
        except Exception as e:
            print(f"[LLM Error: {e}]")
            print("Check your API key and model name")
            print("OpenAI keys start with 'sk-'")
            print("Anthropic keys start with 'sk-ant-'")
            break
        
        if verbose:
            print("LLM RESPONSE:")
            print(response)
            print()
        
        # Parse action
        endpoint, body = parse_llm_action(response)
        
        print(f"[Turn {turn + 1}] Action: {endpoint} {body if body else ''}")
        
        # Execute action
        result = client._request('POST', endpoint, body)
        
        if result.get('success'):
            print(f"  → Success")
            if result.get('details'):
                print(f"     {result.get('details', {})}")
        else:
            print(f"  → Failed: {result.get('error', 'unknown')}")
        
        # Get new state
        state = result.get('state', client.get_state())
        
        # Show key events
        for msg in state.get('messages', []):
            print(f"  > {msg}")
        
        print()
        
        time.sleep(delay)
    
    print("=" * 60)
    print("GAME SESSION COMPLETE")
    print(f"Final Level: {state['player']['level']}")
    print(f"Final HP: {state['player']['hp']}/{state['player']['max_hp']}")
    print(f"Turns played: {turn + 1}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Run Elemental RPG with LLM player')
    parser.add_argument('--api-key', help='API key for LLM service')
    parser.add_argument('--provider', choices=['openai', 'anthropic', 'dummy'], default='dummy',
                        help='LLM provider (default: dummy for testing)')
    parser.add_argument('--model', help='Model name')
    parser.add_argument('--base-url', help='Base URL for API (e.g., http://localhost:11434/v1 for Ollama)')
    parser.add_argument('--max-turns', type=int, default=50, help='Maximum turns to play')
    parser.add_argument('--delay', type=float, default=0.3, help='Delay between turns (seconds)')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')
    
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
            print("Error: Anthropic API key required (--api-key or ANTHROPIC_API_KEY env)")
            sys.exit(1)
        model = args.model or 'claude-3-sonnet-20240229'
        llm = AnthropicLLM(api_key, model)
        print(f"Using Anthropic {model}")
    
    else:
        llm = DummyLLM()
        print("Using dummy LLM (rule-based, for testing)")
    
    print()
    
    run_game_loop(llm, max_turns=args.max_turns, delay=args.delay, verbose=not args.quiet)


if __name__ == '__main__':
    main()
