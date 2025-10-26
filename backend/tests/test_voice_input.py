#!/usr/bin/env python3
"""
Voice Input Test Script
Simulates voice input messages to test the backend without the frontend
"""

import asyncio
import websockets
import json
from datetime import datetime
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)

async def send_ability_command(ability: str, target: str = "enemy"):
    """Send an ability_used message to the backend"""
    uri = "ws://localhost:8000/ws"

    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to backend")

            # Send ability_used message
            message = {
                "type": "ability_used",
                "data": {
                    "ability": ability,
                    "target": target,
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            }

            logger.info(f"🎤 Simulating voice input: '{target} {ability}'")
            await websocket.send(json.dumps(message))
            logger.success(f"→ Sent: {json.dumps(message, indent=2)}")

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)

                if data.get("type") == "ack":
                    logger.success(f"✓ {data.get('message')}")
                elif data.get("type") == "error":
                    logger.error(f"❌ {data.get('message')}")

                logger.debug(f"← Response: {json.dumps(data, indent=2)}")

                # Check for cooldown update
                cooldown_response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                cooldown_data = json.loads(cooldown_response)

                if cooldown_data.get("type") == "cooldowns":
                    logger.info("⏱️  Updated cooldowns:")
                    cooldowns = cooldown_data['data']
                    logger.info(f"   Q: {cooldowns['Q']:.1f}s | W: {cooldowns['W']:.1f}s | E: {cooldowns['E']:.1f}s | R: {cooldowns['R']:.1f}s")

            except asyncio.TimeoutError:
                logger.warning("No response received (timeout)")

    except websockets.exceptions.ConnectionRefused:
        logger.error("❌ Connection refused. Is the backend running?")
        logger.info("Start the backend with: python main.py")
    except Exception as e:
        logger.error(f"Error: {e}")

async def interactive_mode():
    """Interactive mode for testing multiple commands"""
    print("\n" + "=" * 80)
    print("Voice Input Test - Interactive Mode")
    print("=" * 80)
    print("\nCommands:")
    print("  q, w, e, r     - Test basic abilities")
    print("  flash, ignite  - Test summoner spells")
    print("  quit, exit     - Exit interactive mode\n")

    while True:
        try:
            command = input("\nEnter ability > ").strip().lower()

            if command in ['quit', 'exit', 'q']:
                logger.info("Exiting...")
                break

            if not command:
                continue

            # Map common inputs
            ability_map = {
                'q': 'Q', 'w': 'W', 'e': 'E', 'r': 'R',
                'ult': 'R', 'ultimate': 'R',
                'flash': 'Flash', 'ignite': 'Ignite',
                'tp': 'Teleport', 'teleport': 'Teleport'
            }

            ability = ability_map.get(command, command.upper())
            await send_ability_command(ability)

        except KeyboardInterrupt:
            logger.info("\n✓ Exiting...")
            break

async def quick_test():
    """Run a quick test of all basic abilities"""
    print("\n" + "=" * 80)
    print("Voice Input Test - Quick Test Mode")
    print("=" * 80)
    print("\nTesting all basic abilities in sequence...\n")

    abilities = ['Q', 'W', 'E', 'R']

    for ability in abilities:
        logger.info(f"\nTesting {ability}...")
        await send_ability_command(ability)
        await asyncio.sleep(1)

    logger.success("\n✓ Quick test complete!")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Quick test mode
            asyncio.run(quick_test())
        else:
            # Single command mode
            ability = sys.argv[1].upper()
            asyncio.run(send_ability_command(ability))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())
