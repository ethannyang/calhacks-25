#!/usr/bin/env python
"""
ROI Calibration Tool for League of Legends Screen Capture
Tests if the capture pipeline is working and ROIs are properly aligned
"""

import cv2
import time
from src.capture.macos import MacOSCapture
from src.ocr.extractor import GameDataExtractor
from loguru import logger

def calibrate_rois():
    """Interactive ROI calibration tool"""
    print("=" * 60)
    print("League of Legends ROI Calibration Tool")
    print("=" * 60)
    print("\n1. Please make sure League of Legends is running")
    print("2. The game should be in an active match (not lobby)")
    print("3. Starting calibration...")

    # Initialize capture
    print("\n🔍 Searching for League window...")
    capture = MacOSCapture()
    window_info = capture.find_game_window()

    if not window_info:
        print("❌ League of Legends window not found!")
        print("\nTroubleshooting:")
        print("1. Make sure League is running")
        print("2. Try switching to windowed or borderless mode")
        print("3. Check if the game window is minimized")
        return

    print(f"✅ Found window: {window_info.app_name} - {window_info.window_name}")
    print(f"   Resolution: {window_info.bounds[2]}x{window_info.bounds[3]}")

    # Capture frame
    print("\n📸 Capturing game window...")
    frame = capture.capture_window(window_info.window_id)

    if frame is None:
        print("❌ Failed to capture window")
        return

    print(f"✅ Captured frame: {frame.shape[1]}x{frame.shape[0]}")

    # Setup ROIs
    print("\n📐 Setting up ROIs...")
    capture.setup_lol_rois(frame.shape[1], frame.shape[0])
    print(f"✅ Configured {len(capture.rois)} ROIs")

    # Draw ROIs on frame
    display = frame.copy()
    colors = {
        'gold': (0, 255, 255),      # Yellow
        'cs': (255, 0, 255),         # Magenta
        'game_time': (0, 255, 0),    # Green
        'player_hp': (0, 255, 0),    # Green
        'player_mana': (255, 0, 0),  # Blue
        'minimap': (255, 255, 0),    # Cyan
    }

    for roi in capture.rois:
        color = colors.get(roi.name, (0, 255, 0))
        # Draw rectangle
        cv2.rectangle(display,
                     (roi.x, roi.y),
                     (roi.x + roi.width, roi.y + roi.height),
                     color, 2)
        # Draw label
        cv2.putText(display, roi.name,
                   (roi.x, roi.y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Save calibration image
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    calibration_file = f'roi_calibration_{timestamp}.png'
    cv2.imwrite(calibration_file, display)
    print(f"\n💾 Saved calibration image: {calibration_file}")
    print("   Check if the colored rectangles align with:")
    print("   - Yellow: Gold counter (bottom center)")
    print("   - Magenta: CS counter (top right)")
    print("   - Green: Game timer (top right)")
    print("   - Green: HP bar (bottom center)")
    print("   - Blue: Mana bar (bottom center)")
    print("   - Cyan: Minimap (bottom right)")

    # Extract and test OCR
    print("\n🔬 Testing OCR extraction...")
    roi_extracts = capture.extract_rois(frame)

    # Save individual ROI images for debugging
    for name, img in roi_extracts.items():
        if img is not None:
            roi_file = f"debug_roi_{name}_{timestamp}.png"
            cv2.imwrite(roi_file, img)
            print(f"   Saved ROI: {roi_file} ({img.shape[1]}x{img.shape[0]})")

    # Run OCR
    print("\n🔤 Running OCR on extracted regions...")
    extractor = GameDataExtractor()
    results = extractor.extract_game_data(roi_extracts)

    print("\n📊 OCR Results:")
    print("-" * 40)
    success_count = 0
    for key, value in results.items():
        if value is not None:
            print(f"  ✅ {key:12} : {value}")
            success_count += 1
        else:
            print(f"  ❌ {key:12} : Failed to extract")

    print("-" * 40)
    print(f"Success rate: {success_count}/{len(results)} ({success_count*100//len(results)}%)")

    # Provide recommendations
    print("\n💡 Recommendations:")
    if success_count == 0:
        print("❌ No data extracted. Issues:")
        print("1. ROIs might be misaligned for your resolution")
        print("2. OCR preprocessing might need adjustment")
        print("3. Check the saved ROI images to see what's being captured")
    elif success_count < 3:
        print("⚠️ Partial extraction. Try:")
        print("1. Adjusting game UI scale in League settings")
        print("2. Using borderless windowed mode")
        print("3. Check debug_roi_*.png files for what's being captured")
    else:
        print("✅ Pipeline is working! You can now:")
        print("1. Run the main application: python main.py")
        print("2. The real data should flow through the coaching system")

    print("\n📁 Debug files saved in current directory:")
    print(f"   - {calibration_file} (overall ROI alignment)")
    print(f"   - debug_roi_*.png (individual ROI captures)")

if __name__ == "__main__":
    try:
        calibrate_rois()
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        import traceback
        traceback.print_exc()