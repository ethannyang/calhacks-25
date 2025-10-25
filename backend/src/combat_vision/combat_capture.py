"""
High-Speed Combat Capture System
Captures game at 30 FPS specifically for combat detection
Focuses on champion area (center of screen) for performance
"""

import numpy as np
from typing import Optional
from loguru import logger
from src.capture.macos import MacOSCapture


class CombatCapture:
    """High-speed capture system for combat analysis"""

    def __init__(self):
        self.base_capture = MacOSCapture()
        self.combat_mode_active = False

    def enable_combat_mode(self):
        """Switch to high-speed combat capture (30 FPS)"""
        self.combat_mode_active = True
        logger.info("🎯 Combat mode ENABLED - 30 FPS capture")

    def disable_combat_mode(self):
        """Return to normal capture speed"""
        self.combat_mode_active = False
        logger.info("🎯 Combat mode DISABLED - returning to 2 FPS")

    def capture_combat_frame(self) -> Optional[np.ndarray]:
        """
        Capture frame focused on combat area
        Captures center 60% of screen for performance
        """
        # Get full frame
        full_frame = self.base_capture.capture_game()
        if full_frame is None:
            return None

        # Crop to center (where champion usually is during combat)
        height, width = full_frame.shape[:2]

        # Center 60% of screen
        crop_width = int(width * 0.6)
        crop_height = int(height * 0.6)

        x1 = (width - crop_width) // 2
        y1 = (height - crop_height) // 2
        x2 = x1 + crop_width
        y2 = y1 + crop_height

        combat_frame = full_frame[y1:y2, x1:x2]

        return combat_frame

    def detect_combat_situation(self, frame: np.ndarray) -> bool:
        """
        Detect if player is in combat
        Triggers based on:
        1. Rapid HP changes
        2. Ability VFX detected
        3. Multiple champions visible on screen
        """
        # This is a placeholder - will be enhanced with actual detection
        # For now, we'll activate combat mode manually via game state

        return False  # Will implement full detection later
