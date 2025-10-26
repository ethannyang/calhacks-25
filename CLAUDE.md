# CLAUDE.md - AI Assistant Implementation Guide

## 🎮 Project Overview

**Product**: League of Legends AI Coaching Overlay (CalHacks 2025 Project)
**Purpose**: Real-time AI-powered coaching overlay for League of Legends that provides actionable guidance through hybrid rule-based and LLM-powered decision making
**Status**: Phase 1 MVP Core Complete (as of 2025-10-25)
**Architecture**: Python FastAPI backend + Electron/React frontend overlay

## 🏗️ Architecture Summary

```
Game Window → Screen Capture → OCR → Game State → AI Engines → WebSocket → Overlay
                                  ↓
                            Riot API Data
```

### Key Components
1. **Backend** (Python/FastAPI): Game state processing, AI coaching logic
2. **Frontend** (Electron/React): Transparent overlay display
3. **Voice Proxy** (Node.js): Deepgram ASR integration for voice commands
4. **Combat Vision**: Audio-based ability detection for Darius vs Garen matchup

## 📁 Critical File Locations

### Backend Core Files
```
/backend/
├── main.py                    # FastAPI server entry point (WebSocket at /ws)
├── game_loop.py               # Main coordinator - CRITICAL FILE
├── requirements.txt           # Python deps (just cleaned, all accurate)
├── package.json               # Node.js deps for voice proxy
├── voice_proxy.js             # Deepgram WebSocket proxy
├── .env                       # API keys (RIOT_API_KEY, ANTHROPIC_API_KEY, etc.)
└── src/
    ├── models/game_state.py   # Pydantic models for game data
    ├── ai_engine/
    │   ├── llm_engine.py      # LLM coaching (F2, F4 features)
    │   └── rule_engine.py     # Fast deterministic rules (F1, F6)
    ├── riot_api/
    │   ├── client.py          # Riot API with rate limiting
    │   └── live_game_manager.py # Live game tracking
    ├── capture/macos.py       # macOS screen capture
    ├── ocr/extractor.py       # OCR text extraction
    └── combat_vision/         # Audio-based ability detection
        ├── combat_coach_module.py
        └── audio_template_detector.py
```

### Frontend Core Files
```
/frontend/
├── electron/main.js           # Electron window management
├── src/
│   ├── App.tsx               # Main React component
│   ├── services/
│   │   ├── websocket.ts      # Backend WebSocket connection
│   │   └── voiceStreaming.ts # Deepgram integration
│   ├── components/
│   │   ├── CommandCard.tsx   # Coaching display
│   │   └── VoiceInput.tsx    # Voice control UI
│   └── store/coachingStore.ts # Zustand state management
```

## 🚀 Current Implementation Status

### ✅ Working Features
- FastAPI WebSocket server for real-time communication
- Electron transparent overlay with click-through mode
- Rule-based coaching (F1: Safety warnings, F6: Recall timing)
- LLM coaching (F2: Wave management, F4: Objectives)
- Voice input via Deepgram cloud ASR
- Audio-based Garen ability detection
- Riot API integration with rate limiting
- Combat coaching for Darius vs Garen matchup

### ⚠️ Partially Implemented
- **Screen Capture**: macOS implementation exists but NOT fully integrated
- **OCR Extraction**: Module exists but needs integration with game loop
- **Game State Building**: Currently using mock data, needs real OCR data

### ❌ Not Implemented (Phase 2+)
- F3: Trading Advice
- F5: Rotation Guidance
- F7: Vision Coaching
- F8: Positioning Help
- Windows/Linux screen capture
- TTS for critical warnings
- Settings panel UI
- Supabase match history integration

## 🔑 API Keys & Services (.env file)

```bash
# Required API Keys (check .env file)
RIOT_API_KEY=              # Riot Games API for live game data
ANTHROPIC_API_KEY=         # Claude API for LLM coaching
OPENAI_API_KEY=            # Optional GPT-4 fallback
DEEPGRAM_API_KEY=          # Voice recognition service

# Audio Configuration
AUDIO_DEVICE_INDEX=        # For audio capture (combat vision)
```

## 📊 Data Flow

