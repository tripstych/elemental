"""Test play script for LLM interface - Run this to test the game"""
import sys
import os

# Ensure output is flushed
sys.stdout.reconfigure(line_buffering=True)

try:
    from game_llm import LLMGameInterface
    import json
    
    print('=== ELEMENTAL RPG TEST PLAY ===')
    print('Initializing game...')
    
    game = LLMGameInterface(seed=42)
    
    state = game.get_state()
    print(f'\nSTART: HP={state["player"]["hp"]}, Pos={state["player"]["position"]}')
    print(f'Essences: {state["player"]["essences"]}')
    print(f'Nearby monsters: {len(state["nearby_monsters"])}')
    for m in state['nearby_monsters']:
        print(f'  - {m["name"]} ({m["hp"]}) {m["direction"]} dist={m["distance"]}')
    
    commands = ['look', 'n', 'e', 'pickup', 'inventory', 'w', 's', 'attack', 'attack', 'attack', 'cast fireball', 'stats']
    
    print('\n--- PLAYING TURNS ---\n')
    
    for cmd in commands:
        if not game.running:
            break
        state = game.process(cmd)
        print(f'> {cmd}')
        for msg in state['messages']:
            print(f'  {msg}')
        print(f'  [HP={state["player"]["hp"]}, Level={state["player"]["level"]}, XP={state["player"]["xp"]}]')
        print()
    
    print('=== FINAL STATE ===')
    print(f'Level: {state["player"]["level"]}')
    print(f'HP: {state["player"]["hp"]}')
    print(f'Essences: {state["player"]["essences"]} (max: {state["player"]["max_essence"]})')
    print(f'Inventory: {state["inventory"]}')
    print(f'Nearby monsters: {len(state["nearby_monsters"])}')
    print('\nTest complete!')
    
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
