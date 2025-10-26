"""
Debug script to visualize ROI locations on the captured frame
This helps identify the correct coordinates for each UI element
"""

import cv2
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from capture import get_capture
from loguru import logger


def main():
    logger.info("Starting ROI debug...")

    # Create capture instance (platform-aware)
    capture = get_capture()

    # Find League of Legends
    lol_window = capture.find_game_window()

    if not lol_window:
        logger.error("League of Legends window not found")
        return

    # Capture window
    frame = capture.capture_window(lol_window.window_id)

    if frame is None:
        logger.error("Failed to capture window")
        return

    logger.info(f"Captured frame: {frame.shape}")

    # Setup ROIs
    capture.setup_lol_rois(frame.shape[1], frame.shape[0])

    # Draw rectangles on the frame to show ROI locations
    debug_frame = frame.copy()

    colors = [
        (0, 255, 0),    # Green - gold
        (255, 0, 0),    # Blue - cs
        (0, 255, 255),  # Yellow - game_time
        (255, 0, 255),  # Magenta - player_hp
        (0, 165, 255),  # Orange - player_mana
        (255, 255, 0),  # Cyan - minimap
    ]

    for i, roi in enumerate(capture.rois):
        color = colors[i % len(colors)]
        # Draw rectangle
        cv2.rectangle(debug_frame,
                     (roi.x, roi.y),
                     (roi.x + roi.width, roi.y + roi.height),
                     color, 3)

        # Add label
        label = roi.name
        label_pos = (roi.x, roi.y - 10 if roi.y > 20 else roi.y + roi.height + 20)
        cv2.putText(debug_frame, label, label_pos,
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # Save annotated frame
    output_path = "debug_rois_annotated.png"
    cv2.imwrite(output_path, debug_frame)
    logger.info(f"Saved annotated frame to {output_path}")

    # Also save the original
    cv2.imwrite("debug_rois_original.png", frame)
    logger.info("Saved original frame to debug_rois_original.png")

    # Print current ROI coordinates
    print("\n=== Current ROI Coordinates (at 1920x1080) ===")
    scale_x = 1920.0 / frame.shape[1]
    scale_y = 1080.0 / frame.shape[0]

    for roi in capture.rois:
        # Convert back to 1920x1080 coordinates
        x_1080 = int(roi.x * scale_x)
        y_1080 = int(roi.y * scale_y)
        w_1080 = int(roi.width * scale_x)
        h_1080 = int(roi.height * scale_y)
        print(f"{roi.name}: ({x_1080}, {y_1080}, {w_1080}, {h_1080})")

    print(f"\n=== Check the annotated image: {output_path} ===")
    print("Look at where each colored rectangle is placed:")
    for i, roi in enumerate(capture.rois):
        color_name = ["Green", "Blue", "Yellow", "Magenta", "Orange", "Cyan"][i]
        print(f"  {color_name}: {roi.name}")


if __name__ == "__main__":
    main()
