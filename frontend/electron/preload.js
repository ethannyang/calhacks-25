/**
 * Electron Preload Script
 * Exposes safe IPC methods to renderer process
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  // Display and window control
  getDisplaySize: () => ipcRenderer.invoke('get-display-size'),
  setWindowPosition: (x, y) => ipcRenderer.invoke('set-window-position', x, y),
  setWindowSize: (width, height) => ipcRenderer.invoke('set-window-size', width, height),
  setOpacity: (opacity) => ipcRenderer.invoke('set-opacity', opacity),

  // Event listeners
  onClickThroughToggled: (callback) => {
    ipcRenderer.on('click-through-toggled', (event, isEnabled) => callback(isEnabled));
  },
});
