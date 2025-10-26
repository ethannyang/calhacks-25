"""
Test script for screen capture functionality
Run this to test if screen capture is working on your system
"""

import cv2
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from capture import get_capture
from loguru import logger


def main():
    logger.info("Starting screen capture test...")

    # Create capture instance (platform-aware)
    capture = get_capture()

    # List all windows
    logger.info("Listing all windows...")
    windows = capture.list_windows()
    logger.info(f"Found {len(windows)} windows")

    print("\n=== Available Windows ===")
    for i, window in enumerate(windows[:20]):  # Show first 20
        print(f"{i+1}. {window.app_name} - {window.window_name}")
        print(f"   Size: {window.bounds[2]}x{window.bounds[3]}")

    # Try to find League of Legends
    print("\n=== Searching for League of Legends ===")
    lol_window = capture.find_game_window()

    if lol_window:
        logger.info(f"Found LoL window: {lol_window.app_name} - {lol_window.window_name}")
        logger.info(f"Window ID: {lol_window.window_id}")
        logger.info(f"Size: {lol_window.bounds[2]}x{lol_window.bounds[3]}")

        # Try to capture it
        logger.info("Attempting to capture window...")
        frame = capture.capture_window(lol_window.window_id)

        if frame is not None:
            logger.info(f"Successfully captured frame: {frame.shape}")

            # Setup ROIs
            capture.setup_lol_rois(frame.shape[1], frame.shape[0])
            logger.info(f"Setup {len(capture.rois)} ROIs")

            # Extract ROIs
            roi_extracts = capture.extract_rois(frame)

            # Save captured frame for inspection
            output_path = "captured_frame.png"
            cv2.imwrite(output_path, frame)
            logger.info(f"Saved captured frame to {output_path}")

            # Save ROI extracts
            for roi_name, roi_img in roi_extracts.items():
                if roi_img is not None:
                    roi_path = f"roi_{roi_name}.png"
                    cv2.imwrite(roi_path, roi_img)
                    logger.info(f"Saved ROI '{roi_name}' to {roi_path}")

            print("\n=== Capture Successful! ===")
            print(f"Check the following files:")
            print(f"  - captured_frame.png (full capture)")
            for roi_name in roi_extracts.keys():
                print(f"  - roi_{roi_name}.png")

        else:
            logger.error("Failed to capture window")
            print("\n=== Capture Failed ===")
            print("Make sure League of Legends is running and visible")

    else:
        logger.warning("League of Legends window not found")
        print("\n=== LoL Window Not Found ===")
        print("Options:")
        print("1. Make sure League of Legends is running")
        print("2. Try running in a game (not just client)")
        print("3. Check the window list above to see available windows")

        # Fallback: Try to capture any window for testing
        print("\nWould you like to test capture with another window? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            try:
                idx = int(input("Enter window number from the list above: ")) - 1
                if 0 <= idx < len(windows):
                    test_window = windows[idx]
                    logger.info(f"Testing with: {test_window.app_name}")
                    frame = capture.capture_window(test_window.window_id)
                    if frame is not None:
                        cv2.imwrite("test_capture.png", frame)
                        logger.info("Saved test_capture.png")
                        print("✅ Capture working! Check test_capture.png")
                    else:
                        logger.error("Capture failed")
            except Exception as e:
                logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()
