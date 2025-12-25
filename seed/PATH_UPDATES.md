# Path Updates Summary

## New File: paths.py

Centralized path configuration for all files:

```python
from paths import LANDSCAPE_FEATURES, SEED_CONFIG, DATA_DIR, OUTPUT_DIR
```

### Available Constants

- `BASE_DIR` - Project root directory
- `DATA_DIR` - data/ folder
- `LANDSCAPE_FEATURES` - data/landscape_features.json
- `SEED_CONFIG` - data/seed_config.json
- `OUTPUT_DIR` - output/ folder (auto-created)
- `TEMP_DIR` - temp/ folder (auto-created)

### Helper Functions

- `get_data_path(filename)` - Get path to file in data/
- `get_output_path(filename)` - Get path to file in output/
- `get_temp_path(filename)` - Get path to file in temp/

## Updated Files

### ✅ render_features.py
- Now imports `from paths import LANDSCAPE_FEATURES`
- Default parameter uses `LANDSCAPE_FEATURES` constant
- No more hardcoded 'landscape_features.json'

### ✅ feature_editor.py
- Imports `from paths import LANDSCAPE_FEATURES`
- Uses `CONFIG_PATH = LANDSCAPE_FEATURES`
- Removed inline path construction

### ✅ seed_doci.py
- Imports `from paths import SEED_CONFIG, DATA_DIR`
- Uses `CONFIG_PATH = SEED_CONFIG`
- Removed inline path construction

### ✅ test_zoom.py
- Imports `from paths import SEED_CONFIG`
- Loads config from `SEED_CONFIG` constant
- Updated to use `RenderFeatures` (your renamed class)
- Removed `/tmp` hardcoded paths

## Directory Structure

```
pangea/
├── paths.py                      # NEW: Central path config
├── data/                         # JSON configs
│   ├── landscape_features.json
│   └── seed_config.json
├── output/                       # Generated files (auto-created)
├── temp/                         # Temp files (auto-created)
├── render_features.py            # Updated
├── feature_editor.py             # Updated
├── seed_doci.py                  # Updated
├── test_zoom.py                  # Updated
└── ... other files
```

## Benefits

1. **No hardcoded paths** - All paths defined once in paths.py
2. **Cross-platform** - Uses `os.path.join()` properly
3. **Auto-creation** - Creates data/, output/, temp/ if missing
4. **Easy to change** - Modify one file to change all paths
5. **Import consistency** - Everyone uses same constants

## Usage Examples

### In Your Code

```python
from paths import LANDSCAPE_FEATURES, SEED_CONFIG, OUTPUT_DIR

# Load landscape features
with open(LANDSCAPE_FEATURES, 'r') as f:
    features = json.load(f)

# Save output
output_file = os.path.join(OUTPUT_DIR, 'world_map.png')
plt.savefig(output_file)
```

### Adding New Config Files

Edit paths.py:

```python
# Add to paths.py
GAME_CONFIG = os.path.join(DATA_DIR, "game_config.json")
PLAYER_DATA = os.path.join(DATA_DIR, "player_data.json")
```

Then import anywhere:

```python
from paths import GAME_CONFIG, PLAYER_DATA
```

## Testing

All updated files now use consistent paths:

```bash
cd /home/claude
python test_zoom.py          # Works - uses paths.py
python feature_editor.py      # Works - uses paths.py
python seed_doci.py           # Works - uses paths.py
```

No more `/tmp` paths, no more hardcoded strings!

## Migration Notes

If you have other files that use hardcoded paths:

**Before:**
```python
config = json.load(open('data/my_config.json'))
```

**After:**
```python
from paths import get_data_path
config = json.load(open(get_data_path('my_config.json')))
```

Or add to paths.py:
```python
MY_CONFIG = os.path.join(DATA_DIR, "my_config.json")
```

Then:
```python
from paths import MY_CONFIG
config = json.load(open(MY_CONFIG))
```
