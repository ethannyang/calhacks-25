#!/usr/bin/env python
"""
End-to-end test of the capture → OCR → game state pipeline
"""

import asyncio
import time
from game_loop import GameLoop
from loguru import logger
import json

async def test_pipeline():
    """Test the complete capture → OCR → game state pipeline"""
    print("=" * 60)
    print("Testing Complete Pipeline: Capture → OCR → Game State")
    print("=" * 60)

    # Initialize game loop
    print("\n🎮 Initializing game loop...")
    loop = GameLoop()

    # Test 1: Window Detection
    print("\n[Test 1] Window Detection")
    print("-" * 40)
    window_info = loop.capture.find_game_window()
    if window_info:
        print(f"✅ Found window: {window_info.app_name}")
        print(f"   Resolution: {window_info.bounds[2]}x{window_info.bounds[3]}")
    else:
        print("❌ No League window found")
        print("   Please start League of Legends and enter a match")
        return

    # Test 2: Frame Capture
    print("\n[Test 2] Frame Capture")
    print("-" * 40)
    frame = loop.capture.capture_game()
    if frame is not None:
        print(f"✅ Captured frame: {frame.shape[1]}x{frame.shape[0]}")
    else:
        print("❌ Failed to capture frame")
        return

    # Test 3: ROI Setup
    print("\n[Test 3] ROI Configuration")
    print("-" * 40)
    loop.capture.setup_lol_rois(frame.shape[1], frame.shape[0])
    print(f"✅ Configured {len(loop.capture.rois)} ROIs:")
    for roi in loop.capture.rois:
        print(f"   - {roi.name:12} : ({roi.x}, {roi.y}) {roi.width}x{roi.height}")

    # Test 4: ROI Extraction
    print("\n[Test 4] ROI Extraction")
    print("-" * 40)
    roi_extracts = loop.capture.extract_rois(frame)
    extracted_count = sum(1 for v in roi_extracts.values() if v is not None)
    print(f"✅ Extracted {extracted_count}/{len(roi_extracts)} ROIs successfully")

    # Test 5: OCR Processing
    print("\n[Test 5] OCR Processing")
    print("-" * 40)
    game_data = loop.extractor.extract_game_data(roi_extracts)

    print("OCR Results:")
    for key, value in game_data.items():
        status = "✅" if value is not None else "❌"
        print(f"   {status} {key:12} : {value}")

    # Test 6: Game State Building
    print("\n[Test 6] Game State Building")
    print("-" * 40)
    game_state = loop._build_game_state(game_data, time.time())

    if game_state:
        print("✅ Game state successfully built:")
        print(f"   Game Time: {game_state.game_time}s ({game_state.game_time // 60}:{game_state.game_time % 60:02d})")
        print(f"   Phase: {game_state.game_phase}")
        print(f"   Player: {game_state.player.champion_name} (Level {game_state.player.level})")
        print(f"   KDA: {game_state.player.kills}/{game_state.player.deaths}/{game_state.player.assists}")
        print(f"   Gold: {game_state.player.gold}")
        print(f"   CS: {game_state.player.cs}")
        print(f"   HP: {game_state.player.hp}%")
        print(f"   Mana: {game_state.player.mana}%")
    else:
        print("❌ Failed to build game state")

    # Test 7: Full Frame Processing
    print("\n[Test 7] Full Frame Processing (with AI)")
    print("-" * 40)

    # Set up a callback to capture commands
    commands_received = []
    def on_command(command):
        commands_received.append(command)

    loop.on_command = on_command

    # Process one frame
    start_time = time.time()
    await loop.process_frame()
    elapsed = (time.time() - start_time) * 1000

    print(f"✅ Frame processed in {elapsed:.1f}ms")

    if commands_received:
        print(f"   Generated {len(commands_received)} coaching command(s):")
        for cmd in commands_received:
            if hasattr(cmd, 'to_dict'):
                cmd_dict = cmd.to_dict()
                print(f"   - [{cmd_dict['priority']}] {cmd_dict['message']}")

    # Test 8: Performance Test
    print("\n[Test 8] Performance Test (10 frames)")
    print("-" * 40)

    frame_times = []
    for i in range(10):
        start = time.time()
        await loop.process_frame()
        frame_time = (time.time() - start) * 1000
        frame_times.append(frame_time)
        print(f"   Frame {i+1}: {frame_time:.1f}ms")

    avg_time = sum(frame_times) / len(frame_times)
    max_time = max(frame_times)
    min_time = min(frame_times)

    print(f"\n📊 Performance Summary:")
    print(f"   Average: {avg_time:.1f}ms")
    print(f"   Min: {min_time:.1f}ms")
    print(f"   Max: {max_time:.1f}ms")
    print(f"   Target: <500ms {'✅' if avg_time < 500 else '❌'}")

    # Final Summary
    print("\n" + "=" * 60)
    print("Pipeline Test Summary")
    print("=" * 60)

    # Check what's working
    working = []
    issues = []

    if window_info:
        working.append("Window detection")
    else:
        issues.append("Cannot find League window")

    if frame is not None:
        working.append("Frame capture")
    else:
        issues.append("Cannot capture frames")

    if extracted_count > 0:
        working.append(f"ROI extraction ({extracted_count} regions)")
    else:
        issues.append("ROI extraction failing")

    ocr_working = sum(1 for v in game_data.values() if v is not None)
    if ocr_working > 0:
        working.append(f"OCR extraction ({ocr_working} fields)")
    else:
        issues.append("OCR not extracting any data")

    if game_state:
        working.append("Game state building")
    else:
        issues.append("Cannot build game state")

    if avg_time < 500:
        working.append(f"Performance ({avg_time:.0f}ms avg)")
    else:
        issues.append(f"Performance too slow ({avg_time:.0f}ms)")

    print("\n✅ Working:")
    for item in working:
        print(f"   - {item}")

    if issues:
        print("\n❌ Issues:")
        for issue in issues:
            print(f"   - {issue}")

    # Recommendations
    print("\n💡 Next Steps:")
    if not issues:
        print("   ✨ Pipeline is fully functional!")
        print("   1. Run main.py to start the coaching overlay")
        print("   2. The system should now use real game data")
    elif ocr_working == 0:
        print("   1. Run calibrate_rois.py to check ROI alignment")
        print("   2. Adjust ROI coordinates in capture/base.py")
        print("   3. Check game UI scale settings in League")
    elif ocr_working < 3:
        print("   1. Some OCR is working - check which fields")
        print("   2. Adjust preprocessing for failing fields")
        print("   3. Consider different OCR configs for different regions")
    else:
        print("   1. OCR is working but game state has issues")
        print("   2. Check _build_game_state logic in game_loop.py")
        print("   3. Ensure required fields are being extracted")

if __name__ == "__main__":
    try:
        asyncio.run(test_pipeline())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()