# Engineering Specification
# League of Legends AI Coaching Overlay

## 1. Product Overview

### 1.1 Product Vision
An intelligent, real-time coaching overlay for League of Legends that provides actionable guidance to beginner players (Iron-Silver rank) through AI-powered game state analysis and directive coaching commands.

### 1.2 Problem Statement
Beginner League of Legends players struggle to improve due to:
- Information overload during gameplay
- Lack of real-time feedback on decision-making
- Difficulty translating theoretical knowledge into in-game actions
- Limited access to personalized coaching

### 1.3 Solution
A lightweight, cross-platform overlay application that:
- Captures and analyzes live game state with <500ms latency
- Provides context-aware, directive coaching commands
- Overlays actionable advice directly on the game screen
- Requires minimal setup and zero in-game configuration

---

## 2. Goals & Success Metrics

### 2.1 Primary Goals
1. Help beginner players improve win rate by 5-10% within 20 games
2. Reduce user decision-making time for critical macro plays
3. Provide educational value that persists beyond active coaching

### 2.2 Key Performance Indicators (KPIs)

**Product Metrics:**
- User adoption: 1,000+ active users in first 3 months
- Session engagement: 70%+ of games completed with overlay active
- User retention: 40%+ weekly active user retention

**Technical Metrics:**
- Coaching latency: <500ms from game state change to recommendation
- Overlay FPS impact: <5% reduction in game performance
- Accuracy: 85%+ accuracy in OCR-based data extraction
- Uptime: 99%+ availability for Riot API integration

**User Impact Metrics:**
- Average rank improvement: Users increase 1+ division within 50 games
- User satisfaction: 4.0+ star rating
- Learning outcomes: Users report improved game knowledge in surveys

---

## 3. Component Specifications

### 3.1 Screen Capture Pipeline
**Technology:** OpenCV (Python)

**Responsibilities:**
- Capture game screen at 1-2 FPS
- Detect region-of-interest (ROI) for UI elements
- Preprocess images for OCR (grayscale, thresholding)

**Requirements:**
- Cross-platform capture (Windows: Windows Graphics Capture API, macOS: CGWindowListCreateImage)
- CPU usage <5%
- Configurable capture regions
- Support for multiple monitor setups

**Data Extraction Targets:**
- Player gold count (top-right UI)
- CS (creep score) count
- HP/Mana bars (OCR + color detection)
- Minimap (for champion positions, vision)
- Game timer
- Death timers

### 3.2 Riot API Integration
**Technology:** Python async HTTP client (aiohttp)

**Endpoints:**
- `/lol/summoner/v4/summoners/by-name/{summonerName}`
- `/lol/spectator/v4/active-games/by-summoner/{encryptedSummonerId}`
- `/lol/match/v5/matches/by-puuid/{puuid}/ids`
- `/lol/platform/v3/champion-rotations`
- Data Dragon (static champion/item data)

**Data Retrieval:**
- Live game state (participant list, game time, scores)
- Static champion stats and abilities
- Player match history
- Item builds and economy

**Requirements:**
- Secure API key management and rotation
- Implement rate limiting handler (20 req/sec, 100 req/2 min)
- Cache static data (champions, items)
- Implement fallback mechanisms for API downtime
- Support regional endpoints

### 3.3 AI Decision Engine
**Technology:** Hybrid LLM (Claude/GPT-4) + Python Rule-Based System

**Architecture:**
```
Game State Input (OCR + API)
     ↓
┌─────────────────┐
│ Rule Engine     │ ← Fast, deterministic checks
│ (Python)        │   (e.g., safety, low HP)
└────────┬────────┘
        │
        ↓
┌─────────────────┐
│ Context Builder │ ← Format state to JSON for LLM
└────────┬────────┘
        │
        ↓
┌─────────────────┐
│ LLM API         │ ← Strategic decisions
│ (Claude/GPT-4)  │   (e.g., macro, wave mgt)
└────────┬────────┘
        │
        ↓
┌─────────────────┐
│ Command         │ ← Format LLM text to UI command
│ Formatter       │
└─────────────────┘
```

**Rule-Based Logic (Target: <50ms):**
- Safety warnings (position + enemy MIA + vision)
- Basic CS reminders (cannon minion)
- Recall triggers (low HP/mana + safe location)
- Ward expiration tracking

**LLM Integration (Target: <500ms):**
- Wave management (context: enemy pos, objectives, wave state)
- Objective priority (dragon, baron, tower)
- Rotation guidance (TP plays, roams)
- Trading windows (cooldowns, minion advantage)

