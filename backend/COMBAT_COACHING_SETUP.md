# Combat Coaching Setup Guide

Audio-based ability detection for Darius vs Garen matchup with real-time coaching overlay.

## Overview

This system uses **audio template matching** to detect Garen's abilities (Q, W, E, R) and provides real-time combat coaching for Darius players through the overlay.

## Architecture

```
League Audio → BlackHole → Audio Detector → Combat Coach → Game Loop → WebSocket → Overlay
```

1. **BlackHole**: Virtual audio device captures League's system audio
2. **Audio Template Detector**: Matches Garen ability sounds using cross-correlation
3. **Combat Coach**: Analyzes detected abilities + game state → generates coaching commands
4. **Game Loop**: Integrates all systems and broadcasts to overlay
5. **Overlay**: Displays real-time coaching advice on screen

## Setup Instructions

### 1. Install BlackHole (Required)

BlackHole is a free virtual audio device for macOS that lets us capture system audio.

```bash
brew install blackhole-2ch
```

### 2. Configure Audio MIDI Setup

1. Open **Spotlight** (Cmd+Space) and search "Audio MIDI Setup"
2. Click the **"+"** button at bottom left
3. Select **"Create Multi-Output Device"**
4. Check both:
   - ✓ **Built-in Output** (so you can hear the game)
   - ✓ **BlackHole 2ch** (so we can capture audio)
5. Right-click the **Multi-Output Device** → **"Use This Device For Sound Output"**

### 3. Test Audio Setup

Verify BlackHole is working:

```bash
cd /Users/ethan/Desktop/projects/calhacks-25/backend
python3 -c "from src.combat_vision.audio_template_detector import AudioTemplateDetector; AudioTemplateDetector.list_audio_devices()"
```

You should see "BlackHole 2ch" in the list. Note its device index (e.g., `2`).

### 4. Configure Backend

Add the BlackHole device index to your `.env` file:

```bash
# In backend/.env
AUDIO_DEVICE_INDEX=2  # Replace with your BlackHole device index
```

### 5. Test Audio Detection (Optional)

Test the audio detection system standalone:

```bash
cd /Users/ethan/Desktop/projects/calhacks-25/backend
python3 test_audio_template.py
```

- Choose option 1 to list devices
- Choose option 2 and enter BlackHole device index
- Play League and fight Garen - you should see ability detections

### 6. Run Full System

Start the backend with combat coaching enabled:

```bash
cd /Users/ethan/Desktop/projects/calhacks-25/backend
python3 main.py
```

You should see:
```
✅ Combat coach module enabled (audio device: 2)
✅ Combat coach module started (audio detection active)
```

### 7. Start the Overlay

In another terminal:

```bash
cd /Users/ethan/Desktop/projects/calhacks-25
npm start
```

The Electron overlay will launch and connect to the backend.

### 8. Play League

1. Start a game as **Darius**
2. Lane against **Garen**
3. The overlay will show real-time coaching advice:
   - "GAREN Q! BACK OFF - you'll get silenced!"
   - "GAREN SPINNING! WALK OUT NOW!"
   - "Garen E ends in 1.2s - PREPARE TO ENGAGE!"
   - "4 STACKS! HIT Q FOR NOXIAN MIGHT!"
   - etc.

## How It Works

### Audio Detection

The system uses **template matching** with actual Garen ability sound files:

1. Loads Garen's Q, W, E, R audio files as templates
2. Continuously captures live audio from League via BlackHole
3. Performs FFT-based cross-correlation between templates and live audio
4. Detects abilities when correlation exceeds threshold (60% by default)

**Advantages:**
- Position-independent (works regardless of camera position)
- No need to track Garen's location on screen
- More accurate than visual detection with game effects
- Handles volume variations and background noise

### Combat Coaching Logic

The `DariusVsGarenCoach` implements matchup-specific knowledge:

**Priority 1: Critical Situations**
- Garen R when low HP → "FLASH NOW or you die!"
- Garen E spinning → "WALK OUT NOW!"
- Garen Q incoming → "BACK OFF - you'll get silenced!"

**Priority 2: High Value Opportunities**
- Garen abilities on cooldown → "PULL (E) + TRADE!"
- 4 bleed stacks → "HIT Q FOR NOXIAN MIGHT!"
- Noxian Might active → "ALL IN - YOU WIN!"

**Priority 3: Trading Windows**
- Garen W shield up → "WAIT 2s then trade"
- Safe Q poke range → "Hit Q (outer ring) for poke + heal!"

**Priority 4: Defensive Positioning**
- Low HP → "Play safe near tower"
- Garen full combo up → "Respect spacing"

### Command Priority System

Commands are prioritized (highest to lowest):

1. **Combat** (real-time fight-or-flight decisions from audio detection)
2. **Recall** (item build recommendations)
3. **LLM** (wave management, macro strategy)
4. **Rule** (basic safety checks)

## Troubleshooting

### "Audio capture not active"

**Problem:** Backend logs show combat coaching disabled

**Solutions:**
- Check BlackHole is installed: `brew list | grep blackhole`
- Verify AUDIO_DEVICE_INDEX is set in `.env`
- Run device list command to find correct index
- Restart backend after changing `.env`

### "No abilities detected"

**Problem:** Audio detection running but no Garen abilities detected

**Solutions:**
- Ensure League audio is playing (check in-game sound settings)
- Verify Multi-Output Device is set as system output
- Increase in-game sound effects volume
- Lower detection threshold in combat_coach_module.py (try 0.4 instead of 0.6)

### "BlackHole not in device list"

**Problem:** BlackHole installed but not showing up

**Solutions:**
- **Restart your Mac** (required after BlackHole installation)
- Or restart CoreAudio: `sudo killall coreaudiod`
- Check Audio MIDI Setup for BlackHole device

### "Permission denied" errors

**Problem:** Audio capture fails with permission errors

**Solutions:**
- Grant microphone permissions to Terminal/Python
- System Settings → Privacy & Security → Microphone
- Add Terminal.app and Python

## Performance

- **Audio Detection:** ~30 Hz processing rate
- **Game Loop:** 1 FPS by default (configurable)
- **Combat Commands:** Real-time (< 100ms latency from ability sound to overlay)
- **CPU Usage:** ~5-10% additional overhead for audio detection

## Files

- `src/combat_vision/audio_template_detector.py` - Audio detection engine
- `src/combat_vision/darius_vs_garen_coach.py` - Matchup-specific coaching logic
- `src/combat_vision/combat_coach_module.py` - Integration layer
- `game_loop.py` - Main game loop with combat coaching
- `test_audio_template.py` - Standalone audio detection test
- `*.wav` - Garen ability audio templates (Q, W, E, R)

## Future Improvements

- [ ] Add HP detection via OCR for more accurate R dunk timing
- [ ] Detect distance to Garen using minimap or visual detection
- [ ] Add Darius ability tracking (Q, E, R cooldowns)
- [ ] Expand to other matchups (e.g., Darius vs Mordekaiser)
- [ ] Machine learning model for audio classification
- [ ] Support for multiple audio devices/configurations
