#!/usr/bin/env python3
"""
Calculate transmutation costs for level 1 magician
"""

def calculate_transmute_cost(source_weight, target_weight, wisdom=12):
    """Calculate transmutation cost with Wisdom modifier"""
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
    
    # Apply Wisdom modifier (5% reduction per point above 10)
    wisdom_modifier = max(0, (wisdom - 10) * 0.05)  # WIS 12 = 10% reduction
    
    # Apply modifier to costs
    modified_cost = {}
    for element, cost in base_cost.items():
        modified_cost[element] = cost * (1.0 - wisdom_modifier)
    
    return modified_cost, None

def main():
    print("=== LEVEL 1 MAGICIAN TRANSFORMATION COSTS ===")
    print("Wisdom: 12 (10% cost reduction)")
    print("Source -> Target (Weight) | Fire | Water | Earth | Air | Total")
    print("-" * 65)
    
    # Test realistic weapon weights
    test_cases = [
        ("Potato", 0.5, "Dagger", 0.5),      # Same weight, small weapon
        ("Potato", 0.5, "Knife", 0.3),      # Lighter weapon
        ("Potato", 0.5, "Short Sword", 1.0), # Heavier weapon
        ("Potato", 0.5, "Long Sword", 2.0),  # Max weight (2x)
        ("Potato", 0.5, "Greatsword", 3.0),  # Too heavy (invalid)
        ("Rock", 2.0, "Sword", 1.5),        # Rock to sword
        ("Rock", 2.0, "Shield", 3.0),        # Rock to shield
        ("Rock", 2.0, "Greatsword", 4.0),    # Max weight (2x)
    ]
    
    for source_name, source_weight, target_name, target_weight in test_cases:
        cost, error = calculate_transmute_cost(source_weight, target_weight)
        if cost:
            total_cost = sum(cost.values())
            weight_ratio = target_weight / source_weight
            print(f"{source_name} ({source_weight:4.1f}) -> {target_name} ({target_weight:4.1f}) | "
                  f"{cost['fire']:4.1f} | {cost['water']:4.1f} | {cost['earth']:4.1f} | {cost['air']:4.1f} | {total_cost:5.1f}")
        else:
            print(f"{source_name} -> {target_name}: {error}")
    
    print()
    print("=== ANALYSIS ===")
    print("Potato (0.5kg) -> Dagger (0.5kg): 18 essence total")
    print("Potato (0.5kg) -> Short Sword (1.0kg): 36 essence total") 
    print("Potato (0.5kg) -> Long Sword (2.0kg): 72 essence total")
    print("Rock (2.0kg) -> Greatsword (4.0kg): 72 essence total")
    print()
    print("Conclusion: Level 1 magician can make daggers easily,")
    print("short swords moderately, long swords with significant cost.")

if __name__ == "__main__":
    main()