**Prompt Engineering:**
- Input: Structured JSON with game state
- Style: Few-shot examples for consistent, directive output
- Parameters: Temperature: 0.3, Max tokens: 100

**LLM Provider:**
- Primary: Anthropic Claude (Sonnet)
- Fallback: OpenAI GPT-4
- Future: Llama 3 8B (local/offline mode)

### 3.4 Overlay UI
**Technology:** Electron + React + TypeScript

**Specifications:**
- Frameless, transparent window
- Always-on-top, click-through enabled (WS_EX_TRANSPARENT / NSWindow)
- Hardware acceleration enabled
- Target UI update latency: <100ms

**Features:**
- Customizable position and size
- Opacity control (50-100%)
- Font size/color options
- Command history (last 5 commands)
- Priority-based highlighting (e.g., critical warnings in red)

**UI Components:**
- CommandCard: Displays current directive
- TimerWidget: Tracks objectives, summoner spells
- SettingsPanel: Toggled via hotkey (Ctrl+Shift+C)
- PerformanceMonitor: Displays FPS, latency (debug mode)
- MatchHistoryView (Phase 3): Fetches and displays data from Supabase

---

## 4. Functional Implementation (Core Features)

### F1: Safety Warnings
**Triggers:**
- Player position >50% lane with no allied vision
- 3+ enemies missing from minimap
- Player HP <30% with enemy jungler detected nearby (minimap)
- Tower dive risk (multiple enemies under tower, low HP)

**Output Example:**
- "⚠️ DANGER: Back off - 3 enemies missing, no vision"
- "⚠️ WARNING: Enemy jungler bot side, ward river"

**Implementation:**
- Rule-based system
- Minimap analysis: enemy position detection via color matching
- API data: vision score, ward placement tracking
- Response time: <100ms

### F2: Wave Management
**Triggers:**
- Wave state near enemy tower (slow push)
- Cannon wave arriving (freeze)
- Player recall intent (hard shove)
- Objective spawning in <60s (setup push)

**Output Example:**
- "🌊 SLOW PUSH: Last hit only, build large wave"
- "🌊 HARD SHOVE: Clear wave fast, recall for items"
- "🌊 FREEZE: Let enemy push, zone from CS"

**Implementation:**
- OCR: Minion count detection
- API: Wave position estimation
- LLM: Strategic decision based on game context
- Response time: <500ms

### F3: Trading Advice
**Triggers:**
- Enemy key ability on cooldown
- Minion wave advantage (>3 minion difference)
- Player hits level/item powerspike
- Enemy low on resources (mana/energy)

**Output Example:**
- "⚔️ TRADE: Enemy E on CD for 8s, play aggressive"
- "⚔️ DISENGAGE: Enemy level 6, you're 5 - play safe"

### F4: Objective Coaching
**Triggers:**
- Objective spawning in 60s
- Numbers advantage near objective
- Enemy jungler visible on opposite side of map
- Post-teamfight (ace or key enemies dead)

**Output Example:**
- "🐉 DRAGON in 45s: Ward river, group bot"
- "🏆 BARON: Enemy jungler top, 4v3 setup NOW"

### F5: Rotation Guidance
**Output Example:**
- "🔄 ROAM: Shove mid and roam bot, enemy overextended"
- "🔄 RECALL: Reset now, TP top for herald fight"

### F6: Recall Timing
**Output Example:**
- "🏠 RECALL: 1250g - back for Mythic component, wave pushed"
- "🏠 STAY: Dragon in 30s, don't back yet"

### F7: Vision Coaching
**Output Example:**
- "👁️ WARD: River brush on cooldown in 15s, place for dragon"
- "👁️ SWEEP: Clear baron pit vision before setup"

### F8: Positioning Help
**Output Example:**
- "📍 POSITION: Stay behind tank, DPS backline"
- "📍 FOCUS: Target enemy ADC (low HP)"

---

## 5. Non-Functional Requirements

### 5.1 Performance
**Latency:**
- Screen capture: 500-1000ms/frame (1-2 FPS)
- OCR processing: <100ms per ROI
- API calls: <200ms
- LLM inference: <500ms
- UI update: <50ms
- **Total end-to-end latency: <500ms**

**Resource Usage:**
- CPU: <10% average (quad-core)
- RAM: <500MB
- GPU: Minimal (UI hardware acceleration)

**Game Performance Impact:**
- FPS reduction: <5%
- Input latency increase: <5ms

