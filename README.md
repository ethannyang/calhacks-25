# League of Legends AI Coaching Overlay

Real-time AI coaching overlay for League of Legends that provides actionable guidance through hybrid rule-based and LLM-powered decision making.

## Features

- **Transparent Overlay**: Frameless, always-on-top window with click-through
- **Real-time Coaching**: <500ms latency from game state to recommendations
- **Hybrid AI**: Fast rule-based engine (<50ms) + strategic LLM decisions (<500ms)
- **WebSocket Communication**: Real-time bidirectional communication
- **Priority-Based UI**: Visual styling based on command urgency

## Architecture

### Backend (Python)
- **FastAPI**: High-performance async web framework
- **OpenCV**: Screen capture and image processing
- **Tesseract/EasyOCR**: OCR for game data extraction
- **Riot API Client**: Rate-limited API integration
- **AI Engines**:
  - Rule Engine: F1 (Safety Warnings), F6 (Recall Timing)
  - LLM Engine: F2 (Wave Management), F4 (Objective Coaching)

### Frontend (Electron + React)
- **Electron**: Cross-platform desktop overlay
- **React + TypeScript**: UI components
- **Zustand**: State management
- **TailwindCSS**: Styling
- **WebSocket**: Real-time backend connection

## Setup

### Backend Setup

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Development mode
npm run electron:dev
```

## Configuration

Edit `backend/.env`:

```env
RIOT_API_KEY=your_riot_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Get API keys:
- **Riot API**: https://developer.riotgames.com/
- **Anthropic Claude**: https://console.anthropic.com/

## Running the Application

1. **Start Backend**:
```bash
cd backend
python3 main.py
```
Backend runs on `http://localhost:8000`

2. **Start Frontend** (in new terminal):
```bash
cd frontend
npm run electron:dev
```

## Keyboard Shortcuts

- **Ctrl+Shift+C**: Toggle click-through mode
- **Ctrl+Shift+I**: Toggle DevTools
- **Ctrl+Shift+R**: Reload overlay

## MVP Features (Phase 1)

- ✅ FastAPI backend with WebSocket
- ✅ Riot API client with rate limiting
- ✅ Pydantic data models
- ✅ Rule-based engine (F1: Safety Warnings)
- ✅ LLM engine (F2: Wave Management, F4: Objectives)
- ✅ Electron transparent overlay
- ✅ React UI with priority-based styling
- ✅ WebSocket real-time communication
- 🚧 Screen capture module (Windows)
- 🚧 OCR extraction (gold, CS, HP/mana)

## Project Structure

```
calhacks-25/
├── backend/
│   ├── src/
│   │   ├── models/          # Pydantic data models
│   │   ├── riot_api/        # Riot API client
│   │   ├── ai_engine/       # Rule + LLM engines
│   │   ├── capture/         # Screen capture (TODO)
│   │   └── ocr/             # OCR processing (TODO)
│   ├── main.py              # FastAPI entry point
│   └── requirements.txt
├── frontend/
│   ├── electron/            # Electron main process
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # WebSocket service
│   │   └── store/           # Zustand store
│   └── package.json
└── TECHNICAL_PRD.md         # Full technical specification
```

## Technical Specifications

- **Target Latency**: <500ms end-to-end
- **CPU Usage**: <10% average
- **RAM Usage**: <500MB
- **FPS Impact**: <5%
- **OCR Accuracy**: 85%+

## Next Steps (Phase 2)

- [ ] Implement screen capture (Windows Graphics Capture API)
- [ ] Implement OCR extraction pipeline
- [ ] Add game state aggregation service
- [ ] Test with live League of Legends game
- [ ] Add F3-F8 coaching features
- [ ] macOS/Linux support
- [ ] TTS for critical warnings

## License

MIT

## Technical PRD

See [TECHNICAL_PRD.md](./TECHNICAL_PRD.md) for complete engineering specification.
