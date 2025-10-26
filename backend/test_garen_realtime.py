"""
Real-time Garen ability detection test
Automatically starts capturing and detecting without prompts
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
    print("GAREN ABILITY DETECTION - REAL-TIME TEST")
    print("=" * 60)
    print("\n🎮 Starting in 3 seconds...")
    print("Fight Garen and watch for ability detections!")
    print("Press Ctrl+C to stop\n")
    await asyncio.sleep(3)
    print("=" * 60)
    print("🔴 RECORDING...\n")

    capture = MacOSCapture()
    detector = GarenAbilityDetector()

    frame_count = 0
    last_fps_time = time.time()
    fps = 0
    detection_count = 0

    try:
        while True:
            # Capture frame
            frame = capture.capture_game()

            if frame is None:
                print("\r⚠️  No game window detected. Waiting...              ", end='', flush=True)
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
            q_status = f"Q:{'✓' if garen_q else '-'}({cooldowns['Q']:.0f}s)"
            w_status = f"W:{'✓' if garen_w else '-'}({cooldowns['W']:.0f}s)"
            e_status = f"E:{'SPIN!' if garen_e_result['spinning'] else '-'}({cooldowns['E']:.0f}s)"
            r_status = f"R:{'✓' if garen_r else '-'}({cooldowns['R']:.0f}s)"

            print(f"\r[{fps:.0f} FPS] {q_status} | {w_status} | {e_status} | {r_status} | Frames:{frame_count}",
                  end='', flush=True)

            # Save detection screenshots
            if garen_q or garen_w or garen_e_result['spinning'] or garen_r:
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

                filename = f"garen_{detection_count}_{ability_name}_{int(time.time())}.png"
                success = cv2.imwrite(filename, frame)
                if success:
                    print(f"\n🎯 DETECTED! Saved: {filename}")
                else:
                    print(f"\n❌ DETECTED but FAILED to save: {filename} (frame shape: {frame.shape if frame is not None else 'None'})")

            # Run at ~30 FPS
            await asyncio.sleep(0.033)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("✅ Test stopped")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  Total frames: {frame_count}")
        print(f"  Detections: {detection_count}")
        print(f"  Screenshots: Check current directory")
        print(f"  Log: garen_detection_test.log")
        print("\n")


if __name__ == "__main__":
    asyncio.run(test_garen_detection())
