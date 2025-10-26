/**
 * Electron Main Process
 * Transparent, always-on-top, click-through overlay window
 * Adds:
 *  - Bigger default size
 *  - Auto-resize support (renderer can send its preferred size)
 *  - Manual "set larger" helper + IPC
 */

const { app, BrowserWindow, screen, ipcMain, globalShortcut } = require('electron');
const path = require('path');

let mainWindow;
let isClickThrough = false;  // Start with click-through disabled so user can see the overlay

// ---- Auto-resize config ----
let autoResizeEnabled = true;         // can be toggled via IPC
const MIN_WIDTH = 300;        // Smaller minimum for better flexibility
const MIN_HEIGHT = 120;       // Smaller minimum height
// main.js
const START_WIDTH = 500;    // smaller width for overlay
const START_HEIGHT = 190;   // smaller height for overlay


// clamp window to the current work area (avoid going off-screen)
function clampToWorkArea(x, y, width, height) {
  const { workArea } = screen.getPrimaryDisplay();
  const clampedWidth = Math.min(width, workArea.width);
  const clampedHeight = Math.min(height, workArea.height);
  const clampedX = Math.min(Math.max(x, workArea.x), workArea.x + workArea.width - clampedWidth);
  const clampedY = Math.min(Math.max(y, workArea.y), workArea.y + workArea.height - clampedHeight);
  return { x: clampedX, y: clampedY, width: clampedWidth, height: clampedHeight };
}

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: waWidth, height: waHeight } = primaryDisplay.workAreaSize;

  // position near top-right by default
  const startBounds = clampToWorkArea(
    waWidth - (START_WIDTH + 20),
    20,
    START_WIDTH,
    START_HEIGHT
  );

  mainWindow = new BrowserWindow({
    width: startBounds.width,
    height: startBounds.height,
    x: startBounds.x,
    y: startBounds.y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,                  // allow manual resize (programmatic + OS edges if click-through disabled)
    useContentSize: true,             // sizing refers to webContents size
    hasShadow: false,                 // remove window shadow for better overlay appearance
    focusable: true,                  // Allow focus so the window can be interacted with
    // Remove type: 'panel' as it causes issues on Windows
    titleBarStyle: 'hidden',          // removes any remaining window chrome
    backgroundColor: '#00000000',     // Fully transparent background
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Minimum size safeguards
  mainWindow.setMinimumSize(MIN_WIDTH, MIN_HEIGHT);

  // Set window level to stay on top of fullscreen apps (including games)
  if (process.platform === 'win32') {
    // On Windows, we need to set the window to stay on top aggressively
    mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
    mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

    // Ensure window stays on top even when fullscreen apps are running
    setInterval(() => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
      }
    }, 1000);
  } else {
    // For macOS and Linux
    mainWindow.setAlwaysOnTop(true, 'floating', 1);
    mainWindow.setVisibleOnAllWorkspaces(true);
  }

  // Optional: zoom up a bit on HiDPI if desired
  // mainWindow.webContents.setZoomFactor(1.1);

  // Click-through configuration (starts disabled so overlay is visible)
  if (isClickThrough) {
    mainWindow.setIgnoreMouseEvents(true, { forward: true });
  } else {
    mainWindow.setIgnoreMouseEvents(false);
  }

  // Load the app
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools({ mode: 'detached' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Ensure window is visible after loading
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    // Flash the window briefly to indicate it's ready
    mainWindow.flashFrame(true);
    setTimeout(() => {
      if (mainWindow) mainWindow.flashFrame(false);
    }, 1000);
  });

  // Keep window on-screen if display metrics change (e.g., user changes resolution)
  screen.on('display-metrics-changed', () => {
    if (!mainWindow) return;
    const [x, y] = mainWindow.getPosition();
    const [w, h] = mainWindow.getSize();
    const bounds = clampToWorkArea(x, y, w, h);
    mainWindow.setBounds(bounds);
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  registerShortcuts();
}

/**
 * AUTO-RESIZE FLOW
 * - Renderer detects its own preferred content size (e.g., measure React root)
 * - Renderer sends: ipcRenderer.invoke('preferred-size', { width, height })
 * - Main clamps to MIN_* and workArea, then resizes.
 *
 * NOTE: Auto-resize respects `autoResizeEnabled`. Toggle via:
 * ipcRenderer.invoke('set-auto-resize', true|false)
 */

function applyPreferredSize({ width, height }) {
  if (!mainWindow) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const { workAreaSize } = primaryDisplay;

  const targetW = Math.max(MIN_WIDTH, Math.min(width, workAreaSize.width));
  const targetH = Math.max(MIN_HEIGHT, Math.min(height, workAreaSize.height));

  const [curX, curY] = mainWindow.getPosition();
  const bounds = clampToWorkArea(curX, curY, targetW, targetH);
  mainWindow.setBounds(bounds);
}

function registerShortcuts() {
  // Toggle click-through: Ctrl+Shift+C
  globalShortcut.register('CommandOrControl+Shift+C', () => {
    if (!mainWindow) return;
    isClickThrough = !isClickThrough;
    mainWindow.setIgnoreMouseEvents(isClickThrough, { forward: true });
    mainWindow.webContents.send('click-through-toggled', isClickThrough);
    console.log(`Click-through: ${isClickThrough ? 'enabled' : 'disabled'}`);

    // Flash frame to indicate state change
    mainWindow.flashFrame(true);
    setTimeout(() => mainWindow.flashFrame(false), 500);
  });

  // Toggle visibility: Ctrl+Shift+V (Show/Hide overlay)
  globalShortcut.register('CommandOrControl+Shift+V', () => {
    if (!mainWindow) return;
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
      mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
    }
  });

  // Toggle DevTools: Ctrl+Shift+I
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    if (mainWindow) mainWindow.webContents.toggleDevTools();
  });

  // Reload: Ctrl+Shift+R
  globalShortcut.register('CommandOrControl+Shift+R', () => {
    if (mainWindow) mainWindow.reload();
  });

  // Hot-grow size: Ctrl+Alt+=  (incrementally make window larger)
  globalShortcut.register('CommandOrControl+Alt+Plus', () => {
    if (!mainWindow) return;
    const [w, h] = mainWindow.getSize();
    const growW = w + 160;
    const growH = h + 80;
    const [x, y] = mainWindow.getPosition();
    const bounds = clampToWorkArea(x, y, growW, growH);
    mainWindow.setBounds(bounds);
  });

  // Hot-shrink size: Ctrl+Alt+-  (incrementally make window smaller)
  globalShortcut.register('CommandOrControl+Alt+Minus', () => {
    if (!mainWindow) return;
    const [w, h] = mainWindow.getSize();
    const shrinkW = Math.max(MIN_WIDTH, w - 160);
    const shrinkH = Math.max(MIN_HEIGHT, h - 80);
    const [x, y] = mainWindow.getPosition();
    const bounds = clampToWorkArea(x, y, shrinkW, shrinkH);
    mainWindow.setBounds(bounds);
  });

  // Reset position: Ctrl+Shift+Home (move to top-right corner)
  globalShortcut.register('CommandOrControl+Shift+Home', () => {
    if (!mainWindow) return;
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: waWidth } = primaryDisplay.workAreaSize;
    const [w, h] = mainWindow.getSize();
    const bounds = clampToWorkArea(waWidth - (w + 20), 20, w, h);
    mainWindow.setBounds(bounds);
  });
}

