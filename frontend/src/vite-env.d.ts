/// <reference types="vite/client" />

interface Window {
  electron?: {
    getDisplaySize: () => Promise<{ width: number; height: number }>;
    setWindowPosition: (x: number, y: number) => Promise<void>;
    setWindowSize: (width: number, height: number) => Promise<void>;
    setOpacity: (opacity: number) => Promise<void>;
    onClickThroughToggled: (callback: (isEnabled: boolean) => void) => void;
  };
}
