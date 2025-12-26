#!/usr/bin/env python3
"""
Simple test script to analyze transmutation costs across weight ranges
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

def analyze_weight_ranges():
    """Analyze costs across different weight ranges"""
    
    # Test weight ranges from small to large
    test_weights = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
    
    print("=== WEIGHT RANGE ANALYSIS ===")
    print("Source -> Target (Weight Ratio) | Fire | Water | Earth | Air | Total")
    print("-" * 70)
    
    costs_data = []
    max_cost = 0
    min_cost = float('inf')
    max_ratio = 0
    min_ratio = float('inf')
    
    for source_weight in test_weights:
        for target_weight in test_weights:
            if target_weight <= source_weight * 2:  # Valid transformation
                cost, error = calculate_transmute_cost(source_weight, target_weight)
                if cost:
                    weight_ratio = target_weight / source_weight
                    total_cost = sum(cost.values())
                    costs_data.append((source_weight, target_weight, weight_ratio, cost, total_cost))
                    
                    # Track min/max
                    max_cost = max(max_cost, total_cost)
                    min_cost = min(min_cost, total_cost)
                    max_ratio = max(max_ratio, weight_ratio)
                    min_ratio = min(min_ratio, weight_ratio)
                    
                    print(f"{source_weight:4.1f}kg -> {target_weight:4.1f}kg ({weight_ratio:4.1f}x) | "
                          f"{cost['fire']:5.1f} | {cost['water']:5.1f} | {cost['earth']:5.1f} | {cost['air']:5.1f} | {total_cost:6.1f}")
    
    print()
    print("=== STATISTICS ===")
    print(f"Valid transformations tested: {len(costs_data)}")
    print(f"Weight ratio range: {min_ratio:.2f}x - {max_ratio:.2f}x")
    print(f"Total essence cost range: {min_cost:.1f} - {max_cost:.1f}")
    print(f"Cost per unit weight ratio: {max_cost/max_ratio:.1f}")
    
    print()
    print("=== SAMPLE TRANSFORMATIONS ===")
    print("Potato (0.5kg) transformations:")
    potato_weight = 0.5
    for target_weight in [0.5, 0.8, 1.0]:  # Valid targets for potato
        cost, error = calculate_transmute_cost(potato_weight, target_weight)
        if cost:
            total = sum(cost.values())
            ratio = target_weight / potato_weight
            print(f"  -> {target_weight}kg ({ratio:.1f}x) | Total cost: {total:.1f}")
    
    print()
    print("Sword (2.0kg) transformations:")
    sword_weight = 2.0
    for target_weight in [1.0, 2.0, 3.0, 4.0]:  # Valid targets for sword
        cost, error = calculate_transmute_cost(sword_weight, target_weight)
        if cost:
            total = sum(cost.values())
            ratio = target_weight / sword_weight
            print(f"  -> {target_weight}kg ({ratio:.1f}x) | Total cost: {total:.1f}")

if __name__ == "__main__":
    analyze_weight_ranges()
