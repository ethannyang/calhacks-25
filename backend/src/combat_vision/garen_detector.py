"""
Garen Ability Detector
Detects Garen's abilities using computer vision on screen capture
Focus: Detecting Q (sword glow), W (shield), E (spin), R (sword from sky)
"""

import cv2
import numpy as np
from typing import Optional, Dict, Tuple
from loguru import logger
import time


class GarenAbilityDetector:
    """Detects Garen's ability animations using OpenCV"""

    def __init__(self):
        # Cooldown tracking
        self.last_q_time = 0
        self.last_w_time = 0
        self.last_e_time = 0
        self.last_r_time = 0

        # Cooldowns (these are approximate, will be refined)
        self.q_cooldown = 8.0  # Garen Q cooldown at rank 1
        self.w_cooldown = 24.0  # Garen W cooldown
        self.e_cooldown = 9.0  # Garen E cooldown
        self.r_cooldown = 120.0  # Garen R cooldown at rank 1

        # Detection state
        self.garen_spinning = False
        self.spin_start_time = 0

    def detect_garen_q(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> bool:
        """
        Detect Garen Q (Decisive Strike)
        Visual: Sword glows white/gold above Garen's head

        Detection method:
        1. Look for bright white/gold glow in champion area
        2. Detect increased brightness above champion model
        """
        if garen_position is None:
            # If we don't know Garen's position, scan center of screen
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # Define ROI around Garen (assume he's in this area)
        roi_size = 150
        x1, y1 = max(0, x - roi_size//2), max(0, y - roi_size)
        x2, y2 = min(frame.shape[1], x + roi_size//2), min(frame.shape[0], y + roi_size//2)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False

        # Convert to HSV to detect bright white/gold glow
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # White glow (high value, low saturation)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 50, 255])
        white_mask = cv2.inRange(hsv, lower_white, upper_white)

        # Gold glow (yellow hue)
        lower_gold = np.array([20, 100, 200])
        upper_gold = np.array([40, 255, 255])
        gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)

        # Combine masks
        combined_mask = cv2.bitwise_or(white_mask, gold_mask)

        # Count bright pixels
        bright_pixels = np.sum(combined_mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        bright_ratio = bright_pixels / total_pixels

        # If >3% of ROI is bright white/gold, Q is active
        if bright_ratio > 0.03:
            now = time.time()
            if now - self.last_q_time > 2.0:  # Debounce (don't spam detections)
                self.last_q_time = now
                logger.info("🗡️  GAREN Q DETECTED - Sword glow visible")
                return True

        return False

    def detect_garen_w(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> bool:
        """
        Detect Garen W (Courage)
        Visual: Blue shield appears around Garen

        Detection method:
        1. Look for blue circular glow around champion
        2. Detect shield VFX (blue-ish particles)
        """
        if garen_position is None:
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # ROI around Garen
        roi_size = 200
        x1, y1 = max(0, x - roi_size//2), max(0, y - roi_size)
        x2, y2 = min(frame.shape[1], x + roi_size//2), min(frame.shape[0], y + roi_size//2)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False

        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Blue shield glow
        lower_blue = np.array([90, 50, 100])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Count blue pixels
        blue_pixels = np.sum(blue_mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        blue_ratio = blue_pixels / total_pixels

        # If >2% of ROI is blue, W is active
        if blue_ratio > 0.02:
            now = time.time()
            if now - self.last_w_time > 2.0:
                self.last_w_time = now
                logger.info("🛡️  GAREN W DETECTED - Shield active")
                return True

        return False

    def detect_garen_e(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> Dict[str, any]:
        """
        Detect Garen E (Judgment)
        Visual: Full body spin animation with sword trails

        Detection method:
        1. Look for circular motion blur
        2. Detect rapid color changes (spinning creates blur)
        3. Track duration of spin (lasts 3 seconds)

        Returns: {
            'spinning': bool,
            'duration': float (seconds spinning)
        }
        """
        if garen_position is None:
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # ROI around Garen
        roi_size = 200
        x1, y1 = max(0, x - roi_size//2), max(0, y - roi_size)
        x2, y2 = min(frame.shape[1], x + roi_size//2), min(frame.shape[0], y + roi_size//2)

        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return {'spinning': False, 'duration': 0}

        # Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # Calculate motion blur (spinning creates high frequency changes)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()

        # Also check for sword trail colors (blue/white streaks)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Bright streaks (sword trails)
        lower_bright = np.array([0, 0, 180])
        upper_bright = np.array([180, 100, 255])
        bright_mask = cv2.inRange(hsv, lower_bright, upper_bright)
        bright_ratio = np.sum(bright_mask > 0) / (roi.shape[0] * roi.shape[1])

        # If high variance AND bright streaks, Garen is spinning
        is_spinning = variance > 500 and bright_ratio > 0.05

        now = time.time()

        if is_spinning:
            if not self.garen_spinning:
                # Spin just started
                self.garen_spinning = True
                self.spin_start_time = now
                self.last_e_time = now
                logger.info("🌀 GAREN E DETECTED - SPINNING STARTED")

            duration = now - self.spin_start_time
            return {'spinning': True, 'duration': duration}
        else:
            if self.garen_spinning:
                # Spin just ended
                duration = now - self.spin_start_time
                logger.info(f"🌀 GAREN E ENDED - Spun for {duration:.1f}s")
                self.garen_spinning = False

            return {'spinning': False, 'duration': 0}

    def detect_garen_r(self, frame: np.ndarray) -> bool:
        """
        Detect Garen R (Demacian Justice)
        Visual: Giant sword falls from sky with dramatic VFX

        Detection method:
        1. Look for giant sword shape descending
        2. Detect dramatic lighting change (screen flashes)
        3. Look for specific R VFX colors (gold/red)
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Giant sword is usually gold/yellow with bright glow
        lower_gold = np.array([15, 100, 200])
        upper_gold = np.array([35, 255, 255])
        gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)

        # Also check for red (justice theme)
        lower_red = np.array([0, 150, 150])
        upper_red = np.array([10, 255, 255])
        red_mask = cv2.inRange(hsv, lower_red, upper_red)

        # Combine
        combined_mask = cv2.bitwise_or(gold_mask, red_mask)

        # R VFX covers a large area
        bright_pixels = np.sum(combined_mask > 0)
        total_pixels = frame.shape[0] * frame.shape[1]
        effect_ratio = bright_pixels / total_pixels

        # If >10% of screen is gold/red, R is happening
        if effect_ratio > 0.10:
            now = time.time()
            if now - self.last_r_time > 5.0:  # Debounce
                self.last_r_time = now
                logger.info("⚔️  GAREN R DETECTED - DEMACIAN JUSTICE")
                return True

        return False

    def get_ability_cooldowns(self) -> Dict[str, float]:
        """
        Get estimated cooldowns for Garen's abilities
        Returns time remaining (seconds) for each ability
        """
        now = time.time()

        return {
            'Q': max(0, self.q_cooldown - (now - self.last_q_time)),
            'W': max(0, self.w_cooldown - (now - self.last_w_time)),
            'E': max(0, self.e_cooldown - (now - self.last_e_time)),
            'R': max(0, self.r_cooldown - (now - self.last_r_time))
        }

    def is_ability_available(self, ability: str) -> bool:
        """Check if a specific ability is off cooldown"""
        cooldowns = self.get_ability_cooldowns()
        return cooldowns.get(ability, 0) == 0
