"""
Test audio-based ability detection
First run: List available audio devices
Second run: Detect abilities in real-time
"""

import asyncio
import time
from src.combat_vision.audio_detector import AudioAbilityDetector
from loguru import logger

# Setup logging
logger.add("audio_detection_test.log", rotation="10 MB")


async def list_devices():
    """List all available audio devices"""
    print("\n" + "=" * 60)
    print("AUDIO DEVICE DETECTION")
    print("=" * 60)
    print("\nScanning for audio devices...\n")

    AudioAbilityDetector.list_audio_devices()

    print("\n" + "=" * 60)
    print("\nNOTE: On macOS, you may need to:")
    print("1. Install BlackHole or Loopback for system audio capture")
    print("2. Create a Multi-Output Device in Audio MIDI Setup")
    print("3. Grant microphone permissions to Terminal/Python")
    print("\nFor League of Legends audio:")
    print("- Look for 'BlackHole' or 'Loopback' device")
    print("- Or use 'Built-in Microphone' to test with your voice")
    print("=" * 60)


async def test_audio_detection(device_index: int):
    """Test Garen ability detection using audio"""
    print("\n" + "=" * 60)
    print("AUDIO-BASED ABILITY DETECTION TEST")
    print("=" * 60)
    print(f"\n🎧 Using audio device: {device_index}")
    print("🎮 Starting in 3 seconds...")
    print("Fight Garen and watch for audio detections!")
    print("Press Ctrl+C to stop\n")
    await asyncio.sleep(3)
    print("=" * 60)
    print("🔴 LISTENING...\n")

    detector = AudioAbilityDetector()

    # Start audio capture
    if not detector.start_capture(device_index=device_index):
        print("❌ Failed to start audio capture")
        print("Make sure:")
        print("1. The device index is correct")
        print("2. You have microphone permissions")
        print("3. The audio device is not in use")
        return

    frame_count = 0
    last_fps_time = time.time()
    fps = 0
    detection_count = 0

    try:
        while True:
            frame_count += 1

            # Calculate FPS
            if frame_count % 30 == 0:
                now = time.time()
                fps = 30 / (now - last_fps_time)
                last_fps_time = now

            # Test all ability detections
            garen_q = detector.detect_garen_q()
            garen_w = detector.detect_garen_w()
            garen_e_result = detector.detect_garen_e()
            garen_r = detector.detect_garen_r()

            # Get cooldowns
            cooldowns = detector.get_ability_cooldowns()

            # Display info
            q_status = f"Q:{'✓' if garen_q else '-'}({cooldowns['Q']:.0f}s)"
            w_status = f"W:{'✓' if garen_w else '-'}({cooldowns['W']:.0f}s)"
            e_status = f"E:{'SPIN!' if garen_e_result['spinning'] else '-'}({cooldowns['E']:.0f}s)"
            r_status = f"R:{'✓' if garen_r else '-'}({cooldowns['R']:.0f}s)"

            print(f"\r[{fps:.0f} Hz] {q_status} | {w_status} | {e_status} | {r_status} | Frames:{frame_count}",
                  end='', flush=True)

            # Count detections
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

                print(f"\n🎯 DETECTED: {ability_name}")

            # Run at ~30 Hz
            await asyncio.sleep(0.033)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("✅ Test stopped")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  Total frames: {frame_count}")
        print(f"  Detections: {detection_count}")
        print(f"  Log: audio_detection_test.log")
        print("\n")
    finally:
        detector.stop_capture()


async def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("GAREN AUDIO DETECTION TEST SUITE")
    print("=" * 60)
    print("\nWhat would you like to do?")
    print("1. List available audio devices")
    print("2. Test audio detection (requires device index)")
    print("\nEnter choice (1 or 2): ", end='')

    choice = input().strip()

    if choice == '1':
        await list_devices()
    elif choice == '2':
        print("\nEnter audio device index (see option 1 first): ", end='')
        device_index = input().strip()
        try:
            device_index = int(device_index)
            await test_audio_detection(device_index)
        except ValueError:
            print("❌ Invalid device index. Must be a number.")
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
