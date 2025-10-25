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
        Uses normalized coordinates that scale to any resolution
        """
        # Normalized ROI coordinates (x, y, w, h) as fractions of screen dimensions
        # These are calibrated for standard LoL UI layout
        normalized_rois = {
            "player_hp": (0.391, 0.963, 0.163, 0.016),
            "player_mana": (0.391, 0.979, 0.161, 0.012),
            "gold": (0.564, 0.979, 0.053, 0.016),
            "cs": (0.903, 0.005, 0.035, 0.021),
            "game_time": (0.948, 0.002, 0.049, 0.026),
            "minimap": (0.839, 0.747, 0.153, 0.242),  # 3024×1890: TL(2536,1411) BR(2998,1868)
        }

        # Convert normalized coordinates to pixel coordinates
        for roi_name, (norm_x, norm_y, norm_w, norm_h) in normalized_rois.items():
            x = int(norm_x * width)
            y = int(norm_y * height)
            w = int(norm_w * width)
            h = int(norm_h * height)
            self.rois.append(ROI(roi_name, x, y, w, h))

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
