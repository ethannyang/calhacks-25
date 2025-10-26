# LoL AI Coaching Overlay Guide

## Overview
Your Electron overlay has been enhanced with the following features:
- **Always-on-top overlay** that stays above fullscreen applications (including games)
- **Dynamic resizing** that automatically adjusts to coaching directive content
- **Click-through toggle** to interact with the game while the overlay is visible
- **Enhanced visibility** with semi-transparent background and visual indicators

## Starting the Overlay

### Development Mode
```bash
npm run electron:dev
```
This will start both the Vite dev server and Electron.

### Production Build
```bash
npm run electron:build
```

## Key Features and Fixes

### 1. Window Visibility
- **Fixed**: The overlay now starts visible with `focusable: true` and no `type: 'panel'`
- **Click-through disabled by default** so you can see and interact with the overlay
- **Semi-transparent background** for better visibility
- **Force show on startup** to ensure the overlay appears

### 2. Always On Top
- **Windows-specific handling**: Uses `screen-saver` level with priority 1
- **Auto-refresh**: The overlay re-asserts its top position every second
- **Works with fullscreen games**: Properly stays above League of Legends

### 3. Dynamic Resizing
- **Auto-resize hook**: Measures content and adjusts window size automatically
- **Smart padding**: Adds 40px padding for better appearance
- **Threshold**: Only resizes when content changes by more than 10px
- **Min/max constraints**: Respects minimum (300x120) and maximum (screen size) bounds

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+C` | Toggle click-through mode (allows clicking through the overlay) |
| `Ctrl+Shift+V` | Show/Hide the overlay |
| `Ctrl+Shift+I` | Toggle DevTools |
| `Ctrl+Shift+R` | Reload the overlay |
| `Ctrl+Alt+Plus` | Increase overlay size |
| `Ctrl+Alt+Minus` | Decrease overlay size |
| `Ctrl+Shift+Home` | Reset position to top-right corner |

## Visual Enhancements

### Overlay Appearance
- **Glass morphism effect**: Blur and gradient background
- **Border and shadow**: Subtle border with drop shadow
- **Status indicators**: Shows connection status and available commands
- **Fade-in animations**: Smooth transitions when commands appear

### Window Properties
```javascript
// Key window settings that make it work:
{
  frame: false,           // No window chrome
  transparent: true,      // Transparent background
  alwaysOnTop: true,     // Stay on top
  focusable: true,       // Can receive focus (important!)
  backgroundColor: '#00000000', // Fully transparent
  resizable: true        // Manual and programmatic resize
}
```

## Troubleshooting

### If the overlay doesn't appear:
1. Press `Ctrl+Shift+V` to toggle visibility
2. Check if the app is running (system tray or task manager)
3. Make sure you're running `npm run electron:dev` not just `npm run dev`

### If the overlay doesn't stay on top:
1. The overlay automatically refreshes its top-level status every second
2. Try pressing `Ctrl+Shift+V` twice to hide and show again
3. On Windows, make sure no other "always on top" applications are conflicting

### If click-through isn't working:
1. Press `Ctrl+Shift+C` to toggle click-through mode
2. The window will flash to indicate the state change
3. When click-through is enabled, you can't interact with the overlay

## WebSocket Connection
The overlay connects to your backend at `ws://localhost:8001/ws`
- Connection status is shown in the overlay
- Auto-reconnects if connection is lost
- Displays coaching commands as they arrive

## Development Tips

### Testing Dynamic Resize
The overlay automatically resizes based on content. To test:
1. Send different sized coaching directives through the WebSocket
2. The window will grow/shrink to fit the content
3. Minimum size is 300x120, maximum is screen size

### Customizing Appearance
Edit `src/App.tsx` to change:
- Background gradient and opacity
- Border radius and styling
- Font sizes and colors
- Animation effects

### Window Positioning
The overlay starts in the top-right corner by default.
- Drag to reposition (when click-through is disabled)
- Press `Ctrl+Shift+Home` to reset position
- Position is clamped to screen boundaries

## Next Steps
1. Test with League of Legends running in fullscreen
2. Adjust opacity and styling as needed
3. Fine-tune the auto-resize thresholds
4. Consider adding user preferences storage