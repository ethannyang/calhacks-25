/**
 * Electron Main Process
 * Creates transparent, always-on-top, click-through overlay window
 */

const { app, BrowserWindow, screen, ipcMain, globalShortcut } = require('electron');
const path = require('path');

let mainWindow;
let isClickThrough = false;  // Start with click-through disabled so window is more visible

function createWindow() {
  // Get primary display dimensions
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: 450,
    height: 200,
    x: width - 470,  // Position in top-right
    y: 20,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: false,  // Show in taskbar for now (easier to close during dev)
    resizable: true,
    visibleOnAllWorkspaces: true,  // Show on all spaces/desktops
    fullscreenable: false,  // Prevent fullscreen mode
    hasShadow: true,  // Add shadow to make window more visible
    opacity: 1.0,  // Full opacity initially
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Critical: Set highest window level to show over fullscreen apps/games
  // Try 'screen-saver' first (highest level), fallback to 'pop-up-menu' or 'floating'
  // Note: For true fullscreen games, this may not work - game needs to be in Borderless mode
  try {
    mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
  } catch (e) {
    console.warn('Could not set screen-saver level, trying pop-up-menu:', e);
    mainWindow.setAlwaysOnTop(true, 'pop-up-menu', 1);
  }
  mainWindow.setVisibleOnAllWorkspaces(true);

  // Periodically ensure window stays on top (every 2 seconds)
  setInterval(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      try {
        mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
      } catch (e) {
        mainWindow.setAlwaysOnTop(true, 'pop-up-menu', 1);
      }
      mainWindow.showInactive(); // Show without stealing focus
    }
  }, 2000);

  // Set click-through by default (can be toggled)
  if (isClickThrough) {
    mainWindow.setIgnoreMouseEvents(true, { forward: true });
  }

  // Load the app
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173');
    // Open DevTools in development
    // mainWindow.webContents.openDevTools({ mode: 'detached' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Handle window events
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Register global shortcuts
  registerShortcuts();
}

function registerShortcuts() {
  // Toggle click-through: Ctrl+Shift+C
  globalShortcut.register('CommandOrControl+Shift+C', () => {
    if (mainWindow) {
      isClickThrough = !isClickThrough;
      mainWindow.setIgnoreMouseEvents(isClickThrough, { forward: true });
      mainWindow.webContents.send('click-through-toggled', isClickThrough);
      console.log(`Click-through: ${isClickThrough ? 'enabled' : 'disabled'}`);
    }
  });

  // Toggle DevTools: Ctrl+Shift+I
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    if (mainWindow) {
      mainWindow.webContents.toggleDevTools();
    }
  });

  // Reload: Ctrl+Shift+R
  globalShortcut.register('CommandOrControl+Shift+R', () => {
    if (mainWindow) {
      mainWindow.reload();
    }
  });
}

// IPC handlers - must be set up before app.whenReady()
function setupIPCHandlers() {
  ipcMain.handle('get-display-size', () => {
    const primaryDisplay = screen.getPrimaryDisplay();
    return primaryDisplay.workAreaSize;
  });

  ipcMain.handle('set-window-position', (event, x, y) => {
    if (mainWindow) {
      mainWindow.setPosition(x, y);
    }
  });

  ipcMain.handle('set-window-size', (event, width, height) => {
    if (mainWindow) {
      mainWindow.setSize(width, height);
    }
  });

  ipcMain.handle('set-opacity', (event, opacity) => {
    if (mainWindow) {
      mainWindow.setOpacity(opacity);
    }
  });
}

// App lifecycle
app.whenReady().then(() => {
  setupIPCHandlers();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  // Unregister all shortcuts
  globalShortcut.unregisterAll();
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}
