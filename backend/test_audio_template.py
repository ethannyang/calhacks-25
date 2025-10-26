"""
Test template-based audio detection for Garen abilities
Uses actual ability sound files for accurate matching
"""

import asyncio
import time
from src.combat_vision.audio_template_detector import AudioTemplateDetector
from loguru import logger

# Setup logging
logger.add("audio_template_test.log", rotation="10 MB")

# Path to audio template files
AUDIO_FILES = {
    'Q': '/Users/ethan/Desktop/projects/calhacks-25/GarenQ.wav',
    'W': '/Users/ethan/Desktop/projects/calhacks-25/GarenW.wav',
    'E': '/Users/ethan/Desktop/projects/calhacks-25/GarenE.wav',
    'R': '/Users/ethan/Desktop/projects/calhacks-25/GarenR.wav'
}


async def list_devices():
    """List all available audio devices"""
    print("\n" + "=" * 60)
    print("AUDIO DEVICE DETECTION")
    print("=" * 60)
    print("\nScanning for audio devices...\n")

    AudioTemplateDetector.list_audio_devices()

    print("\n" + "=" * 60)
    print("\n⚠️  IMPORTANT - macOS Audio Capture Setup:")
    print("=" * 60)
    print("\nTo capture League of Legends audio, you need:")
    print("\n1. Install BlackHole (free virtual audio device):")
    print("   brew install blackhole-2ch")
    print("\n2. Open 'Audio MIDI Setup' app")
    print("   - Create a Multi-Output Device")
    print("   - Add: Built-in Output + BlackHole 2ch")
    print("   - Set as System Output")
    print("\n3. In League of Legends:")
    print("   - Go to Sound Settings")
    print("   - Ensure sound effects volume is up")
    print("\n4. Run this test and select 'BlackHole 2ch' device")
    print("\n5. Grant microphone permissions to Terminal if prompted")
    print("=" * 60)


async def test_template_detection(device_index: int, threshold: float = 0.6):
    """Test Garen ability detection using audio templates"""
    print("\n" + "=" * 60)
    print("TEMPLATE-BASED AUDIO DETECTION TEST")
    print("=" * 60)
    print(f"\n🎧 Audio device: {device_index}")
    print(f"🎯 Detection threshold: {threshold}")
    print("🎮 Loading audio templates...")

    # Initialize detector with template files
    detector = AudioTemplateDetector(
        audio_files=AUDIO_FILES,
        sample_rate=44100,
        threshold=threshold
    )

    print("\n✅ Templates loaded successfully!")
    print("\n🎮 Starting in 3 seconds...")
    print("Fight Garen and watch for ability detections!")
    print("Press Ctrl+C to stop\n")
    await asyncio.sleep(3)
    print("=" * 60)
    print("🔴 LISTENING FOR GAREN ABILITIES...\n")

    # Start audio capture
    if not detector.start_capture(device_index=device_index):
        print("❌ Failed to start audio capture")
        print("\nTroubleshooting:")
        print("1. Check that device index is correct (run option 1)")
        print("2. Grant microphone permissions to Terminal")
        print("3. If using BlackHole, ensure Multi-Output is system output")
        print("4. Close other apps using the audio device")
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

            # Detect all abilities
            garen_q = detector.detect_garen_q()
            garen_w = detector.detect_garen_w()
            garen_e_result = detector.detect_garen_e()
            garen_r = detector.detect_garen_r()

            # Get cooldowns
            cooldowns = detector.get_ability_cooldowns()

            # Display status
            q_status = f"Q:{'✓' if garen_q else '-'}({cooldowns['Q']:.0f}s)"
            w_status = f"W:{'✓' if garen_w else '-'}({cooldowns['W']:.0f}s)"
            e_status = f"E:{'SPIN!' if garen_e_result['spinning'] else '-'}({cooldowns['E']:.0f}s)"
            r_status = f"R:{'✓' if garen_r else '-'}({cooldowns['R']:.0f}s)"

            print(f"\r[{fps:.0f} Hz] {q_status} | {w_status} | {e_status} | {r_status} | Frames:{frame_count}",
                  end='', flush=True)

            # Log detections
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

                timestamp = time.strftime("%H:%M:%S")
                print(f"\n[{timestamp}] 🎯 DETECTED: {ability_name}")

            # Run at ~30 Hz
            await asyncio.sleep(0.033)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("✅ Test stopped")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  Total frames: {frame_count}")
        print(f"  Runtime: {frame_count / max(fps, 1):.1f}s")
        print(f"  Detections: {detection_count}")
        print(f"  Log file: audio_template_test.log")
        print("\n")
    finally:
        detector.stop_capture()


async def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("GAREN AUDIO TEMPLATE DETECTION TEST")
    print("=" * 60)
    print("\nUsing template matching with actual ability sounds")
    print("for highly accurate detection!\n")
    print("Options:")
    print("1. List available audio devices")
    print("2. Test detection (requires device index)")
    print("3. Test with custom threshold")
    print("\nEnter choice (1-3): ", end='')

    choice = input().strip()

    if choice == '1':
        await list_devices()

    elif choice == '2':
        print("\nEnter audio device index: ", end='')
        device_index = input().strip()
        try:
            device_index = int(device_index)
            await test_template_detection(device_index)
        except ValueError:
            print("❌ Invalid device index. Must be a number.")

    elif choice == '3':
        print("\nEnter audio device index: ", end='')
        device_index = input().strip()
        print("Enter detection threshold (0.3-0.9, default 0.6): ", end='')
        threshold = input().strip()

        try:
            device_index = int(device_index)
            threshold = float(threshold) if threshold else 0.6
            threshold = max(0.3, min(0.9, threshold))  # Clamp between 0.3-0.9
            await test_template_detection(device_index, threshold)
        except ValueError:
            print("❌ Invalid input.")

    else:
        print("❌ Invalid choice. Exiting.")


if __name__ == "__main__":
    asyncio.run(main())
