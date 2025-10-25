"""
OCR extraction for League of Legends game UI
Extracts gold, CS, HP/mana, game timer from screen captures
"""

import numpy as np
import cv2
import pytesseract
from typing import Optional, Dict, Any
import re
from loguru import logger


class GameDataExtractor:
    """Extract game data from screen captures using OCR"""

    def __init__(self):
        self.tesseract_config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:'
        self.gold_config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'

    def preprocess_image(self, img: np.ndarray, threshold: bool = True) -> np.ndarray:
        """
        Preprocess image for better OCR results
        - Convert to grayscale
        - Apply thresholding
        - Denoise
        """
        if img is None or img.size == 0:
            return img

        # Convert to grayscale if needed
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # Apply thresholding to get white text on black background
        if threshold:
            # Invert if text is light on dark background
            mean_val = np.mean(gray)
            if mean_val < 128:
                gray = cv2.bitwise_not(gray)

            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            thresh = gray

        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)

        return denoised

    def extract_number(self, img: np.ndarray, config: Optional[str] = None) -> Optional[int]:
        """Extract a numeric value from an image"""
        if img is None or img.size == 0:
            return None

        try:
            # Preprocess
            processed = self.preprocess_image(img, threshold=True)

            # Upscale for better OCR (3x)
            h, w = processed.shape[:2]
            upscaled = cv2.resize(processed, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)

            # Run OCR
            cfg = config or self.gold_config
            text = pytesseract.image_to_string(upscaled, config=cfg).strip()

            # Extract first number
            numbers = re.findall(r'\d+', text)
            if numbers:
                return int(numbers[0])

            return None

        except Exception as e:
            logger.debug(f"Error extracting number: {e}")
            return None

    def extract_time(self, img: np.ndarray) -> Optional[int]:
        """Extract game time in seconds (format MM:SS)"""
        if img is None or img.size == 0:
            return None

        try:
            processed = self.preprocess_image(img, threshold=True)
            h, w = processed.shape[:2]
            upscaled = cv2.resize(processed, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)

            text = pytesseract.image_to_string(upscaled, config=self.tesseract_config).strip()

            # Parse MM:SS format
            match = re.search(r'(\d+):(\d+)', text)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                return minutes * 60 + seconds

            return None

        except Exception as e:
            logger.debug(f"Error extracting time: {e}")
            return None

    def extract_hp_bar(self, img: np.ndarray) -> Optional[float]:
        """
        Extract HP percentage from HP bar using color detection
        Green pixels = current HP
        """
        if img is None or img.size == 0:
            return None

        try:
            # Convert to HSV for color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Green color range for HP bar
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([85, 255, 255])

            # Create mask for green pixels
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Count green pixels
            green_pixels = np.sum(mask > 0)
            total_pixels = img.shape[0] * img.shape[1]

            if total_pixels == 0:
                return None

            # Approximate HP percentage
            hp_percent = (green_pixels / total_pixels) * 100
            return min(100.0, max(0.0, hp_percent))

        except Exception as e:
            logger.debug(f"Error extracting HP: {e}")
            return None

    def extract_mana_bar(self, img: np.ndarray) -> Optional[float]:
        """
        Extract mana percentage from mana bar using color detection
        Blue pixels = current mana
        """
        if img is None or img.size == 0:
            return None

        try:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Blue color range for mana bar
            lower_blue = np.array([90, 40, 40])
            upper_blue = np.array([130, 255, 255])

            mask = cv2.inRange(hsv, lower_blue, upper_blue)
            blue_pixels = np.sum(mask > 0)
            total_pixels = img.shape[0] * img.shape[1]

            if total_pixels == 0:
                return None

            mana_percent = (blue_pixels / total_pixels) * 100
            return min(100.0, max(0.0, mana_percent))

        except Exception as e:
            logger.debug(f"Error extracting mana: {e}")
            return None

    def extract_game_data(self, roi_extracts: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Extract all game data from ROI extracts
        Returns dict with: gold, cs, game_time, hp_percent, mana_percent
        """
        data = {
            'gold': None,
            'cs': None,
            'game_time': None,
            'hp_percent': None,
            'mana_percent': None,
        }

        # Extract gold
        if 'gold' in roi_extracts and roi_extracts['gold'] is not None:
            data['gold'] = self.extract_number(roi_extracts['gold'])
            logger.debug(f"Extracted gold: {data['gold']}")

        # Extract CS
        if 'cs' in roi_extracts and roi_extracts['cs'] is not None:
            data['cs'] = self.extract_number(roi_extracts['cs'])
            logger.debug(f"Extracted CS: {data['cs']}")

        # Extract game time
        if 'game_time' in roi_extracts and roi_extracts['game_time'] is not None:
            data['game_time'] = self.extract_time(roi_extracts['game_time'])
            logger.debug(f"Extracted time: {data['game_time']}s")

        # Extract HP
        if 'player_hp' in roi_extracts and roi_extracts['player_hp'] is not None:
            data['hp_percent'] = self.extract_hp_bar(roi_extracts['player_hp'])
            logger.debug(f"Extracted HP: {data['hp_percent']}%")

        # Extract mana
        if 'player_mana' in roi_extracts and roi_extracts['player_mana'] is not None:
            data['mana_percent'] = self.extract_mana_bar(roi_extracts['player_mana'])
            logger.debug(f"Extracted mana: {data['mana_percent']}%")

        return data
