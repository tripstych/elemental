import json
import requests
import os
import time

# Ollama API configuration
OLLAMA_API_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAII5xHytqVnwiB1Jkco42Nzt/bjKS5z8+t+vSP4Q8CNiM"
OLLAMA_MODEL = "qwen3-coder:480b-cloud"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Cache file to avoid losing progress
CACHE_FILE = "game_object_weights_cache.json"
OUTPUT_FILE = "game_object_weights.json"

def load_cache():
    """Load cached weight results"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save cache to file"""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def query_ollama_weight(item_name, item_type, definition, material, size):
    """Query Ollama for estimated weight of an item"""
    prompt = f"""Estimate the weight in kilograms for this game item. Return ONLY a number (decimal allowed).

Item: {item_name}
Type: {item_type}
Material: {material}
Size: {size}
Description: {definition}

Respond with just the weight number in kg, nothing else. For example: 2.5"""

    try:
        response = requests.post(
            OLLAMA_URL,
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            weight_str = result.get("response", "").strip()
            # Extract number from response
            try:
                # Handle responses like "2.5 kg" or just "2.5"
                weight_str = weight_str.replace("kg", "").replace("KG", "").strip()
                weight = float(weight_str)
                return weight
            except ValueError:
                print(f"  Could not parse weight: {weight_str}")
                return None
        else:
            print(f"  API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None

def main():
    # Load game objects
    with open("game_objects.json", "r") as f:
        data = json.load(f)

    # Filter to relevant types
    types_to_process = ['weapons', 'tools', 'gems', 'food']
    items_to_process = [obj for obj in data if obj.get("type") in types_to_process]

    print(f"Found {len(items_to_process)} items to process")

    # Load existing cache
    cache = load_cache()
    print(f"Loaded {len(cache)} cached weights")

    # Process each item
    for i, obj in enumerate(items_to_process):
        synset = obj.get("synset", obj.get("name"))

        # Skip if already cached
        if synset in cache:
            print(f"[{i+1}/{len(items_to_process)}] {obj['name']} - cached: {cache[synset]} kg")
            continue

        print(f"[{i+1}/{len(items_to_process)}] Querying: {obj['name']}...")

        weight = query_ollama_weight(
            item_name=obj.get("name", "unknown"),
            item_type=obj.get("type", "misc"),
            definition=obj.get("definition", ""),
            material=obj.get("material", "unknown"),
            size=obj.get("size", "medium")
        )

        if weight is not None:
            cache[synset] = weight
            print(f"  -> {weight} kg")
            # Save cache after each successful query
            save_cache(cache)
        else:
            print(f"  -> Failed to get weight")

        # Rate limiting
        time.sleep(0.5)

    # Create final output with updated weights
    output_data = []
    for obj in items_to_process:
        synset = obj.get("synset", obj.get("name"))
        updated_obj = obj.copy()
        if synset in cache:
            updated_obj["weight"] = cache[synset]
        output_data.append(updated_obj)

    # Save final output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDone! Saved {len(output_data)} items to {OUTPUT_FILE}")
    print(f"Successfully estimated weights for {len(cache)} items")

if __name__ == "__main__":
    main()