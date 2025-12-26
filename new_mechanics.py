#NEW VECTOR ENGINE MECHANICS
class VectorEngine:
    def __init__(self):
        self.lexicon = {
            # --- LIGHT ALPHABET (ADDITIVE) ---
            "OOM": 1,    # Earth +1
            "THUD": 3,   # Earth +3
            "KRAK": 1,   # Fire +1
            "ZOOM": 16,  # Air +16 (Velocity)

            # --- DARK ALPHABET (SUBTRACTIVE) ---
            "NIX": -1,   # Earth -1 (Makes lighter)
            "VUL": -3,   # Earth -3
            "QUEL": -1,  # Fire -1 (Cools down)
            "HALT": -16, # Air -16 (Stops motion instantly)
        }
        
        # Determine which stat the word targets
        self.stat_map = {
            "OOM": "w", "NIX": "w", "THUD": "w", "VUL": "w",
            "KRAK": "e", "QUEL": "e",
            "ZOOM": "a", "HALT": "a"
        }

def cast_spell(caster, item, phrase, engine):
    words = phrase.upper().split()
    vectors = {"w": 0, "e": 0, "a": 0, "f": 0}
    
    # We track Absolute Strain (The cost) separately from the Vector (The effect)
    total_strain_index = 0
    
    print(f"--- Casting: '{phrase}' on {item.name} ({item.stats['w']}kg) ---")
    
    for word in words:
        if word in engine.lexicon:
            value = engine.lexicon[word]
            stat = engine.stat_map[word]
            
            # 1. Apply the Effect (Math can be negative)
            vectors[stat] += value
            
            # 2. Calculate the Cost (Math is always positive)
            # The universe charges you for the MAGNITUDE of the shift.
            strain = abs(value)
            total_strain_index += strain
            
            direction = "INCREASE" if value > 0 else "DECREASE"
            print(f"  > '{word}': {direction} {stat.upper()} by {abs(value)}")
            
    # 3. Calculate Final Load
    # Load = Total Strain * Object Weight
    load = total_strain_index * item.stats['w']
    
    print(f"  > Total Strain: {total_strain_index}")
    print(f"  > Load Calculation: {total_strain_index} * {item.stats['w']} = {load}")
    
    # 4. Check for Death
    if load > caster.conduit_limit:
        damage = load - caster.conduit_limit
        print(f"  ⚠️  OVERLOAD! Taken {damage} damage.")
    else:
        print(f"  ✅  Success. No damage.")

    # 5. Apply Stats
    for stat in vectors:
        item.stats[stat] += vectors[stat]
        # Prevent stats from vanishing completely (unless you want that)
        if item.stats[stat] < 0:
            item.stats[stat] = 0
            
            
#---- END NEW MECHANICS ----#

# ==========================================
# SCENARIOS
# ==========================================

engine = VectorEngine()
# A Heavy Rock (Weight: 100)
rock = Item("Boulder", w=100, e=0, a=0, f=50) 
me = Caster("Player", conduit_limit=250, hp=100)

# SCENARIO A: Making it float (Dark Earth)
# "VUL" (-3 Weight)
cast_spell(me, rock, "VUL", engine)
# Cost: 3 * 100 = 300 Load. (50 Damage).
# Effect: Rock is now 97kg.

# SCENARIO B: The "Halt" Word (Dark Air)
# An arrow is flying at you (Velocity: 16). You panic and shout "HALT" (-16).
arrow = Item("Arrow", w=1, e=0, a=16, f=1) # Very light object
cast_spell(me, arrow, "HALT", engine)
# Cost: 16 * 1 = 16 Load.
# Effect: Arrow velocity drops to 0. It falls out of the air.





