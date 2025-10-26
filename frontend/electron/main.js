/**
 * Electron Main Process
 * Creates transparent, always-on-top, click-through overlay window
 */

const { app, BrowserWindow, screen, ipcMain, globalShortcut } = require('electron');
const path = require('path');
const { uIOhook, UiohookKey } = require('uiohook-napi');

let mainWindow;
let isClickThrough = true;  // Enable click-through by default so it doesn't interfere with game
let isVoiceInputActive = false;  // Track voice input state

// Handle EPIPE errors gracefully to prevent app crashes
process.on('uncaughtException', (error) => {
  if (error.code === 'EPIPE') {
    // Ignore EPIPE errors from console.log
    return;
  }
  // Log other errors but don't crash
  console.error('Uncaught exception:', error);
});

// Safe console logging wrapper
function safeLog(...args) {
  try {
    console.log(...args);
  } catch (e) {
    // Silently ignore console errors
  }
}

function createWindow() {
  // Get primary display dimensions
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: 500,
    height: 300,
    x: width - 520,  // Position in top-right (20px from right edge)
    y: 20,  // 20px from top
    frame: false,  // Frameless for cleaner overlay look
    transparent: true,  // Enable transparency for translucent effect
    alwaysOnTop: true,
    skipTaskbar: false,  // Show in taskbar for now (easier to close during dev)
    resizable: true,
    visibleOnAllWorkspaces: true,  // Show on all spaces/desktops
    fullscreenable: false,  // Prevent fullscreen mode
    hasShadow: true,  // Add shadow to make window more visible
    opacity: 0.95,  // Slightly translucent (95% opacity)
    backgroundColor: '#00000000',  // Transparent background
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      // Enable media access for speech recognition
      enableRemoteModule: false,
      sandbox: false,  // Disable sandbox to allow speech API
    }
  });

  // Critical: Set highest window level to show over fullscreen apps/games
  // Try 'screen-saver' first (highest level), fallback to 'pop-up-menu' or 'floating'
  // Note: For true fullscreen games, this may not work - game needs to be in Borderless mode
  try {
    mainWindow.setAlwaysOnTop(true, 'screen-saver', 1);
  } catch (e) {
    safeLog('Could not set screen-saver level, trying pop-up-menu:', e);
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

  // Grant permission for media devices (microphone for speech recognition)
  mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      // Approve microphone access for speech recognition
      callback(true);
    } else {
      callback(false);
    }
  });

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
      safeLog(`Click-through: ${isClickThrough ? 'enabled' : 'disabled'}`);
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

function setupKeyboardMonitoring() {
  // Monitor ~ (Grave/Tilde) key for toggle voice input
  // Key code 41 = ` key (the key above Tab, left of 1)
  const GRAVE_KEY_CODE = 41;
  let lastToggleTime = 0;
  const DEBOUNCE_MS = 300; // Ignore events within 300ms of each other

  uIOhook.on('keydown', (e) => {
    // ~ key (Grave accent) - using actual key code since UiohookKey.Grave is undefined
    if (e.keycode === GRAVE_KEY_CODE) {
      const now = Date.now();

      // Ignore rapid repeated keydown events (key repeat while holding)
      if (now - lastToggleTime < DEBOUNCE_MS) {
        return;
      }
      lastToggleTime = now;

      // Toggle voice input on/off
      isVoiceInputActive = !isVoiceInputActive;

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('voice-input-toggle', isVoiceInputActive);
      }

      safeLog(`Voice input ${isVoiceInputActive ? 'activated' : 'deactivated'} (toggle)`);
    }
  });

  // Start the keyboard hook
  uIOhook.start();
  safeLog('Keyboard monitoring started (` key = code 41 to toggle voice input)');
}

// Enable features for speech recognition
app.commandLine.appendSwitch('enable-speech-input');
app.commandLine.appendSwitch('enable-web-speech-api');
// Allow insecure content for development (needed for Speech API in some cases)
app.commandLine.appendSwitch('allow-insecure-localhost', 'true');
// Ensure audio input is allowed
app.commandLine.appendSwitch('enable-features', 'AudioServiceOutOfProcess');

// App lifecycle
app.whenReady().then(() => {
  setupIPCHandlers();
  createWindow();
  setupKeyboardMonitoring();

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
  // Unregister all shortcuts (only if app was ready)
  if (app.isReady()) {
    globalShortcut.unregisterAll();
  }

  // Stop keyboard monitoring
  try {
    uIOhook.stop();
    safeLog('Keyboard monitoring stopped');
  } catch (e) {
    safeLog('Error stopping keyboard monitoring:', e);
  }
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
