/// <reference types="vite/client" />

interface Window {
  electron?: {
    getDisplaySize: () => Promise<{ width: number; height: number }>;
    setWindowPosition: (x: number, y: number) => Promise<void>;
    setWindowSize: (width: number, height: number) => Promise<void>;
    setOpacity: (opacity: number) => Promise<void>;
    forceShow: () => Promise<void>;
    isVisible: () => Promise<boolean>;
    toggleVisibility: () => Promise<boolean>;
    setAutoResize: (enabled: boolean) => Promise<{ autoResizeEnabled: boolean }>;
    setPreferredSize: (width: number, height: number) => Promise<{ applied: boolean; reason?: string }>;
    onClickThroughToggled: (callback: (isEnabled: boolean) => void) => void;
  };
}
