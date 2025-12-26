#!/usr/bin/env python3
"""
Test script to analyze transmutation costs across weight ranges
"""

import json
import os

# Load game objects
def load_game_objects():
    filepath = os.path.join(os.path.dirname(__file__), 'game_objects.json')
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_transmute_cost(source_weight, target_weight, target_composition=None):
    """Calculate transmutation cost based on weight difference"""
    # Check weight constraint
    if target_weight > source_weight * 2:
        return None, f"Target too heavy: {target_weight}kg vs {source_weight}kg source"
    
    # Calculate essence requirements based on weight difference
    weight_ratio = target_weight / max(source_weight, 0.1)
    
    # Base essence cost scales with weight difference
    base_cost = {
        'fire': 5 * weight_ratio,
        'water': 5 * weight_ratio, 
        'earth': 5 * weight_ratio,
        'air': 5 * weight_ratio
    }
    
    # Adjust for target's actual composition
    if target_composition:
        for element, amount in target_composition.items():
            if element in base_cost:
                base_cost[element] = amount * weight_ratio
    
    return base_cost, None

def analyze_weight_ranges():
    """Analyze costs across different weight ranges"""
    game_objects = load_game_objects()
    
    # Filter objects with weights
    objects_with_weights = [(obj['name'], obj.get('weight', 0), obj.get('synset', '')) 
                          for obj in game_objects if obj.get('weight', 0) > 0]
    
    # Sort by weight
    objects_with_weights.sort(key=lambda x: x[1])
    
    print("=== WEIGHT RANGE ANALYSIS ===")
    print(f"Total objects with weights: {len(objects_with_weights)}")
    print(f"Lightest: {objects_with_weights[0][0]} ({objects_with_weights[0][1]}kg)")
    print(f"Heaviest: {objects_with_weights[-1][0]} ({objects_with_weights[-1][1]}kg)")
    print()
    
    # Test weight ranges
    test_weights = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    
    print("=== TRANSFORMATION COSTS BY WEIGHT RATIO ===")
    print("Source -> Target (Weight Ratio) | Fire | Water | Earth | Air | Total")
    print("-" * 70)
    
    costs_data = []
    
    for source_weight in test_weights:
        for target_weight in test_weights:
            if target_weight <= source_weight * 2:  # Valid transformation
                cost, error = calculate_transmute_cost(source_weight, target_weight)
                if cost:
                    weight_ratio = target_weight / source_weight
                    total_cost = sum(cost.values())
                    costs_data.append((source_weight, target_weight, weight_ratio, cost, total_cost))
                    
                    print(f"{source_weight:4.1f}kg -> {target_weight:4.1f}kg ({weight_ratio:4.1f}x) | "
                          f"{cost['fire']:5.1f} | {cost['water']:5.1f} | {cost['earth']:5.1f} | {cost['air']:5.1f} | {total_cost:6.1f}")
    
    print()
    print("=== STATISTICS ===")
    if costs_data:
        weight_ratios = [c[2] for c in costs_data]
        total_costs = [c[4] for c in costs_data]
        
        print(f"Weight ratio range: {min(weight_ratios):.2f}x - {max(weight_ratios):.2f}x")
        print(f"Total cost range: {min(total_costs):.1f} - {max(total_costs):.1f}")
        print(f"Average cost per unit weight ratio: {sum(total_costs)/len(total_costs):.1f}")
    
    print()
    print("=== SAMPLE REAL OBJECT TRANSFORMATIONS ===")
    print("Source -> Target | Source Weight | Target Weight | Ratio | Total Essence Cost")
    print("-" * 75)
    
    # Test some real object transformations
    sample_objects = objects_with_weights[:10]  # First 10 objects
    for i, (source_name, source_weight, source_synset) in enumerate(sample_objects):
        for j, (target_name, target_weight, target_synset) in enumerate(sample_objects):
            if i != j and target_weight <= source_weight * 2:
                cost, error = calculate_transmute_cost(source_weight, target_weight)
                if cost:
                    weight_ratio = target_weight / source_weight
                    total_cost = sum(cost.values())
                    print(f"{source_name[:12]:12} -> {target_name[:12]:12} | "
                          f"{source_weight:11.2f}kg | {target_weight:12.2f}kg | "
                          f"{weight_ratio:4.1f}x | {total_cost:13.1f}")

if __name__ == "__main__":
    analyze_weight_ranges()
