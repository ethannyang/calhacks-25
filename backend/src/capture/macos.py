"""
macOS screen capture implementation using Quartz/CoreGraphics
Captures specific application windows
"""

import numpy as np
from typing import Optional, List
import Quartz
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID
from Quartz import CGWindowListCreateImage, CGRectNull, kCGWindowListOptionIncludingWindow
from Quartz import kCGWindowImageDefault
from Quartz import CoreGraphics
from PIL import Image
from loguru import logger

from .base import ScreenCapture, WindowInfo


class MacOSCapture(ScreenCapture):
    """macOS-specific screen capture using Quartz"""

    def list_windows(self) -> List[WindowInfo]:
        """List all available windows on macOS"""
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
        windows = []

        for window in window_list:
            window_id = window.get('kCGWindowNumber', 0)
            window_name = window.get('kCGWindowName', '')
            app_name = window.get('kCGWindowOwnerName', '')
            bounds = window.get('kCGWindowBounds', {})

            # Skip windows without names or from system processes
            if not app_name or not window_name:
                continue

            x = int(bounds.get('X', 0))
            y = int(bounds.get('Y', 0))
            width = int(bounds.get('Width', 0))
            height = int(bounds.get('Height', 0))

            # Skip tiny windows
            if width < 100 or height < 100:
                continue

            windows.append(WindowInfo(
                window_id=window_id,
                window_name=window_name,
                app_name=app_name,
                bounds=(x, y, width, height)
            ))

        return windows

    def find_game_window(self, window_name_pattern: str = "League of Legends") -> Optional[WindowInfo]:
        """Find the League of Legends game window"""
        windows = self.list_windows()

        # First try: exact match on app name
        for window in windows:
            if window_name_pattern.lower() in window.app_name.lower():
                logger.info(f"Found LoL window: {window.app_name} - {window.window_name}")
                return window

        # Second try: check window name
        for window in windows:
            if window_name_pattern.lower() in window.window_name.lower():
                logger.info(f"Found LoL window: {window.app_name} - {window.window_name}")
                return window

        # Third try: look for Riot Client or League Client
        for window in windows:
            if "riot" in window.app_name.lower() or "league" in window.app_name.lower():
                logger.info(f"Found potential LoL window: {window.app_name} - {window.window_name}")
                return window

        logger.warning("League of Legends window not found")
        logger.info(f"Available windows: {[(w.app_name, w.window_name) for w in windows[:10]]}")
        return None

    def capture_window(self, window_id: int) -> Optional[np.ndarray]:
        """
        Capture a specific window on macOS
        Returns BGR numpy array (OpenCV format) or None if capture fails
        """
        try:
            # Create image from window
            cg_image = CGWindowListCreateImage(
                CGRectNull,
                kCGWindowListOptionIncludingWindow,
                window_id,
                kCGWindowImageDefault
            )

            if not cg_image:
                logger.error(f"Failed to capture window {window_id}")
                return None

            # Get image dimensions
            width = CoreGraphics.CGImageGetWidth(cg_image)
            height = CoreGraphics.CGImageGetHeight(cg_image)

            if width == 0 or height == 0:
                logger.error(f"Invalid dimensions: {width}x{height}")
                return None

            # Create bitmap context
            bytes_per_row = width * 4
            color_space = CoreGraphics.CGColorSpaceCreateDeviceRGB()

            # Create bitmap data
            bitmap_data = bytearray(bytes_per_row * height)
            context = CoreGraphics.CGBitmapContextCreate(
                bitmap_data,
                width,
                height,
                8,
                bytes_per_row,
                color_space,
                CoreGraphics.kCGImageAlphaPremultipliedLast
            )

            if not context:
                logger.error("Failed to create bitmap context")
                return None

            # Draw image to context
            rect = CoreGraphics.CGRectMake(0, 0, width, height)
            CoreGraphics.CGContextDrawImage(context, rect, cg_image)

            # Convert to numpy array (RGBA)
            img_array = np.frombuffer(bitmap_data, dtype=np.uint8)
            img_array = img_array.reshape((height, width, 4))

            # Convert RGBA to BGR (OpenCV format)
            bgr_array = img_array[:, :, [2, 1, 0]].copy()

            logger.debug(f"Captured frame: {width}x{height}")
            return bgr_array

        except Exception as e:
            logger.error(f"Error capturing window: {e}")
            return None

    def capture_screen(self) -> Optional[np.ndarray]:
        """Capture the entire screen (fallback if window capture fails)"""
        try:
            # Capture main display
            cg_image = CoreGraphics.CGDisplayCreateImage(CoreGraphics.CGMainDisplayID())

            if not cg_image:
                logger.error("Failed to capture screen")
                return None

            width = CoreGraphics.CGImageGetWidth(cg_image)
            height = CoreGraphics.CGImageGetHeight(cg_image)

            # Create bitmap data
            bytes_per_row = width * 4
            bitmap_data = bytearray(bytes_per_row * height)
            color_space = CoreGraphics.CGColorSpaceCreateDeviceRGB()

            context = CoreGraphics.CGBitmapContextCreate(
                bitmap_data,
                width,
                height,
                8,
                bytes_per_row,
                color_space,
                CoreGraphics.kCGImageAlphaPremultipliedLast
            )

            rect = CoreGraphics.CGRectMake(0, 0, width, height)
            CoreGraphics.CGContextDrawImage(context, rect, cg_image)

            img_array = np.frombuffer(bitmap_data, dtype=np.uint8)
            img_array = img_array.reshape((height, width, 4))
            bgr_array = img_array[:, :, [2, 1, 0]].copy()

            return bgr_array

        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None


def get_capture() -> ScreenCapture:
    """Factory function to get macOS capture instance"""
    return MacOSCapture()
