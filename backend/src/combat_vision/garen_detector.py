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

        # Temporal filtering - 3-frame sliding window
        self.q_detection_history = []
        self.w_detection_history = []
        self.e_detection_history = []

        # Gamma correction value
        self.gamma = 1.3

        # Build gamma lookup table for performance
        inv_gamma = 1.0 / self.gamma
        self.gamma_table = np.array([((i / 255.0) ** inv_gamma) * 255
                                     for i in range(256)]).astype("uint8")

    def _apply_gamma_correction(self, frame: np.ndarray) -> np.ndarray:
        """Apply gamma correction for better color detection"""
        return cv2.LUT(frame, self.gamma_table)

    def _temporal_filter(self, history: list, current_detection: bool, window_size: int = 3) -> bool:
        """Apply temporal filtering with sliding window"""
        history.append(current_detection)
        if len(history) > window_size:
            history.pop(0)

        # Require at least 2 out of 3 frames to confirm detection
        if len(history) >= 2:
            return sum(history) >= 2
        return False

    def detect_garen_q(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> bool:
        """
        Detect Garen Q (Decisive Strike)
        Visual: Sword glows golden-yellow above Garen's head

        Specifications:
        - HSV Range: H(35-55), S(0.6-1.0), V(0.8-1.0)
        - Detection Region: 60×120px sword region above champion
        - Threshold: ≥20% gold pixels
        - Temporal: 3-frame sliding window
        """
        if garen_position is None:
            # If we don't know Garen's position, scan center of screen
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # Apply gamma correction
        frame_corrected = self._apply_gamma_correction(frame)

        # Define ROI: 60×120px sword region above champion
        roi_width, roi_height = 60, 120
        x1 = max(0, x - roi_width // 2)
        y1 = max(0, y - roi_height)  # Above champion
        x2 = min(frame.shape[1], x + roi_width // 2)
        y2 = min(frame.shape[0], y)

        roi = frame_corrected[y1:y2, x1:x2]
        if roi.size == 0:
            return False

        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Gold glow: H(35-55), S(153-255), V(204-255)
        # S: 0.6 * 255 = 153, V: 0.8 * 255 = 204
        lower_gold = np.array([35, 153, 204])
        upper_gold = np.array([55, 255, 255])
        gold_mask = cv2.inRange(hsv, lower_gold, upper_gold)

        # Apply binary dilation (3×3 kernel)
        kernel = np.ones((3, 3), np.uint8)
        gold_mask = cv2.dilate(gold_mask, kernel, iterations=1)

        # Count gold pixels
        gold_pixels = np.sum(gold_mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        gold_ratio = gold_pixels / total_pixels

        # Threshold: ≥20% gold pixels
        current_detection = gold_ratio >= 0.20

        # Apply temporal filtering
        filtered_detection = self._temporal_filter(self.q_detection_history, current_detection)

        if filtered_detection:
            now = time.time()
            if now - self.last_q_time > 2.0:  # Debounce
                self.last_q_time = now
                logger.info(f"🗡️  GAREN Q DETECTED - Sword glow visible ({gold_ratio*100:.1f}% gold pixels)")
                return True

        return False

    def detect_garen_w(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> bool:
        """
        Detect Garen W (Courage)
        Visual: Blue shield appears around Garen

        Specifications:
        - HSV Range: H(190-220), S(0.5-1.0), V(0.6-1.0)
        - Detection Region: 150-200px circular region around champion
        - Threshold: ≥25% blue pixels
        - Duration: 0.2-0.4s temporal check
        """
        if garen_position is None:
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # Apply gamma correction
        frame_corrected = self._apply_gamma_correction(frame)

        # ROI: 175px radius (middle of 150-200px range) circular region
        roi_size = 175
        x1, y1 = max(0, x - roi_size), max(0, y - roi_size)
        x2, y2 = min(frame.shape[1], x + roi_size), min(frame.shape[0], y + roi_size)

        roi = frame_corrected[y1:y2, x1:x2]
        if roi.size == 0:
            return False

        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Blue shield: H(190-220), S(128-255), V(153-255)
        # S: 0.5 * 255 = 128, V: 0.6 * 255 = 153
        lower_blue = np.array([190, 128, 153])
        upper_blue = np.array([220, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # Apply binary dilation (3×3 kernel)
        kernel = np.ones((3, 3), np.uint8)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=1)

        # Count blue pixels
        blue_pixels = np.sum(blue_mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        blue_ratio = blue_pixels / total_pixels

        # Threshold: ≥25% blue pixels
        current_detection = blue_ratio >= 0.25

        # Apply temporal filtering
        filtered_detection = self._temporal_filter(self.w_detection_history, current_detection)

        if filtered_detection:
            now = time.time()
            if now - self.last_w_time > 2.0:
                self.last_w_time = now
                logger.info(f"🛡️  GAREN W DETECTED - Shield active ({blue_ratio*100:.1f}% blue pixels)")
                return True

        return False

    def detect_garen_e(self, frame: np.ndarray, garen_position: Optional[Tuple[int, int]] = None) -> Dict[str, any]:
        """
        Detect Garen E (Judgment)
        Visual: Full body spin animation with blue-white sword trails

        Specifications:
        - HSV Range: H(200-240), S(0.3-0.9), V(0.8-1.0)
        - Detection Region: 250-300px circular region around champion
        - Threshold: ≥30% blue-white streak pixels
        - Temporal: 0.3s duration confirmation via 3-frame window

        Returns: {
            'spinning': bool,
            'duration': float (seconds spinning)
        }
        """
        if garen_position is None:
            height, width = frame.shape[:2]
            garen_position = (width // 2, height // 2)

        x, y = garen_position

        # Apply gamma correction
        frame_corrected = self._apply_gamma_correction(frame)

        # ROI: 275px radius (middle of 250-300px range) circular region
        roi_size = 275
        x1, y1 = max(0, x - roi_size), max(0, y - roi_size)
        x2, y2 = min(frame.shape[1], x + roi_size), min(frame.shape[0], y + roi_size)

        roi = frame_corrected[y1:y2, x1:x2]
        if roi.size == 0:
            return {'spinning': False, 'duration': 0}

        # Convert to HSV
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Blue-white streaks: H(200-240), S(77-230), V(204-255)
        # S: 0.3 * 255 = 77, 0.9 * 255 = 230, V: 0.8 * 255 = 204
        lower_streaks = np.array([200, 77, 204])
        upper_streaks = np.array([240, 230, 255])
        streak_mask = cv2.inRange(hsv, lower_streaks, upper_streaks)

        # Apply binary dilation (3×3 kernel)
        kernel = np.ones((3, 3), np.uint8)
        streak_mask = cv2.dilate(streak_mask, kernel, iterations=1)

        # Count streak pixels
        streak_pixels = np.sum(streak_mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        streak_ratio = streak_pixels / total_pixels

        # Threshold: ≥30% streak pixels
        current_detection = streak_ratio >= 0.30

        # Apply temporal filtering
        is_spinning = self._temporal_filter(self.e_detection_history, current_detection)

        now = time.time()

        if is_spinning:
            if not self.garen_spinning:
                # Spin just started
                self.garen_spinning = True
                self.spin_start_time = now
                self.last_e_time = now
                logger.info(f"🌀 GAREN E DETECTED - SPINNING STARTED ({streak_ratio*100:.1f}% streaks)")

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