### 5.2 Reliability
- Uptime: 99%+ application uptime
- Graceful degradation to rule-based mode if APIs fail
- Retry logic for API calls (3 attempts, exponential backoff)
- Crash reporting (Sentry)

### 5.3 Security & Privacy
**Data Handling:**
- No persistent storage of screen captures (in-memory only)
- Riot API keys stored in OS keychain/credential manager
- LLM API keys encrypted at rest
- Postgres Row Level Security (RLS) for user data

**Security:**
- Code signing for executables
- Regular dependency scanning
- Secure HTTPS for all API calls

### 5.4 Compliance
**Riot Games ToS:**
- No automated gameplay
- No unfair advantage
- No cheating (no skillshot prediction, fog-of-war removal)
- All features must comply with Riot's third-party application guidelines

---

## 6. Technical Stack

### 6.1 Backend Service (Real-time)
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Libraries:**
  - OpenCV (cv2): Screen capture, image processing
  - Tesseract/EasyOCR: OCR engine
  - aiohttp: Async HTTP client (Riot API)
  - Anthropic SDK: Claude API
  - OpenAI SDK: GPT-4 API (fallback)
  - pydantic: Data validation, settings
  - loguru: Logging

### 6.2 Frontend UI
- **Framework:** Electron 28+
- **UI Library:** React 18+ (TypeScript)
- **State Management:** Zustand
- **Styling:** TailwindCSS
- **Build Tool:** Vite

### 6.3 AI/ML Infrastructure
- **Primary:** Anthropic Claude 3.5 Sonnet
- **Fallback:** OpenAI GPT-4 Turbo
- **Response Caching:** LRU cache (1000 entries)

### 6.4 Infrastructure & DevOps
- **Version Control:** Git + GitHub
- **CI/CD:** GitHub Actions
- **Testing:** pytest (Backend), Jest (Frontend), Playwright (E2E)
- **Distribution:** GitHub Releases, electron-updater
- **Crash Reporting:** Sentry
- **Analytics:** PostHog

### 6.5 User Data & Auth (Phase 3+)
- **Platform:** Supabase
- **Database:** Postgres
- **Authentication:** Supabase Auth
- **Client Libs:** supabase-js, supabase-py

### 6.6 Platform-Specific Implementation
**Windows:**
- Capture: Windows Graphics Capture API
- Installer: NSIS / WiX
- Signing: Microsoft Authenticode

**macOS:**
- Capture: CGWindowListCreateImage
- Installer: DMG
- Signing: Apple Developer ID + Notarization

**Linux:**
- Capture: X11 (xlib) / Wayland
- Installer: AppImage, .deb/.rpm

---

## 7. Phased Implementation Plan

### 7.1 Phase 1: MVP Task List
**Foundation & Setup:**
- [ ] Init repo, CI/CD pipeline, dev environment
- [ ] Implement basic screen capture (Windows only)
- [ ] Implement Riot API client (spectator, summoner endpoints)
- [ ] Define pydantic data models for game state

**Core Processing:**
- [ ] Implement OCR for gold, CS, HP/mana
- [ ] Build game state aggregation service
- [ ] Build rule-based engine (F1: Safety Warnings)

**UI & Integration:**
- [ ] Build Electron overlay (frameless, transparent, click-through)
- [ ] Establish WebSocket link (FastAPI <-> React)
- [ ] Build basic settings panel

**LLM Integration:**
- [ ] Integrate Anthropic SDK
- [ ] Develop prompt template for F2 (Wave Management)
- [ ] Develop prompt template for F4 (Objective Coaching)

**MVP Target:** F1 (Rule-based), F2 (LLM), F4 (LLM) on Windows

### 7.2 Phase 2: Core Feature Expansion
- [ ] macOS/Linux screen capture
- [ ] Advanced minimap analysis
- [ ] F3-F8 feature implementation
- [ ] Multi-model fallback system
- [ ] TTS for critical warnings

### 7.3 Phase 3: ML & Personalization
- [ ] Supabase Auth integration
- [ ] Match history database
- [ ] User behavior tracking
- [ ] Pattern recognition for mistakes
- [ ] Replay analysis tool
- [ ] Champion-specific coaching modules

---

## 8. Glossary
- **CS (Creep Score):** Minions/monsters killed
- **ROI (Region of Interest):** Specific screen area for analysis
- **OCR:** Optical Character Recognition
- **Minimap:** Small map in corner showing positions
- **Ward:** Vision-providing item
- **Objective:** Dragon, Baron, Herald, Tower
- **Recall:** Teleporting to base
- **RLS (Row Level Security):** Postgres feature for per-user data access
