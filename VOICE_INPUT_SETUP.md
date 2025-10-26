# Voice Input Setup Guide

This guide explains how to set up and use the cloud-based voice recognition system for ability tracking.

## Why Cloud ASR?

**The Web Speech API doesn't work in Electron** because Chromium's speech backend requires Google API keys that aren't shipped with Electron. You'll see `SpeechRecognitionErrorEvent { error: 'network' }` - the API exists but immediately fails.

This implementation uses **Deepgram** (cloud ASR) with AudioWorklet streaming for:
- ✅ **Low latency**: ~300ms (faster than Web Speech API)
- ✅ **Live transcription**: See partial results as you speak
- ✅ **Better accuracy**: Gaming vocabulary boosting (Q, W, E, R, Flash, etc.)
- ✅ **Actually works in Electron**

## Architecture

```
[T key pressed] → Electron captures mic
                → AudioWorklet resamples to 16kHz PCM (20ms frames)
                → WebSocket to local proxy (ws://localhost:8787)
                → Proxy authenticates + forwards to Deepgram
                → Partial/final transcripts flow back
                → Frontend parses abilities and sends to backend
```

---

## Setup Instructions

### 1. Get Deepgram API Key

1. Sign up at https://deepgram.com (free tier: $200 credit, ~46,000 minutes)
2. Go to **API Keys** in console
3. Create a new API key
4. Copy the key (starts with something like `abc123...`)

### 2. Add API Key to Environment

Create or update your `.env` file in the **backend** directory:

```bash
# backend/.env
DEEPGRAM_API_KEY=your_api_key_here
```

**IMPORTANT:** Never commit this file to git. Add it to `.gitignore`.

### 3. Install Node.js Dependencies for Proxy

The voice proxy is a Node.js server (separate from your Python backend). Install dependencies:

```bash
cd backend

# Option A: Use the package.json
mv voice-proxy-package.json package.json
npm install

# Option B: Install dependencies manually
npm install ws dotenv
```

### 4. Start the Voice Proxy Server

In a **separate terminal** (keep this running):

```bash
cd backend
node voice_proxy.js
```

You should see:
```
🎤 Voice proxy server starting on port 8787...
✅ Voice proxy server listening on http://localhost:8787
   WebSocket endpoint: ws://localhost:8787/stt
   Deepgram API key: abc123...
```

**Keep this terminal running** while using voice input.

### 5. Start Your Electron App

In another terminal:

```bash
cd frontend
npm run electron:dev
```

### 6. Test Voice Input

1. Press and hold **T** key
2. Say an ability: "Garen Q", "flash", "enemy W", etc.
3. You should see:
   - **LISTENING...** indicator
   - Live transcript in quotes (interim results)
   - Green confirmation when command is recognized

---

## How It Works

### Files Created

1. **`frontend/public/pcm-resampler-worklet.js`**
   - AudioWorklet processor
   - Converts mic input (48kHz) → 16kHz PCM (what Deepgram expects)
   - Sends 20ms frames for low latency

2. **`frontend/src/services/voiceStreaming.ts`**
   - Voice streaming client
   - Manages mic, AudioWorklet, WebSocket connection
   - Replaces Web Speech API

3. **`backend/voice_proxy.js`**
   - WebSocket proxy server
   - Keeps API key secure (never exposed to renderer)
   - Authenticates with Deepgram
   - Forwards audio frames and transcripts

4. **`frontend/src/components/VoiceInput.tsx`** (updated)
   - Uses new `voiceStreamingService` instead of Web Speech API
   - Shows live interim transcripts
   - Same ability parsing logic

### Audio Pipeline

```
getUserMedia (48kHz)
  → AudioContext
    → MediaStreamSource
      → AudioWorkletNode (pcm-resampler)
        → 16kHz PCM frames (20ms each)
          → WebSocket (binary)
            → Proxy forwards to Deepgram
              → Transcripts come back (partial/final)
                → Frontend displays + parses abilities
```

---

## Troubleshooting

### "Cannot connect to voice service"