// ---------- IPC handlers ----------
ipcMain.handle('get-display-size', () => {
  const primaryDisplay = screen.getPrimaryDisplay();
  return primaryDisplay.workAreaSize;
});

ipcMain.handle('set-window-position', (event, x, y) => {
  if (mainWindow) {
    const [w, h] = mainWindow.getSize();
    const bounds = clampToWorkArea(x, y, w, h);
    mainWindow.setBounds(bounds);
  }
});

ipcMain.handle('set-window-size', (event, width, height) => {
  if (mainWindow) {
    applyPreferredSize({ width, height });
  }
});

// NEW: renderer can toggle auto-resize behavior
ipcMain.handle('set-auto-resize', (event, enabled) => {
  autoResizeEnabled = !!enabled;
  return { autoResizeEnabled };
});

// NEW: renderer can propose content size and we’ll resize if enabled
ipcMain.handle('preferred-size', (event, { width, height }) => {
  if (mainWindow && autoResizeEnabled && Number.isFinite(width) && Number.isFinite(height)) {
    applyPreferredSize({ width, height });
    return { applied: true };
  }
  return { applied: false, reason: autoResizeEnabled ? 'invalid-size' : 'auto-resize-disabled' };
});

// Optional: set opacity (existing)
ipcMain.handle('set-opacity', (event, opacity) => {
  if (mainWindow) {
    const clamped = Math.min(1, Math.max(0.1, opacity));
    mainWindow.setOpacity(clamped);
  }
});

// Force show the window and bring it to top
ipcMain.handle('force-show', () => {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
    mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
    mainWindow.flashFrame(true);
    setTimeout(() => {
      if (mainWindow) mainWindow.flashFrame(false);
    }, 1000);
  }
});

// Get window visibility state
ipcMain.handle('is-visible', () => {
  return mainWindow ? mainWindow.isVisible() : false;
});

// Toggle window visibility
ipcMain.handle('toggle-visibility', () => {
  if (!mainWindow) return false;
  if (mainWindow.isVisible()) {
    mainWindow.hide();
    return false;
  } else {
    mainWindow.show();
    mainWindow.focus();
    return true;
  }
});

// ---------- App lifecycle ----------
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  });
}
