"""
Windows screen capture implementation using MSS
Captures specific application windows
"""

import numpy as np
from typing import Optional, List
import mss
import ctypes
from ctypes import windll
from loguru import logger

try:
    import win32gui
    import win32ui
    import win32con
    import win32process
    import psutil
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("win32gui/psutil not available - window enumeration will be limited")

from .base import ScreenCapture, WindowInfo


class WindowsCapture(ScreenCapture):
    """Windows-specific screen capture using MSS and Win32 API"""

    def __init__(self):
        super().__init__()
        self.sct = mss.mss()

    def list_windows(self) -> List[WindowInfo]:
        """List all available windows on Windows"""
        if not HAS_WIN32:
            logger.warning("win32gui not available, cannot list windows")
            return []

        windows = []

        def enum_window_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)

                # Skip windows without titles
                if not window_text:
                    return

                try:
                    # Get window rectangle
                    rect = win32gui.GetWindowRect(hwnd)
                    x, y, x2, y2 = rect
                    width = x2 - x
                    height = y2 - y

                    # Skip tiny windows
                    if width < 100 or height < 100:
                        return

                    # Get process name (app name)
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        app_name = process.name()
                    except:
                        app_name = class_name

                    windows.append(WindowInfo(
                        window_id=hwnd,
                        window_name=window_text,
                        app_name=app_name,
                        bounds=(x, y, width, height)
                    ))
                except Exception as e:
                    logger.debug(f"Error processing window {hwnd}: {e}")

        win32gui.EnumWindows(enum_window_callback, windows)
        return windows

    def find_game_window(self, window_name_pattern: str = "League of Legends") -> Optional[WindowInfo]:
        """
        Find the League of Legends game window
        Prioritizes the actual game window over the client launcher
        """
        windows = self.list_windows()

        # Priority 1: Look for the actual game executable (League of Legends.exe)
        # This is the in-game window, not the launcher
        for window in windows:
            if window.app_name.lower() == "league of legends.exe":
                logger.info(f"Found LoL game window: {window.app_name} - {window.window_name}")
                return window

        # Priority 2: Look for window title containing "League of Legends (TM) Client"
        # This usually indicates the actual game window
        for window in windows:
            if "(tm) client" in window.window_name.lower() and "league" in window.window_name.lower():
                logger.info(f"Found LoL game window: {window.app_name} - {window.window_name}")
                return window

        # Priority 3: Look for any "League of Legends" in window name (excluding launcher)
        for window in windows:
            if "league of legends" in window.window_name.lower() and "leagueclientux" not in window.app_name.lower():
                logger.info(f"Found LoL window: {window.app_name} - {window.window_name}")
                return window

        # Priority 4: Fallback to launcher (LeagueClientUx.exe) if game not running
        for window in windows:
            if "leagueclientux" in window.app_name.lower():
                logger.info(f"Found LoL launcher (game not running): {window.app_name} - {window.window_name}")
                return window

        # Priority 5: Any window with Riot or League in the name
        for window in windows:
            if "riot" in window.app_name.lower() or "league" in window.app_name.lower():
                logger.info(f"Found potential LoL window: {window.app_name} - {window.window_name}")
                return window

        logger.warning("League of Legends window not found")
        logger.info(f"Available windows: {[(w.app_name, w.window_name) for w in windows[:10]]}")
        return None

    def capture_window(self, window_id: int) -> Optional[np.ndarray]:
        """
        Capture a specific window on Windows using PrintWindow API
        This captures the actual window content, not just the screen region
        Returns BGR numpy array (OpenCV format) or None if capture fails
        """
        try:
            if not HAS_WIN32:
                logger.error("win32gui not available, cannot capture window")
                return None

            # Get window dimensions from client area
            left, top, right, bottom = win32gui.GetClientRect(window_id)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                logger.error(f"Invalid window dimensions: {width}x{height}")
                return None

            # Create device contexts
            hwndDC = win32gui.GetWindowDC(window_id)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # Capture the window using PrintWindow via ctypes (captures actual window content)
            # PW_CLIENTONLY (0x1) | PW_RENDERFULLCONTENT (0x2) = 0x3
            result = windll.user32.PrintWindow(window_id, saveDC.GetSafeHdc(), 0x3)

            if result == 0:
                logger.warning("PrintWindow failed, falling back to BitBlt")
                # Fallback to BitBlt if PrintWindow fails
                saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype=np.uint8)
            img = img.reshape((height, width, 4))

            # Convert BGRA to BGR (remove alpha channel)
            bgr_array = img[:, :, :3].copy()

            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(window_id, hwndDC)

            logger.debug(f"Captured window content: {width}x{height}")
            return bgr_array

        except Exception as e:
            logger.error(f"Error capturing window: {e}")
            # Cleanup on error
            try:
                if 'saveBitMap' in locals():
                    win32gui.DeleteObject(saveBitMap.GetHandle())
                if 'saveDC' in locals():
                    saveDC.DeleteDC()
                if 'mfcDC' in locals():
                    mfcDC.DeleteDC()
                if 'hwndDC' in locals() and 'window_id' in locals():
                    win32gui.ReleaseDC(window_id, hwndDC)
            except:
                pass
            return None

    def capture_screen(self) -> Optional[np.ndarray]:
        """Capture the entire primary screen"""
        try:
            # Capture the primary monitor
            monitor = self.sct.monitors[1]  # Index 1 is primary monitor
            screenshot = self.sct.grab(monitor)

            # Convert to numpy array
            img = np.array(screenshot)

            # MSS returns BGRA, convert to BGR
            if img.shape[2] == 4:
                img = img[:, :, :3]

            # Convert RGB to BGR
            bgr_array = img[:, :, [2, 1, 0]].copy()

            return bgr_array

        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None

    def __del__(self):
        """Cleanup MSS instance"""
        if hasattr(self, 'sct'):
            self.sct.close()


def get_capture() -> ScreenCapture:
    """Factory function to get Windows capture instance"""
    return WindowsCapture()
