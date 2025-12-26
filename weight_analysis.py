#!/usr/bin/env python3
"""
Manual calculation of transmutation costs across weight ranges
"""

def calculate_transmute_cost(source_weight, target_weight):
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
    
    return base_cost, None

def main():
    print("===低谷 WEIGHT RANGE ANAL")
    print("Source -> Target (Weight Ratio) | Fire | Water | Earth | Air | Total")
    print("-" * 70)
    
    # Test key transformations
    test_cases = [
        (0.5, 0.5),  # Potato -> same weight
        (0.5, 1.0),  # Potato -> double weight
        (1.0, 1.0),  # Medium -> same
        (1.0, 2.0),  # Medium -> double
        (2.0, 2.0),  # Sword -> same
        (2.0, 4.0),  # Sword -> double
        (5.0, 5.0),  # Heavy -> same
        (5.0, 10.0), # Heavy -> double
    ]
    
    costs = []
    for source_weight, target_weight in test_cases:
        cost, error = calculate_transmute_cost(source_weight, target_weight)
        if cost:
            weight_ratio = target_weight / source_weight
            total_cost = sum(cost.values())
            costs.append(total_cost)
            print(f"{source_weight:4.1f}kg -> {target_weight:4.1f}kg ({weight_ratio:4.1f}x) | "
                  f"{cost['fire']:5.1f} | {cost['water']:5.1f} | {cost['earth']:5.1f} | {cost['air']:5.1f} | {total_cost:6.1f}")
        else:
            print(f"{source_weight:4.1f}kg -> {target_weight:4.1f}kg (INVALID) | {error}")
    
    print()
    print("=== STATISTICS ===")
    if costs:
        print(f"Cost range: {min(costs):.1f} - {max(costs):.1f}")
        print(f"Cost per 1x weight ratio: {costs[1]:.1f}")
        print(f"Cost formula: 20 essence units per 1x weight ratio (5 per element)")

if __name__ == "__main__":
    main()
