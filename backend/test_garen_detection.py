"""
Test script for Garen ability detection
Run this while you're in a game vs Garen to test the detection
"""

import cv2
import numpy as np
import asyncio
import time
from src.capture.macos import MacOSCapture
from src.combat_vision.garen_detector import GarenAbilityDetector
from loguru import logger

# Setup logging
logger.add("garen_detection_test.log", rotation="10 MB")


async def test_garen_detection():
    """Test Garen ability detection in real-time"""

    print("=" * 60)
    print("GAREN ABILITY DETECTION TEST")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Start a game vs Garen (Practice Tool recommended)")
    print("2. Run this script")
    print("3. Fight Garen and watch the console for detections")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)

    capture = MacOSCapture()
    detector = GarenAbilityDetector()

    frame_count = 0
    last_fps_time = time.time()
    fps = 0

    # Save screenshots of detections for analysis
    save_detections = True
    detection_count = 0

    try:
        while True:
            # Capture frame
            frame = capture.capture_game()

            if frame is None:
                print("⚠️  No game window detected. Start League of Legends.")
                await asyncio.sleep(1)
                continue

            # Calculate FPS
            frame_count += 1
            if frame_count % 30 == 0:
                now = time.time()
                fps = 30 / (now - last_fps_time)
                last_fps_time = now

            # Test all ability detections
            garen_q = detector.detect_garen_q(frame)
            garen_w = detector.detect_garen_w(frame)
            garen_e_result = detector.detect_garen_e(frame)
            garen_r = detector.detect_garen_r(frame)

            # Get cooldowns
            cooldowns = detector.get_ability_cooldowns()

            # Display info
            print(f"\r[FPS: {fps:.1f}] Frame {frame_count} | "
                  f"Q: {'✓' if garen_q else '-'} ({cooldowns['Q']:.1f}s) | "
                  f"W: {'✓' if garen_w else '-'} ({cooldowns['W']:.1f}s) | "
                  f"E: {'✓ ({:.1f}s)'.format(garen_e_result['duration']) if garen_e_result['spinning'] else '-'} ({cooldowns['E']:.1f}s) | "
                  f"R: {'✓' if garen_r else '-'} ({cooldowns['R']:.1f}s)",
                  end='', flush=True)

            # Save detection screenshots
            if save_detections and (garen_q or garen_w or garen_e_result['spinning'] or garen_r):
                detection_count += 1
                ability_name = "UNKNOWN"
                if garen_q:
                    ability_name = "Q_DECISIVE_STRIKE"
                elif garen_w:
                    ability_name = "W_COURAGE"
                elif garen_e_result['spinning']:
                    ability_name = f"E_JUDGMENT_{garen_e_result['duration']:.1f}s"
                elif garen_r:
                    ability_name = "R_DEMACIAN_JUSTICE"

                filename = f"garen_detection_{detection_count}_{ability_name}.png"
                cv2.imwrite(filename, frame)
                print(f"\n📸 Saved screenshot: {filename}")

            # Show live feed with detections (optional - can be slow)
            # Uncomment to enable visual feedback
            # display_frame = frame.copy()
            # if garen_q:
            #     cv2.putText(display_frame, "GAREN Q!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)
            # if garen_w:
            #     cv2.putText(display_frame, "GAREN W!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 255), 3)
            # if garen_e_result['spinning']:
            #     cv2.putText(display_frame, f"GAREN E! ({garen_e_result['duration']:.1f}s)", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            # if garen_r:
            #     cv2.putText(display_frame, "GAREN R!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
            #
            # cv2.imshow("Garen Detection Test", display_frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

            # Run at ~30 FPS for testing
            await asyncio.sleep(0.033)

    except KeyboardInterrupt:
        print("\n\n✅ Test stopped by user")
    finally:
        print(f"\n\nTest Summary:")
        print(f"Total frames processed: {frame_count}")
        print(f"Detections saved: {detection_count}")
        print(f"Screenshots saved to current directory")
        print(f"Check 'garen_detection_test.log' for detailed logs")


async def test_single_screenshot():
    """Test detection on a single screenshot"""
    print("=" * 60)
    print("SINGLE SCREENSHOT TEST")
    print("=" * 60)
    print("\nThis will capture ONE screenshot and analyze it.")
    print("Position Garen on screen, then press Enter...")
    input()

    capture = MacOSCapture()
    detector = GarenAbilityDetector()

    frame = capture.capture_game()
    if frame is None:
        print("❌ Could not capture game window")
        return

    print("\n🔍 Analyzing screenshot...")

    # Test all detections
    garen_q = detector.detect_garen_q(frame)
    garen_w = detector.detect_garen_w(frame)
    garen_e_result = detector.detect_garen_e(frame)
    garen_r = detector.detect_garen_r(frame)

    # Save screenshot with annotations
    annotated = frame.copy()
    y_offset = 50

    if garen_q:
        cv2.putText(annotated, "GAREN Q DETECTED!", (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        y_offset += 60

    if garen_w:
        cv2.putText(annotated, "GAREN W DETECTED!", (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 255), 3)
        y_offset += 60

    if garen_e_result['spinning']:
        cv2.putText(annotated, f"GAREN E DETECTED! ({garen_e_result['duration']:.1f}s)", (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        y_offset += 60

    if garen_r:
        cv2.putText(annotated, "GAREN R DETECTED!", (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
        y_offset += 60

    if not (garen_q or garen_w or garen_e_result['spinning'] or garen_r):
        cv2.putText(annotated, "No abilities detected", (50, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 128, 128), 3)

    # Save results
    cv2.imwrite("test_screenshot_original.png", frame)
    cv2.imwrite("test_screenshot_annotated.png", annotated)

    print("\n📊 Results:")
    print(f"  Q (Decisive Strike): {'✓ DETECTED' if garen_q else '✗ Not detected'}")
    print(f"  W (Courage):         {'✓ DETECTED' if garen_w else '✗ Not detected'}")
    print(f"  E (Judgment):        {'✓ DETECTED (%.1fs)' % garen_e_result['duration'] if garen_e_result['spinning'] else '✗ Not detected'}")
    print(f"  R (Demacian Justice): {'✓ DETECTED' if garen_r else '✗ Not detected'}")

    print("\n📸 Screenshots saved:")
    print("  - test_screenshot_original.png")
    print("  - test_screenshot_annotated.png")


async def main():
    """Main test menu"""
    print("\n" + "=" * 60)
    print("GAREN ABILITY DETECTION TEST SUITE")
    print("=" * 60)
    print("\nChoose test mode:")
    print("1. Real-time detection (captures frames continuously)")
    print("2. Single screenshot test (capture once and analyze)")
    print("\nEnter choice (1 or 2): ", end='')

    choice = input().strip()

    if choice == '1':
        await test_garen_detection()
    elif choice == '2':
        await test_single_screenshot()
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
