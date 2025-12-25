"""
Centralized path configuration for Pangea project
All file paths should be imported from here
"""

import os

# Base directory (where this file is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# JSON configuration files
LANDSCAPE_FEATURES = os.path.join(DATA_DIR, "landscape_features.json")
SEED_CONFIG = os.path.join(DATA_DIR, "seed_config.json")

# Output/temp directories
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Default filenames
DEFAULT_WORLD_DB = os.path.join(OUTPUT_DIR, "world.db")
DEFAULT_PREVIEW = os.path.join(TEMP_DIR, "preview_temp.png")


def get_data_path(filename: str) -> str:
    """Get full path to a file in data directory"""
    return os.path.join(DATA_DIR, filename)


def get_output_path(filename: str) -> str:
    """Get full path to a file in output directory"""
    return os.path.join(OUTPUT_DIR, filename)


def get_temp_path(filename: str) -> str:
    """Get full path to a file in temp directory"""
    return os.path.join(TEMP_DIR, filename)
