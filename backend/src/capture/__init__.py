"""
Screen capture module for League of Legends game window
Automatically selects the appropriate platform-specific implementation
"""

import sys
from typing import Optional
from loguru import logger

from .base import ScreenCapture, WindowInfo, ROI


def get_capture() -> ScreenCapture:
    """
    Factory function to get the appropriate screen capture implementation
    based on the current platform.

    Returns:
        ScreenCapture: Platform-specific screen capture instance

    Raises:
        NotImplementedError: If the current platform is not supported
    """
    platform = sys.platform

    if platform == "darwin":  # macOS
        logger.info("Using macOS screen capture")
        from .macos import get_capture as get_macos_capture
        return get_macos_capture()

    elif platform == "win32":  # Windows
        logger.info("Using Windows screen capture")
        from .windows import get_capture as get_windows_capture
        return get_windows_capture()

    elif platform.startswith("linux"):  # Linux
        logger.error("Linux screen capture not yet implemented")
        raise NotImplementedError("Linux screen capture is not yet implemented")

    else:
        logger.error(f"Unsupported platform: {platform}")
        raise NotImplementedError(f"Screen capture not supported on platform: {platform}")


__all__ = ["get_capture", "ScreenCapture", "WindowInfo", "ROI"]