class VectorEngine:
    def __init__(self):
        # The Base-16 Elemental Index (Partial list for demo)
        self.lexicon = {
            # EARTH (Weight/Density)
            "OOM": 1, "GRON": 2, "THUD": 3, "KARN": 4, 
            "BULD": 5, "NOM": 6, "TOR": 12, "ZHONG": 16,
            
            # WATER (Form/Durability)
            "SHII": 1, "GLUR": 2, "FALLOW": 3, "WISHP": 4, 
            "DEEP": 10, "VORT": 16,
            
            # FIRE (Energy/Explosiveness)
            "KRAK": 1, "SIZZ": 2, "FLICK": 3, "PYRE": 4, 
            "BLAZE": 6, "ZHAK": 10, "SKRATCH": 16,
            
            # AIR (Aerodynamics/Velocity)
            "SSSAA": 1, "WHIST": 2, "PHEW": 3, "ZEPH": 4, 
            "GALE": 6, "ZOOM": 16
        }

        # Map words to which stat they boost
        self.stat_map = {
            "OOM": "w", "GRON": "w", "THUD": "w", "KARN": "w", "BULD": "w", "ZHONG": "w",
            "SHII": "f", "GLUR": "f", "VORT": "f",
            "KRAK": "e", "SIZZ": "e", "ZHAK": "e", "SKRATCH": "e",
            "SSSAA": "a", "WHIST": "a", "ZEPH": "a", "ZOOM": "a"
        }

    def parse_phrase(self, phrase):
        """Converts a string like 'Oom Shii' into numerical vectors."""
        words = phrase.upper().split()
        vectors = {"w": 0, "e": 0, "a": 0, "f": 0}
        total_power_index = 0
        
        print(f"--- Parsing Vector: '{phrase}' ---")
        
        for word in words:
            if word in self.lexicon:
                value = self.lexicon[word]
                stat_type = self.stat_map.get(word, "unknown")
                
                # Add to total vector (for transformation)
                if stat_type in vectors:
                    vectors[stat_type] += value
                
                # Add to load calculation index
                total_power_index += value
                print(f"  > Word '{word}': +{value} to {stat_type.upper()}")
            else:
                print(f"  > Word '{word}' not recognized (fizzle).")
                
        return vectors, total_power_index

class Item:
    def __init__(self, name, w, e, a, f, item_type="Food"):
        self.name = name
        self.stats = {"w": w, "e": e, "a": a, "f": f}
        self.item_type = item_type

    def __repr__(self):
        return (f"[{self.name}] Type: {self.item_type} | "
                f"W:{self.stats['w']} E:{self.stats['e']} "
                f"A:{self.stats['a']} F:{self.stats['f']}")

class Caster:
    def __init__(self, name, conduit_limit, hp):
        self.name = name
        self.conduit_limit = conduit_limit  # Max safe load
        self.hp = hp

def cast_spell(caster, item, phrase, engine):
    # 1. Parse the Words
    vectors, total_power_index = engine.parse_phrase(phrase)
    
    # 2. Calculate The LOAD
    # Formula: Sum of Word Values * Object Weight
    load = total_power_index * item.stats['w']
    
    print(f"\n--- CALCULATION ---")
    print(f"Total Word Index: {total_power_index}")
    print(f"Object Anchor (Weight): {item.stats['w']}")
    print(f"Calculated Load: {load}")
    print(f"Caster Limit: {caster.conduit_limit}")
    
    # 3. Check for Burn/Recoil
    recoil_damage = 0
    if load > caster.conduit_limit:
        recoil_damage = load - caster.conduit_limit
        caster.hp -= recoil_damage
        print(f"⚠️ OVERLOAD! {caster.name} takes {recoil_damage} BURN DAMAGE.")
    else:
        print(f"✅ Stable Cast. Energy channeled safely.")

    if caster.hp <= 0:
        print(f"💀 FATAL ERROR: {caster.name} exploded.")
        return

    # 4. Transform the Item
    print(f"\n--- TRANSFORMATION ---")
    print(f"Old Item: {item}")
    
    item.stats['w'] += vectors['w']
    item.stats['e'] += vectors['e']
    item.stats['a'] += vectors['a']
    item.stats['f'] += vectors['f']
    
    print(f"New Item: {item}")
    print("-" * 30)

# ==========================================
# LET'S RUN THE SIMULATION
# ==========================================

engine = VectorEngine()

# 1. Setup our "Potato Scenario"
# Original Stats: E:24, A:15, W:50, F:10
my_potato = Item("Potato", w=50, e=24, a=15, f=10)

# 2. Setup our Caster
# Let's say a standard soldier has 250 Conduit
me = Caster("Player 1", conduit_limit=250, hp=100)

# 3. TEST 1: The Safe Cast (+1 to everything)
# Phrase: "Oom Shii Krak Sssaa" (Index 1 words)
cast_spell(me, my_potato, "Oom Shii Krak Sssaa", engine)

# Reset Potato for next test
my_potato = Item("Potato", w=50, e=24, a=15, f=10)

# 4. TEST 2: The Greedy Cast (Using higher Index words)
# Phrase: "Thud Zoom" (Earth 3, Air 16) -> attempting massive speed
print("\n\n>>> ATTEMPTING HIGH VELOCITY CAST...")
cast_spell(me, my_potato, "Thud Zoom", engine)