
# ============================================================================
# CONSTANTS
# ============================================================================

# Window settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800

# Tile sizes
TILE_SIZE = 24

# Difficulty: 0.5 = easy, 1.0 = normal, 2.0 = hard
TOUGHNESS = 0.8

SPAWN_MONSTERS = 15

SPAWN_SOLVENTS = 15
SPAWN_COAGULANTS = 10

# Vial sizes for solvents
VIAL_SIZES = {
    "tiny": {"name": "Tiny Vial", "volume": 10, "weight": 0.2},
    "small": {"name": "Small Vial", "volume": 25, "weight": 0.4},
    "medium": {"name": "Medium Flask", "volume": 50, "weight": 0.8},
    "large": {"name": "Large Flask", "volume": 100, "weight": 1.5},
    "grand": {"name": "Grand Bottle", "volume": 200, "weight": 3.0},
}

# Solvents for alchemy (dissolve items -> extract essence)
SOLVENTS = {
    "aqua_ignis": {
        "name": "Aqua Ignis",
        "extracts": ["fire", "air"],
        "strength": 0.8,
        "description": "Boiling alchemical water",
        "color": "orange",
    },
    "oleum_terra": {
        "name": "Oleum Terra",
        "extracts": ["earth", "water"],
        "strength": 0.9,
        "description": "Thick mineral oil",
        "color": "brown",
    },
    "alkahest": {
        "name": "Alkahest",
        "extracts": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal solvent",
        "color": "purple",
    },
}

# Coagulants for alchemy (combine essence -> form items/spells)
COAGULANTS = {
    "ite_ignis": {
        "name": "Ite Ignis",
        "affinity": ["fire"],
        "strength": 0.9,
        "description": "Ite powder",
        "color": "red",
    },
    "ite_aqua": {
        "name": "Ite Aqua",
        "affinity": ["water"],
        "strength": 0.9,
        "description": "Cool shimmering gel",
        "color": "blue",
    },
    "ite_terra": {
        "name": "Ite Terra",
        "affinity": ["earth"],
        "strength": 0.85,
        "description": "iteiteiteite",
        "color": "green",
    },
    "ite_aether": {
        "name": "Ite Aether",
        "affinity": ["air"],
        "strength": 0.85,
        "description": "Wispy ethereal mist",
        "color": "white",
    },
    "prima_ite": {
        "name": "Prima Ite",
        "affinity": ["fire", "water", "earth", "air"],
        "strength": 1.0,
        "description": "Universal coagulant",
        "color": "gold",
    },
}

# Material essence values for dissolution
MATERIAL_ESSENCES = {
    'weapons': {'fire': 25, 'water': 5, 'earth': 40, 'air': 5},
    'tools': {'fire': 20, 'water': 10, 'earth': 35, 'air': 10},
    'gems': {'fire': 30, 'water': 20, 'earth': 30, 'air': 20},
    'food': {'fire': 10, 'water': 40, 'earth': 20, 'air': 5},
    'liquids': {'fire': 5, 'water': 50, 'earth': 5, 'air': 15},
    'default': {'fire': 15, 'water': 15, 'earth': 15, 'air': 15},
}

# Colors
COLORS = {
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'gray': (128, 128, 128),
    'dark_gray': (64, 64, 64),
    'light_gray': (192, 192, 192),
    'red': (255, 0, 0),
    'dark_red': (139, 0, 0),
    'green': (0, 255, 0),
    'dark_green': (0, 100, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'orange': (255, 165, 0),
    'purple': (128, 0, 128),
    'cyan': (0, 255, 255),
    'brown': (139, 69, 19),
    'floor': (60, 50, 40),
    'wall': (40, 35, 30),
    'corridor': (50, 45, 35),
    'door': (139, 90, 43),
    'entrance': (100, 200, 100),
    'exit': (200, 100, 100),
    'player': (0, 150, 255),
    'monster': (200, 50, 50),
    'item': (255, 215, 0),
    'ui_bg': (30, 30, 40),
    'ui_border': (80, 80, 100),
    'hp_bar': (200, 50, 50),
    'stamina_bar': (50, 150, 200),
    'essence_fire': (255, 100, 50),
    'essence_water': (50, 150, 255),
    'essence_earth': (139, 90, 43),
    'essence_air': (200, 200, 255),
}