### 1. Game Loop Flow (game_loop.py)
```python
async def process_frame():
    # 1. Capture screen (1-2 FPS)
    screenshot = await capture.capture_screen()

    # 2. Extract OCR data
    ocr_data = await extractor.extract(screenshot)

    # 3. Build game state
    game_state = build_game_state(ocr_data, api_data)

    # 4. Generate coaching commands
    commands = []
    commands += rule_engine.evaluate(game_state)      # <50ms
    commands += await llm_engine.evaluate(game_state) # <500ms
    commands += combat_module.get_commands()          # Audio-based

    # 5. Broadcast to frontend
    await broadcast_callback(commands)
```

### 2. WebSocket Message Format
```typescript
// Frontend → Backend
{
  type: "config" | "command" | "voice_command",
  data: {
    // Config: { player_name, champion, role }
    // Command: { ability, target }
  }
}

// Backend → Frontend
{
  type: "coaching_command",
  data: {
    text: string,
    priority: "low" | "medium" | "high" | "critical",
    duration: number, // seconds
    feature: string   // F1-F8
  }
}
```

## 🐛 Known Issues & TODOs

### Critical Issues
1. **Screen capture not integrated** - OCR pipeline incomplete
2. **Mock game state data** - Need real OCR/API integration
3. **Hardcoded paths** in combat_coach_module.py for audio files
4. **Console.logs everywhere** - 48+ instances in frontend need cleanup
5. **Hardcoded URLs** - WebSocket URLs should be in config

### Code TODOs (found in code)
- `build_tracker.py:L##` - Adjust builds based on enemy champion
- `combat_coach_module.py:L##` - Extract Garen HP from game state
- `combat_coach_module.py:L##` - Estimate distance from game context

## 💻 Development Commands

### Backend
```bash
cd backend

# Install dependencies
pip install -r requirements.txt
npm install  # For voice proxy

# Run services
python main.py           # Start FastAPI server
node voice_proxy.js      # Start voice proxy
python game_loop.py      # Run game loop (if separate)

# Testing
python tests/test_capture.py
python tests/test_ocr.py
```

### Frontend
```bash
cd frontend

# Install and run
npm install
npm run electron:dev     # Development mode
npm run build           # Production build
npm run electron:build  # Package Electron app
```

### Running Background Services (Already Running)
- Electron dev: Background Bash 4898be, de0334
- Voice proxy: Background Bash 15616a, 7159cb

## 🎯 Implementation Priority Order

### Phase 1 Completion (URGENT)
1. **Integrate Screen Capture → OCR Pipeline**
   - Connect `capture/macos.py` → `ocr/extractor.py` in game_loop.py
   - Test OCR accuracy on actual game screenshots
   - Build real GameState from OCR data

2. **Replace Mock Data**
   - Remove hardcoded game state in game_loop.py
   - Use actual OCR + Riot API data
   - Validate data accuracy

3. **Frontend Production Cleanup**
   - Create `config.ts` for all hardcoded values
   - Replace 48+ console.logs with logger utility
   - Fix TypeScript `any` types

### Phase 2 Features
1. **Additional Coaching Features**
   - F3: Trading advice (health/damage calculations)
   - F5: Rotation guidance (map awareness)
   - F7: Vision coaching (ward placement)

2. **Platform Support**
   - Windows screen capture implementation
   - Linux screen capture implementation

3. **Enhanced UX**
   - Settings panel for configuration
   - TTS for critical warnings
   - Visual indicators for cooldowns

## 🏗️ Code Patterns & Conventions

### Backend Patterns
```python
# Async everywhere
async def process_data():
    result = await external_api()

# Pydantic for validation
class GameState(BaseModel):
    game_time: int
    player: PlayerState

# Loguru for logging
from loguru import logger
logger.info(f"Processing frame {frame_id}")
```

### Frontend Patterns
```typescript
// Zustand for state
const useCoachingStore = create((set) => ({
  currentCommand: null,
  setCommand: (cmd) => set({ currentCommand: cmd })
}));

// Service layer pattern
export class WebSocketService {
  private ws: WebSocket | null = null;
  connect(url: string) { ... }
}
```

## ⚡ Performance Targets

