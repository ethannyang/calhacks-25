# 🧠 Souma — Real-Time AI League of Legends Coach

> “Don’t just play League — learn it while you play.”

Souma is an **AI-powered real-time coaching overlay** for *League of Legends*.  
It analyzes your live in-game state and provides **specific, actionable advice** — helping players improve their game sense, mechanics, and decision-making while they play.

---

## 🌟 Inspiration

Most existing League tools only help *before* or *after* your game — with builds, stats, or post-match reviews.  
But what about **during** the match, when decisions matter most?

League has an incredibly high skill floor — both strategically and mechanically.  
Many players give up before learning how to actually enjoy the game.  

So we asked:  
> What if an AI coach could guide you live, teaching better habits and strategy in real time?

That’s how **Souma** was born.

---

## ⚙️ What It Does

Souma watches your gameplay and reacts just like a live coach would.  
It reads your **health, mana, gold, items, minimap state, and lane conditions**, and gives guidance like:

- 🩸 *“Back — low HP, enemy jungler nearby.”*  
- 💰 *“Recall now — major item spike available.”*  
- 🧠 *“Freeze the wave under tower.”*  
- 🗺️ *“Rotate to dragon — 30 seconds to spawn.”*  

This helps players **build instincts** and **learn strategy faster**, turning frustration into confidence and wins.

---

## 🏗️ How It Works

### 🔧 Backend
- **FastAPI** — Asynchronous API backend for real-time data processing.  
- **OpenCV** — Captures game frames and extracts ROIs (health bar, mana, gold, minimap).  
- **Tesseract / EasyOCR** — Optical character recognition for reading in-game text.  
- **Riot API Client** — Fetches live match data (rate-limited).

### 🧠 AI Engines
- **Rule Engine (F1, F6)** — For deterministic events like low-health alerts and recall timing.  
- **LLM Engine (F2, F4)** — For reasoning-based advice such as wave management and objective control.  

### 🖥️ Frontend
- **Electron + React + TypeScript** — Cross-platform overlay interface.  
- **Zustand** — Lightweight state management.  
- **TailwindCSS** — Clean and adaptive styling.  
- **WebSocket** — Real-time connection between backend and overlay.

---

## 🧩 Challenges

- Building stable **image processing** for a live, animated game environment was a huge challenge.  
- **Audio synchronization** for abilities and cues was complex to crossmatch in real time.  
- Integrating **voice input → LLM** interactions took multiple rewrites, but it made the coach feel truly alive.

---

## 🏆 Accomplishments

- Developed a **working live computer vision pipeline** for League of Legends.  
- Implemented **ROI-specific logic** for gold, health, mana, and minimap awareness.  
- Built an AI that **prioritizes coaching advice** intelligently (e.g., safety > objectives > wave control).  
- Watching Souma *call out a gank before it happened* was an unforgettable moment.

---

## 💡 What I Learned

- **Never give up.** Debugging real-time systems tests patience like nothing else.  
- **Image processing for AI in games** still has huge room to grow.  
- **Audio-visual fusion** is key to capturing complex game states.  
- **Voice-driven LLM input** opens up new frontiers for interactive, adaptive AI experiences.

---

## 🚀 Next Steps

- 🧩 Champion-specific advice modules (e.g., different coaching for Garen vs. Fiora).  
- 🔊 Real-time audio feedback from the AI coach.  
- 🧠 Personalized learning paths based on player history.  
- 🕹️ Expand to other esports titles (Dota, Valorant, etc.).

---

## ⚡ Running Locally

### Clone & Install
```bash
git clone https://github.com/yourname/souma.git
cd souma
npm install
