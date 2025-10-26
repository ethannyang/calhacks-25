#!/bin/bash

# Test script for voice input debugging
# This script tests if the ` key is being detected and if voice streaming works

echo "=========================================="
echo "🎤 Voice Input Test Script"
echo "=========================================="
echo ""

# Check if Electron is running
ELECTRON_PID=$(ps aux | grep "Electron\.app/Contents/MacOS/Electron" | grep -v "Riot\|Cursor\|crashpad\|grep" | awk '{print $2}' | head -1)

if [ -z "$ELECTRON_PID" ]; then
    echo "❌ Electron overlay is not running!"
    echo "   Start it with: cd frontend && npm start"
    exit 1
else
    echo "✅ Electron overlay is running (PID: $ELECTRON_PID)"
fi

# Check if backend is running
BACKEND_PID=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$BACKEND_PID" ]; then
    echo "❌ Backend is not running!"
    echo "   Backend is needed for voice commands"
else
    echo "✅ Backend is running (PID: $BACKEND_PID)"
fi

# Check WebSocket connection
echo ""
echo "📡 Checking WebSocket connection..."
sleep 1
BACKEND_LOG="/Users/ethan/Desktop/projects/calhacks-25/backend/backend.log"
if [ -f "$BACKEND_LOG" ]; then
    WS_CONNECTIONS=$(grep -c "Client connected" "$BACKEND_LOG" 2>/dev/null || echo "0")
    echo "   WebSocket connections: $WS_CONNECTIONS"
else
    echo "   ⚠️  Backend log not found"
fi

# Check for keyboard monitoring
echo ""
echo "⌨️  Testing keyboard monitoring..."
echo "   Looking for uiohook/keyboard messages in logs..."
FRONTEND_LOG="/Users/ethan/Desktop/projects/calhacks-25/frontend/frontend.log"
if [ -f "$FRONTEND_LOG" ]; then
    KEYBOARD_MSGS=$(tail -100 "$FRONTEND_LOG" 2>/dev/null | grep -i "keyboard\|voice\|grave" | tail -5)
    if [ -z "$KEYBOARD_MSGS" ]; then
        echo "   ⚠️  No keyboard monitoring messages found"
    else
        echo "$KEYBOARD_MSGS"
    fi
fi

# Check if uiohook-napi module exists
echo ""
echo "📦 Checking uiohook-napi module..."
UIOHOOK_PATH="/Users/ethan/Desktop/projects/calhacks-25/frontend/node_modules/uiohook-napi"
if [ -d "$UIOHOOK_PATH" ]; then
    echo "   ✅ uiohook-napi is installed"
else
    echo "   ❌ uiohook-napi is NOT installed!"
    echo "   Run: cd frontend && npm install uiohook-napi"
fi

# Interactive test
echo ""
echo "=========================================="
echo "🧪 INTERACTIVE TEST"
echo "=========================================="
echo ""
echo "Instructions:"
echo "1. Make sure the overlay window is visible"
echo "2. Press and HOLD the \` key (grave accent, above Tab)"
echo "3. While holding, say: \"Garen used Q\""
echo "4. Release the \` key"
echo ""
echo "Watch the overlay for:"
echo "  - Red 'LISTENING...' indicator should appear when you hold \`"
echo "  - Your speech should be transcribed"
echo "  - A green confirmation should appear"
echo ""
echo "📊 Monitoring backend for voice commands (Ctrl+C to stop)..."
echo ""

# Tail backend log for voice-related messages
if [ -f "$BACKEND_LOG" ]; then
    tail -f "$BACKEND_LOG" | grep --line-buffered -i "voice\|ability\|websocket.*ability\|ability_used"
else
    echo "❌ Backend log not found at: $BACKEND_LOG"
    echo "   Cannot monitor voice commands"
fi