| Component | Target | Current Status |
|-----------|--------|----------------|
| Screen Capture | 1-2 FPS | Implemented (not integrated) |
| OCR Processing | <200ms | Unknown (not integrated) |
| Rule Engine | <50ms | ✅ Achieved |
| LLM Engine | <500ms | ✅ Achieved (cached) |
| End-to-end | <500ms | ❌ Not measured |
| CPU Usage | <10% | ❌ Not measured |
| RAM Usage | <500MB | ❌ Not measured |

## 🔧 Integration Points

### Critical Integrations
1. **Riot API** → Live game data (champion, items, stats)
2. **Deepgram** → Voice commands recognition
3. **Anthropic Claude** → Strategic coaching
4. **macOS Screen Capture** → Game visuals
5. **Tesseract/OCR** → Text extraction from game

### WebSocket Connections
- Backend ↔ Frontend: `ws://localhost:8000/ws`
- Frontend ↔ Voice Proxy: `ws://localhost:8787/stt`
- Voice Proxy ↔ Deepgram: `wss://api.deepgram.com/v1/listen`

## 📝 Important Implementation Notes

### When Working on Screen Capture/OCR
1. ROIs (Regions of Interest) are defined in `capture/macos.py`
2. Different screen resolutions need different ROI coordinates
3. OCR preprocessing (grayscale, threshold) is critical for accuracy
4. Test with actual game screenshots, not mockups

### When Working on AI Coaching
1. LLM has 2.5s update interval to prevent spam
2. Rule engine runs every frame for fast reactions
3. Context caching reduces API calls
4. Priority system: critical > high > medium > low

### When Working on Voice Input
1. Deepgram expects 16kHz PCM audio
2. AudioWorklet resamples from 48kHz → 16kHz
3. Ability detection looks for patterns: "Q", "W", "E", "R"
4. Voice proxy handles API key server-side

### When Working on Frontend
1. Overlay must remain click-through in game
2. Commands auto-clear after duration expires
3. Zustand store manages all state
4. TailwindCSS for styling (already configured)

## 🚨 Common Pitfalls

1. **Don't forget the game loop is async** - All processing must be non-blocking
2. **Rate limits exist** - Riot API: 20req/s, 100req/2min
3. **Mock data vs real data** - Game state structure changes with real OCR
4. **Cross-platform paths** - Use os.path.join(), not hardcoded paths
5. **WebSocket reconnection** - Frontend auto-reconnects, backend doesn't
6. **Audio device index** - Different on each machine, check .env

## 🎮 Testing the Integration

### Quick Test Flow
1. Start backend: `python main.py`
2. Start voice proxy: `node voice_proxy.js`
3. Start frontend: `npm run electron:dev`
4. Open League of Legends (or use test screenshot)
5. Check WebSocket connection in overlay
6. Verify coaching commands appear
7. Test voice input with "Use Q on Enemy"

### Debug Tools Available
- `/backend/debug/debug_websocket.py` - Test WebSocket messages
- `/backend/debug/debug_rois.py` - Visualize OCR regions
- `/backend/debug/check_permissions.py` - Verify screen capture access
- Chrome DevTools in Electron (Ctrl+Shift+I)

## 📚 Documentation References

- Main docs: `/README.md`, `/TECHNICAL_PRD.md`, `/MVP_STATUS.md`
- Voice setup: `/VOICE_INPUT_SETUP.md`
- Combat coaching: `/backend/COMBAT_COACHING_SETUP.md`
- macOS setup: `/MACOS_SETUP.md`

## 🔥 Next Session Quick Start

```bash
# 1. Check running processes
ps aux | grep -E "python|node|npm"

# 2. Verify .env has all keys
cat backend/.env

# 3. Start missing services
cd backend && python main.py &
cd backend && node voice_proxy.js &
cd frontend && npm run electron:dev &

# 4. Focus on completing OCR integration
# This is the #1 priority to make the MVP fully functional
```

---

**Remember**: The core architecture is solid. The main gap is connecting screen capture → OCR → game state. Once that pipeline works, the coaching AI will have real data to work with, and the MVP will be complete!

**File created**: 2025-10-25
**Last updated**: 2025-10-25
**For**: Claude AI assistants implementing this League of Legends coaching overlay