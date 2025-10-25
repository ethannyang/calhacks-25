# macOS Setup Guide

## Screen Recording Permissions

On macOS, apps need explicit permission to capture the screen. You need to grant permission to **Terminal** (or whatever terminal app you're using).

### Steps to Grant Permission:

1. Open **System Settings** (System Preferences on older macOS)
2. Go to **Privacy & Security**
3. Click **Screen Recording** (or **Screen & System Audio Recording**)
4. Click the **lock icon** to make changes (enter your password)
5. Find and enable **Terminal** (or iTerm, VS Code, etc.)
6. **Restart your terminal application** for changes to take effect

### Verifying Permissions

Run the test script to verify screen capture works:

```bash
cd backend
python3 test_capture.py
```

If permissions are working, you should see a list of open windows. If you only see 1-2 windows (like Dock), permissions may not be granted yet.

## Testing Screen Capture

### Without League of Legends

You can test screen capture with any other window:

```bash
python3 test_capture.py
```

When prompted, select `y` to test with another window, then choose a window number from the list.

This will create `test_capture.png` if capture is working.

### With League of Legends

1. Launch League of Legends and start a game (Practice Tool is easiest)
2. Run the test script:
```bash
python3 test_capture.py
```

If LoL is detected, it will:
- Capture the game window
- Extract ROIs (gold, CS, HP/mana, minimap, etc.)
- Save images for inspection

Check these files:
- `captured_frame.png` - Full game window capture
- `roi_gold.png` - Gold counter area
- `roi_cs.png` - CS counter area
- `roi_player_hp.png` - HP bar area
- `roi_player_mana.png` - Mana bar area
- `roi_minimap.png` - Minimap area
- `roi_game_time.png` - Game timer area

## Common Issues

### "Only 1 window found"
- Screen recording permissions not granted
- Terminal app needs to be restarted after granting permissions

### "League of Legends window not found"
- Make sure LoL is running (in-game, not just client)
- Try during an actual game or Practice Tool
- The test script will show all available windows

### "Failed to capture window"
- Some apps block screen capture for security
- Try with a different window to verify capture works

## Next Steps

Once screen capture is working:

1. **Test with Live Game**: Play a League game with the test script running
2. **Verify OCR**: Check if gold, CS, and timer can be read from the ROI images
3. **Full Pipeline**: Integrate into main backend service
4. **Real-time Coaching**: Start receiving AI coaching commands in the overlay!

## Dependencies Installed

- `pyobjc-framework-Quartz` - macOS screen capture APIs
- `opencv-python` - Image processing
- `pytesseract` - OCR for text extraction
- `easyocr` - Fallback OCR system

## Performance Notes

- Screen capture runs at **1-2 FPS** (configurable in .env)
- Target **<5% CPU usage**
- ROI extraction is fast (<10ms)
- OCR processing takes 50-200ms per ROI
- Total latency target: **<500ms** from capture to coaching command
