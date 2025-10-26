# Screen Capture → OCR → Game State Pipeline Implementation

## Phase 1: Expand ROI Coverage (Priority 1)

### 1.1 Add Missing ROIs to capture/base.py

Add these critical regions to `setup_lol_rois()`:

```python
# Additional ROIs needed (normalized coordinates)
"player_level": (0.355, 0.942, 0.025, 0.020),    # Level number near portrait
"kda": (0.320, 0.005, 0.120, 0.021),            # K/D/A display top left
"enemy_champions": (0.005, 0.100, 0.150, 0.400), # Left side enemy frames
"ally_champions": (0.005, 0.500, 0.150, 0.400),  # Left side ally frames
"death_timer": (0.450, 0.450, 0.100, 0.050),    # Center screen death timer
"minion_wave": (0.430, 0.200, 0.140, 0.080),    # Minion positions
"scoreboard": (0.850, 0.050, 0.140, 0.200),     # Tab scoreboard (if open)
```

### 1.2 Enhance OCR Extraction Methods

Add to `ocr/extractor.py`:

```python
def extract_kda(self, img: np.ndarray) -> Tuple[int, int, int]:
    """Extract K/D/A from scoreboard area"""
    # Process image for white text
    processed = self.preprocess_image(img, threshold=True)

    # OCR with format "X / Y / Z"
    text = pytesseract.image_to_string(processed, config='--psm 8')

    # Parse K/D/A pattern
    match = re.match(r'(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', text)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return 0, 0, 0

def extract_level(self, img: np.ndarray) -> Optional[int]:
    """Extract player level from champion portrait area"""
    # Similar to extract_number but specifically for 1-18 range
    level = self.extract_number(img)
    if level and 1 <= level <= 18:
        return level
    return None

def detect_death_timer(self, img: np.ndarray) -> Optional[float]:
    """Detect if player is dead and get respawn timer"""
    # Look for gray overlay and timer text
    gray_pixels = self.detect_grayscale_overlay(img)
    if gray_pixels > 0.7:  # 70% gray means dead
        timer = self.extract_number(img, config='--psm 8')
        return timer
    return None
```

## Phase 2: Improve Game State Building (Priority 2)

### 2.1 Update _build_game_state in game_loop.py

```python
def _build_game_state(self, game_data: dict, frame_time: float) -> Optional[GameState]:
    """Build GameState from OCR + API data"""

    # Required fields
    game_time = game_data.get('game_time')
    if game_time is None:
        logger.warning("Missing game_time, using fallback")
        game_time = int(time.time() - self.game_start_time) if hasattr(self, 'game_start_time') else 0

    # Get live game context
    live_context = {}
    if self.live_game_mgr and self.live_game_mgr.is_in_game():
        live_context = self.live_game_mgr.get_context_summary()

    # Extract KDA
    kills, deaths, assists = game_data.get('kda', (0, 0, 0))

    # Build player state with REAL data
    player = PlayerState(
        champion_name=live_context.get('player', {}).get('champion', 'Unknown'),
        summoner_name=live_context.get('player', {}).get('summoner_name', 'Player'),
        level=game_data.get('level', 1),
        hp=int(game_data.get('hp_percent', 100)),
        hp_max=100,
        mana=int(game_data.get('mana_percent', 100)),
        mana_max=100,
        gold=game_data.get('gold', 0),
        cs=game_data.get('cs', 0),
        kills=kills,
        deaths=deaths,
        assists=assists,
        is_dead=game_data.get('death_timer') is not None,
        respawn_timer=game_data.get('death_timer', 0)
    )

    # Determine wave position from minion detection
    wave = self._analyze_wave_state(game_data.get('minion_wave_img'))

    # Build vision from enemy visibility
    vision = self._analyze_vision_state(game_data.get('enemy_champions_img'))

    # Rest of the game state...
```

## Phase 3: Calibration & Testing (Priority 3)

### 3.1 Create Calibration Tool

```python
# backend/calibrate_rois.py
import cv2
from src.capture.macos import MacOSCapture

def calibrate_rois():
    """Interactive ROI calibration tool"""
    capture = MacOSCapture()
    frame = capture.capture_game()

    if frame is None:
        print("Please start League of Legends first")
        return

    # Show frame with current ROIs overlaid
    display = frame.copy()
    capture.setup_lol_rois(frame.shape[1], frame.shape[0])

    for roi in capture.rois:
        # Draw rectangle for each ROI
        cv2.rectangle(display,
                     (roi.x, roi.y),
                     (roi.x + roi.width, roi.y + roi.height),
                     (0, 255, 0), 2)
        cv2.putText(display, roi.name,
                   (roi.x, roi.y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    # Save calibration image
    cv2.imwrite('roi_calibration.png', display)
    print("Saved roi_calibration.png - check if ROIs align with UI elements")

    # Test OCR on each ROI
    extractor = GameDataExtractor()
    roi_extracts = capture.extract_rois(frame)
    results = extractor.extract_game_data(roi_extracts)

    print("\nOCR Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    calibrate_rois()
```