**Problem:** Voice proxy server isn't running.

**Solution:**
```bash
cd backend
node voice_proxy.js
```

### "Microphone permission denied"

**Problem:** Electron doesn't have mic access.

**Solution (macOS):**
1. System Settings → Privacy & Security → Microphone
2. Enable for Terminal (if running from terminal) or your Electron app
3. Restart Electron app

**Note:** `main.js:91-98` already has permission handler set up.

### "DEEPGRAM_API_KEY not found"

**Problem:** `.env` file missing or not loaded.

**Solution:**
```bash
cd backend
echo "DEEPGRAM_API_KEY=your_key_here" > .env
```

### Audio not streaming

**Check:**
1. Open browser DevTools in Electron: `Cmd+Shift+I`
2. Look for console messages:
   - `[VoiceStreaming] Starting audio streaming...`
   - `[VoiceStreaming] WebSocket connected`
   - `[PCM Resampler] Initialized`
3. Check proxy server terminal for:
   - `📱 Client connected`
   - `🎧 Format configured`
   - `✅ Deepgram connected`

### Poor recognition accuracy

**Deepgram already has keyword boosting for abilities** (see `voice_proxy.js:132`):
```js
keywords: 'Q:2,W:2,E:2,R:2,flash:2,ignite:2'
```

To add more keywords, edit the `keywords` parameter in `buildDeepgramUrl()`.

### High latency

Current settings optimize for low latency:
- `endpointing: 300` - Wait 300ms of silence before finalizing
- `interim_results: true` - Show partial transcripts immediately
- 20ms audio frames - Minimal buffering

To make it even faster, reduce endpointing to 200ms (but may cut off words).

---

## Cost Estimates

Deepgram pricing: **$0.0043/minute** for Nova-2 model

- 1 hour of gaming: **$0.26**
- 10 hours: **$2.58**
- 100 hours: **$25.80**

Free tier gives you **$200 credit** = ~46,000 minutes (766 hours).

For comparison:
- AssemblyAI: $0.00025/min (cheaper, higher latency)
- Azure: $0.024/min (10x more expensive)
- OpenAI Whisper: $0.006/min (not streaming, file-based only)

---

## Advanced Configuration

### Change ASR Provider

To use a different provider (AssemblyAI, Azure, etc.), edit `voice_proxy.js`:

1. Change WebSocket URL in `buildDeepgramUrl()`
2. Update authentication headers
3. Map response format (each provider has different JSON structure)

### Adjust Audio Quality

Edit `voiceStreaming.ts:48-53`:
```typescript
audio: {
  channelCount: 1,
  sampleRate: 48000, // Higher = better quality, more bandwidth
  echoCancellation: true,
  noiseSuppression: true, // Reduces background noise
  autoGainControl: true, // Normalizes volume
}
```

### Run Proxy in Electron Main Process

Instead of separate Node server, you can run the proxy inside Electron's main process. Add to `main.js`:

```js
const { startVoiceProxy } = require('../backend/voice_proxy.js');

app.whenReady().then(() => {
  // ... existing code
  startVoiceProxy(); // Start proxy on port 8787
});
```

---

## Testing Checklist

- [ ] Deepgram API key added to `.env`
- [ ] Voice proxy server running (`node voice_proxy.js`)
- [ ] Electron app started (`npm run electron:dev`)
- [ ] Microphone permission granted
- [ ] Press T → see "LISTENING..." indicator
- [ ] Say "Q" → see live transcript
- [ ] Release T → see green confirmation
- [ ] Check backend receives `ability_used` message

---

## Next Steps

1. **Get API key** from Deepgram
2. **Start proxy server**: `cd backend && node voice_proxy.js`
3. **Test** by holding T and speaking abilities
4. **Monitor** console logs in both Electron and proxy server
5. **Iterate** on keyword boosting for better accuracy

If you have any issues, check the console output in:
- Electron DevTools (`Cmd+Shift+I`)
- Voice proxy terminal
- Backend Python server

Good luck! 🎮🎤
