"""
Test OCR extraction on captured frames
Verifies that GameDataExtractor can extract game data from captured images
"""

import cv2
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ocr.extractor import GameDataExtractor
from loguru import logger


def main():
    logger.info("Starting OCR extraction test...")

    # Check if captured frame exists
    if not os.path.exists("captured_frame.png"):
        logger.error("No captured_frame.png found!")
        print("\n❌ Please run test_capture.py first to capture a frame")
        return

    # Load the captured frame
    frame = cv2.imread("captured_frame.png")
    logger.info(f"Loaded frame: {frame.shape}")

    # Create extractor
    extractor = GameDataExtractor()

    # Load and test each ROI
    roi_files = {
        'gold': 'roi_gold.png',
        'cs': 'roi_cs.png',
        'game_time': 'roi_game_time.png',
        'player_hp': 'roi_player_hp.png',
        'player_mana': 'roi_player_mana.png',
        'minimap': 'roi_minimap.png'
    }

    print("\n" + "="*50)
    print("OCR EXTRACTION RESULTS")
    print("="*50)

    results = {}

    # Test gold
    if os.path.exists(roi_files['gold']):
        img = cv2.imread(roi_files['gold'])
        gold = extractor.extract_number(img)
        results['gold'] = gold
        print(f"💰 Gold: {gold if gold else 'FAILED'}")
    else:
        print(f"⚠️  Gold ROI image not found")

    # Test CS
    if os.path.exists(roi_files['cs']):
        img = cv2.imread(roi_files['cs'])
        cs = extractor.extract_number(img)
        results['cs'] = cs
        print(f"🗡️  CS: {cs if cs else 'FAILED'}")
    else:
        print(f"⚠️  CS ROI image not found")

    # Test game time
    if os.path.exists(roi_files['game_time']):
        img = cv2.imread(roi_files['game_time'])
        game_time = extractor.extract_time(img)
        if game_time:
            minutes = game_time // 60
            seconds = game_time % 60
            results['game_time'] = game_time
            print(f"⏰ Game Time: {minutes}:{seconds:02d} ({game_time}s)")
        else:
            results['game_time'] = None
            print(f"⏰ Game Time: FAILED")
    else:
        print(f"⚠️  Game Time ROI image not found")

    # Test HP bar
    if os.path.exists(roi_files['player_hp']):
        img = cv2.imread(roi_files['player_hp'])
        hp_percent = extractor.extract_hp_bar(img)
        results['hp_percent'] = hp_percent
        print(f"❤️  HP: {hp_percent:.1f}%" if hp_percent else "❤️  HP: FAILED")
    else:
        print(f"⚠️  HP ROI image not found")

    # Test Mana bar
    if os.path.exists(roi_files['player_mana']):
        img = cv2.imread(roi_files['player_mana'])
        mana_percent = extractor.extract_mana_bar(img)
        results['mana_percent'] = mana_percent
        print(f"💙 Mana: {mana_percent:.1f}%" if mana_percent else "💙 Mana: FAILED")
    else:
        print(f"⚠️  Mana ROI image not found")

    print("="*50)

    # Test full extraction pipeline
    print("\n" + "="*50)
    print("TESTING FULL EXTRACTION PIPELINE")
    print("="*50)

    # Load all ROIs
    roi_extracts = {}
    for roi_name, file_path in roi_files.items():
        if os.path.exists(file_path):
            roi_extracts[roi_name] = cv2.imread(file_path)

    # Run full extraction
    game_data = extractor.extract_game_data(roi_extracts)

    print("\nExtracted Game Data:")
    print(f"  Gold: {game_data.get('gold')}")
    print(f"  CS: {game_data.get('cs')}")

    time_seconds = game_data.get('game_time')
    if time_seconds:
        print(f"  Game Time: {time_seconds // 60}:{time_seconds % 60:02d}")
    else:
        print(f"  Game Time: None")

    print(f"  HP: {game_data.get('hp_percent'):.1f}%" if game_data.get('hp_percent') else "  HP: None")
    print(f"  Mana: {game_data.get('mana_percent'):.1f}%" if game_data.get('mana_percent') else "  Mana: None")

    # Success assessment
    print("\n" + "="*50)
    success_count = sum(1 for v in [game_data.get('gold'), game_data.get('cs'), game_data.get('game_time')] if v is not None)
    total_count = 3  # gold, cs, game_time (core metrics)

    if success_count == total_count:
        print("✅ OCR WORKING PERFECTLY!")
        print("   All core metrics extracted successfully")
    elif success_count > 0:
        print(f"⚠️  PARTIAL SUCCESS: {success_count}/{total_count} metrics extracted")
        print("   OCR is working but may need ROI adjustment")
    else:
        print("❌ OCR FAILED")
        print("   No metrics extracted - ROIs may need recalibration")

    print("="*50)


if __name__ == "__main__":
    main()