### 3.2 Test Pipeline End-to-End

```python
# backend/test_pipeline.py
import asyncio
from game_loop import GameLoop

async def test_pipeline():
    """Test the complete capture → OCR → game state pipeline"""
    loop = GameLoop()

    # Capture and process one frame
    frame = loop.capture.capture_game()
    if not frame:
        print("No game window found")
        return

    # Setup ROIs
    loop.capture.setup_lol_rois(frame.shape[1], frame.shape[0])

    # Extract ROIs
    roi_extracts = loop.capture.extract_rois(frame)
    print(f"Extracted {len(roi_extracts)} ROIs")

    # Run OCR
    game_data = loop.extractor.extract_game_data(roi_extracts)
    print("\nOCR Results:")
    for key, value in game_data.items():
        if value is not None:
            print(f"  ✓ {key}: {value}")
        else:
            print(f"  ✗ {key}: None")

    # Build game state
    game_state = loop._build_game_state(game_data, time.time())
    if game_state:
        print("\nGame State Built:")
        print(f"  Time: {game_state.game_time}s")
        print(f"  Player: {game_state.player.champion_name} Lvl {game_state.player.level}")
        print(f"  KDA: {game_state.player.kills}/{game_state.player.deaths}/{game_state.player.assists}")
        print(f"  Gold: {game_state.player.gold}, CS: {game_state.player.cs}")
        print(f"  HP: {game_state.player.hp}%, Mana: {game_state.player.mana}%")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
```

## Phase 4: Optimization (Priority 4)

### 4.1 Performance Improvements

1. **Cache OCR results** for static elements (level changes slowly)
2. **Parallel ROI processing** using asyncio
3. **Reduce OCR calls** by using color detection where possible
4. **Skip OCR** when dead (gray screen detection)

### 4.2 Accuracy Improvements

1. **Multiple OCR attempts** with different preprocessing
2. **Confidence scoring** for OCR results
3. **Fallback to previous values** if OCR fails
4. **Validate ranges** (level 1-18, gold > 0, etc.)

## Implementation Order

1. **Today: Calibrate existing ROIs**
   ```bash
   python calibrate_rois.py
   ```

2. **Next: Test current pipeline**
   ```bash
   python test_pipeline.py
   ```

3. **Then: Add missing ROIs one by one**
   - Start with player_level (easiest)
   - Then KDA (important for coaching)
   - Then death detection
   - Finally wave/vision state

4. **Finally: Remove all mock data**
   - Replace hardcoded values with OCR/API data
   - Add fallbacks for missing data

## Quick Fixes for Immediate Testing

### Fix 1: Ensure ROIs are calibrated
```python
# In game_loop.py, add debug output
def process_frame(self):
    # After ROI extraction
    roi_extracts = self.capture.extract_rois(frame)

    # Debug: save ROI images
    for name, img in roi_extracts.items():
        if img is not None:
            cv2.imwrite(f"debug_roi_{name}.png", img)
```

### Fix 2: Use fallback values
```python
# In _build_game_state
game_time = game_data.get('game_time', 0)  # Default to 0
gold = game_data.get('gold', 500)  # Default starting gold
cs = game_data.get('cs', 0)
hp_percent = game_data.get('hp_percent', 100)
```

### Fix 3: Log what's working
```python
# Add to game_loop.py
successful_extracts = {k: v for k, v in game_data.items() if v is not None}
logger.info(f"Successfully extracted: {list(successful_extracts.keys())}")
```

## Testing Commands

```bash
# 1. Test capture
python -c "from src.capture.macos import MacOSCapture; c=MacOSCapture(); print(c.find_game_window())"

# 2. Test OCR
python tests/test_ocr.py

# 3. Test full pipeline
python test_pipeline.py

# 4. Run with debug logging
LOGURU_LEVEL=DEBUG python main.py
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Window not found" | Make sure LoL is running and not minimized |
| OCR returns None | ROIs need calibration for your resolution |
| Wrong values extracted | Adjust preprocessing thresholds |
| Performance issues | Reduce capture FPS in .env |
| Mock data still showing | Check _build_game_state is using game_data |

## Success Criteria

✅ Pipeline captures League window
✅ OCR extracts at least: gold, CS, game time
✅ Game state uses real data not mock
✅ Commands reflect actual game state
✅ <500ms end-to-end latency

## Next Steps After Pipeline Works

1. Add more sophisticated OCR (items, enemy positions)
2. Implement minimap analysis
3. Add death/respawn detection
4. Enhance wave state detection
5. Add combat state recognition