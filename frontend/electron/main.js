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
let isClickThrough = true;  // Always true for overlay mode

// ---- Auto-resize config ----
let autoResizeEnabled = true;         // can be toggled via IPC
const MIN_WIDTH = 900;
const MIN_HEIGHT = 360;
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
    focusable: false,                 // prevent the window from taking focus
    type: 'panel',                    // makes it a true overlay window
    titleBarStyle: 'hidden',          // removes any remaining window chrome
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Minimum size safeguards
  mainWindow.setMinimumSize(MIN_WIDTH, MIN_HEIGHT);

  // Optional: zoom up a bit on HiDPI if desired
  // mainWindow.webContents.setZoomFactor(1.1);

  // Click-through by default (toggle with shortcut)
  if (isClickThrough) {
    mainWindow.setIgnoreMouseEvents(true, { forward: true });
  }

  // Load the app
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
    // mainWindow.webContents.openDevTools({ mode: 'detached' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

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
