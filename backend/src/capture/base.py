"""
Base screen capture interface
Platform-specific implementations in macos.py, windows.py, linux.py
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
import numpy as np
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Information about a captured window"""
    window_id: int
    window_name: str
    app_name: str
    bounds: Tuple[int, int, int, int]  # (x, y, width, height)


@dataclass
class ROI:
    """Region of Interest for OCR extraction"""
    name: str
    x: int
    y: int
    width: int
    height: int

    def extract(self, frame: np.ndarray) -> np.ndarray:
        """Extract this ROI from a frame"""
        return frame[self.y:self.y + self.height, self.x:self.x + self.width]


class ScreenCapture(ABC):
    """Abstract base class for platform-specific screen capture"""

    def __init__(self):
        self.target_window: Optional[WindowInfo] = None
        self.rois: List[ROI] = []

    @abstractmethod
    def list_windows(self) -> List[WindowInfo]:
        """List all available windows"""
        pass

    @abstractmethod
    def find_game_window(self, window_name_pattern: str = "League of Legends") -> Optional[WindowInfo]:
        """Find the League of Legends game window"""
        pass

    @abstractmethod
    def capture_window(self, window_id: int) -> Optional[np.ndarray]:
        """Capture a specific window and return as numpy array (BGR format)"""
        pass

    def capture_game(self) -> Optional[np.ndarray]:
        """Capture the current target game window"""
        if not self.target_window:
            self.target_window = self.find_game_window()
            if not self.target_window:
                return None

        return self.capture_window(self.target_window.window_id)

    def setup_lol_rois(self, width: int, height: int):
        """
        Setup standard League of Legends UI regions of interest
        Assumes 1920x1080 resolution, will scale for others
        """
        scale_x = width / 1920.0
        scale_y = height / 1080.0

        def scale_roi(x, y, w, h):
            return (int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y))

        # Gold count (bottom-center area, near champion portrait)
        x, y, w, h = scale_roi(440, 1042, 110, 28)
        self.rois.append(ROI("gold", x, y, w, h))

        # CS count (bottom-center, to the right of gold)
        x, y, w, h = scale_roi(555, 1042, 95, 28)
        self.rois.append(ROI("cs", x, y, w, h))

        # Game timer (top-center)
        x, y, w, h = scale_roi(920, 2, 80, 22)
        self.rois.append(ROI("game_time", x, y, w, h))

        # Player HP bar (bottom-left, above abilities)
        x, y, w, h = scale_roi(285, 990, 250, 25)
        self.rois.append(ROI("player_hp", x, y, w, h))

        # Player mana bar (bottom-left, below HP)
        x, y, w, h = scale_roi(285, 1018, 250, 20)
        self.rois.append(ROI("player_mana", x, y, w, h))

        # Minimap area (bottom-right corner)
        x, y, w, h = scale_roi(1620, 780, 300, 300)
        self.rois.append(ROI("minimap", x, y, w, h))

    def extract_rois(self, frame: np.ndarray) -> dict:
        """Extract all ROIs from a frame"""
        extracts = {}
        for roi in self.rois:
            try:
                extracts[roi.name] = roi.extract(frame)
            except Exception as e:
                print(f"Failed to extract ROI {roi.name}: {e}")
                extracts[roi.name] = None
        return extracts
