#!/usr/bin/env python3
"""
Test Voice Input for Cooldown Tracking
This script simulates voice commands to test the cooldown tracking system
"""

import asyncio
import json
import time
from websockets import connect
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


class VoiceInputTester:
    """Test voice commands for ability tracking"""

    def __init__(self, ws_url="ws://localhost:8000/ws"):
        self.ws_url = ws_url
        self.ws = None
        self.cooldowns = {'Q': 0, 'W': 0, 'E': 0, 'R': 0}

    async def connect(self):
        """Connect to backend WebSocket"""
        try:
            self.ws = await connect(self.ws_url)
            logger.info(f"✅ Connected to backend at {self.ws_url}")

            # Start listening for messages
            asyncio.create_task(self.listen_for_messages())
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for messages from backend"""
        try:
            async for message in self.ws:
                data = json.loads(message)

                if data['type'] == 'cooldowns':
                    self.cooldowns = data['data']
                    self.display_cooldowns()
                elif data['type'] == 'ack':
                    logger.success(f"✓ Backend acknowledged: {data.get('message', '')}")
                elif data['type'] == 'command':
                    # Coaching command received
                    cmd = data['data']
                    logger.info(f"📢 COACH: [{cmd['priority'].upper()}] {cmd['message']}")

        except Exception as e:
            logger.error(f"Error in message listener: {e}")

    def display_cooldowns(self):
        """Display current cooldowns in a nice format"""
        cd_display = []
        for ability, cooldown in self.cooldowns.items():
            if cooldown > 0:
                cd_display.append(f"{ability}:{cooldown:.0f}s")
            else:
                cd_display.append(f"{ability}:✓")

        logger.info(f"⏰ Cooldowns: {' | '.join(cd_display)}")

    async def simulate_voice_command(self, ability, target="Garen"):
        """Simulate a voice command being sent"""
        if not self.ws:
            logger.error("Not connected to backend")
            return

        command = {
            "type": "ability_used",
            "data": {
                "ability": ability,
                "target": target,
                "timestamp": int(time.time() * 1000)
            }
        }

        logger.info(f"🎤 Simulating voice: '{target} used {ability}'")
        await self.ws.send(json.dumps(command))

    async def run_test_sequence(self):
        """Run a test sequence of abilities"""
        logger.info("\n" + "="*60)
        logger.info("STARTING TEST SEQUENCE")
        logger.info("="*60)

        # Test individual abilities
        test_abilities = [
            ("Q", "Testing Garen Q (Decisive Strike)"),
            ("W", "Testing Garen W (Courage)"),
            ("E", "Testing Garen E (Judgment)"),
            ("R", "Testing Garen R (Demacian Justice)")
        ]

        for ability, description in test_abilities:
            logger.info(f"\n📝 {description}")
            await self.simulate_voice_command(ability)
            await asyncio.sleep(2)

        logger.info("\n" + "="*60)
        logger.info("Now tracking cooldowns...")
        logger.info("="*60)

        # Watch cooldowns tick down
        for i in range(10):
            await asyncio.sleep(1)
            # Request cooldown update
            await self.ws.send(json.dumps({
                "type": "get_cooldowns"
            }))

    async def interactive_mode(self):
        """Interactive testing mode"""
        logger.info("\n" + "="*60)
        logger.info("INTERACTIVE VOICE TESTING MODE")
        logger.info("="*60)
        logger.info("Commands you can type:")
        logger.info("  q/w/e/r - Report that ability was used")
        logger.info("  all     - Use all abilities at once")
        logger.info("  status  - Show current cooldowns")
        logger.info("  clear   - Clear console")
        logger.info("  exit    - Quit")
        logger.info("="*60 + "\n")

        while True:
            try:
                # Get user input
                cmd = input("Enter command (q/w/e/r/all/status/exit): ").strip().lower()

                if cmd == 'exit':
                    break
                elif cmd == 'clear':
                    print("\033[H\033[J")  # Clear terminal
                elif cmd == 'status':
                    self.display_cooldowns()
                elif cmd == 'all':
                    logger.info("🔥 Using all abilities!")
                    for ability in ['Q', 'W', 'E', 'R']:
                        await self.simulate_voice_command(ability)
                        await asyncio.sleep(0.5)
                elif cmd in ['q', 'w', 'e', 'r']:
                    await self.simulate_voice_command(cmd.upper())
                elif cmd == '':
                    continue
                else:
                    logger.warning(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")

        logger.info("\n👋 Exiting interactive mode")


async def main():
    """Main test function"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     Voice Input & Cooldown Tracking Test Suite          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  This tool tests the voice input → cooldown pipeline    ║
    ║  Make sure the backend is running on port 8000          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Check if backend is running
    logger.info("Checking backend connection...")

    tester = VoiceInputTester()
    connected = await tester.connect()

    if not connected:
        logger.error("❌ Could not connect to backend!")
        logger.info("Make sure to run: python main.py")
        return

    # Give connection time to stabilize
    await asyncio.sleep(1)

    # Choose test mode
    print("\nSelect test mode:")
    print("1. Automated test sequence")
    print("2. Interactive mode")
    print("3. Exit")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == '1':
        await tester.run_test_sequence()
        # Keep running to see cooldowns
        logger.info("\nPress Ctrl+C to exit...")
        try:
            await asyncio.sleep(120)  # Run for 2 minutes
        except KeyboardInterrupt:
            pass
    elif choice == '2':
        await tester.interactive_mode()

    # Cleanup
    if tester.ws:
        await tester.ws.close()
    logger.info("✅ Test complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")