# League of Legends AI Coaching - Quick Start Guide

## What's Working ✅

### 1. Screen Capture System
- Captures League of Legends game window at 1 FPS
- Extracts ROIs (gold, CS, HP, mana, minimap, game time)
- Works on macOS with proper permissions

### 2. OCR Extraction
- Extracts gold, CS, and game time with Tesseract OCR
- Color-based HP/Mana percentage detection
- Tested and verified working (test_ocr.py)

### 3. AI Coaching Engines
- **Rule Engine**: Fast safety warnings (<50ms)
- **LLM Engine**: Strategic coaching with Claude (~1.7s)
- Both engines generating contextual game advice

### 4. Backend Server
- FastAPI server with WebSocket support
- Game loop runs as background task
- Commands broadcast to all connected clients

## How to Run

### Option 1: Standalone Game Loop (Testing)
```bash
python3 game_loop.py
```
This runs the game loop with mock command output to console.

### Option 2: Full Server with WebSocket
```bash
python3 main.py
# Or use uvicorn:
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Server runs on http://localhost:8000

### WebSocket Connection
Connect to: `ws://localhost:8000/ws`

Commands are broadcast in this format:
```json
{
  "type": "command",
  "data": {
    "priority": "high",
    "category": "safety",
    "icon": "⚠️",
    "message": "DANGER: Low HP - BACK OFF",
    "duration": 5,
    "timestamp": 1729825051.138
  }
}
```

## Testing

### 1. Test Screen Capture
```bash
python3 test_capture.py
```
Captures a frame and saves ROI extracts.

### 2. Test OCR Extraction
```bash
python3 test_ocr.py
```
Runs OCR on captured frames and shows extracted data.

### 3. Test Full Pipeline
```bash
python3 game_loop.py
```
Runs the complete integration (capture → OCR → AI → output).

## Configuration

Edit `.env` file:
```env
RIOT_API_KEY=your_riot_api_key
ANTHROPIC_API_KEY=your_anthropic_key
CAPTURE_FPS=1
LOG_LEVEL=INFO
```

## Performance Metrics

From testing:
- **Screen Capture**: ~100-200ms
- **OCR Extraction**: ~300-400ms per frame
- **Rule Engine**: <50ms
- **LLM Engine**: ~1.7s (runs every 5 seconds)
- **Total Frame Processing**: ~470ms average

## What's Next

### Immediate Priorities:
1. **Frontend/Overlay**: Electron app to display commands in-game
2. **Enhanced Game State**: Integrate Riot API for full champion/team data
3. **Minimap Analysis**: Computer vision for enemy positions
4. **More Coaching Rules**: Expand rule engine with more scenarios

### To Build Frontend:
You'll need an Electron overlay that:
1. Connects to `ws://localhost:8000/ws`
2. Displays commands as overlay notifications
3. Stays on top of game window
4. Transparent background with positioned elements

## Architecture

```
League of Legends Game
         ↓
   Screen Capture (MacOSCapture)
         ↓
   ROI Extraction
         ↓
   OCR (Tesseract)
         ↓
   Game State Builder
         ↓
   ┌─────────┴──────────┐
   ↓                    ↓
Rule Engine        LLM Engine
   ↓                    ↓
   └─────────┬──────────┘
         ↓
   Coaching Command
         ↓
   WebSocket Broadcast
         ↓
   Electron Overlay (TODO)
         ↓
   Player sees in-game!
```

## Troubleshooting

### "tesseract not installed"
```bash
brew install tesseract
```

### "Screen recording permission denied"
1. Go to System Settings → Privacy & Security → Screen Recording
2. Enable permission for Terminal/Python

### "Lost game window"
- Make sure LoL is in focus and not minimized
- Window ID can change if game is restarted

### OCR extraction fails
- Check ROI coordinates in `base.py:setup_lol_rois()`
- Different resolutions may need ROI adjustment
- Run `debug_rois.py` to visualize ROI positions

## Notes

- Currently uses mock data for champion names, KDA, team data
- Full integration requires Riot API connection
- LLM model will be deprecated Oct 2025, update to latest Claude version
- Capture only works while LoL is visible (not minimized)

---

🎮 **Status**: Backend fully functional, ready for frontend integration!
