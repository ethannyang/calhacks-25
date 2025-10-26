#!/usr/bin/env python3
"""
WebSocket Debug Client
Connects to the backend WebSocket and displays all messages in real-time
"""

import asyncio
import websockets
import json
from datetime import datetime
from loguru import logger
import sys

# Configure logger for nice output
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="DEBUG"
)

async def debug_websocket():
    uri = "ws://localhost:8000/ws"

    logger.info(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            logger.success("✓ Connected to backend WebSocket")
            logger.info("Waiting for messages... (Press Ctrl+C to stop)")
            logger.info("-" * 80)

            # Send initial config
            config_msg = {
                "type": "config",
                "data": {
                    "clientVersion": "debug-0.1.0",
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            }
            await websocket.send(json.dumps(config_msg))
            logger.debug(f"→ Sent: {json.dumps(config_msg, indent=2)}")

            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")

                    # Pretty print based on message type
                    if msg_type == "command":
                        logger.info("=" * 80)
                        logger.warning(f"📢 COACHING COMMAND")
                        logger.info(f"   Priority: {data['data']['priority']}")
                        logger.info(f"   Category: {data['data']['category']}")
                        logger.info(f"   Icon: {data['data']['icon']}")
                        logger.info(f"   Message: {data['data']['message']}")
                        logger.info(f"   Duration: {data['data']['duration']}s")
                        logger.info("=" * 80)

                    elif msg_type == "cooldowns":
                        logger.success("⏱️  COOLDOWN UPDATE")
                        cooldowns = data['data']
                        logger.info(f"   Q: {cooldowns['Q']:.1f}s | W: {cooldowns['W']:.1f}s | E: {cooldowns['E']:.1f}s | R: {cooldowns['R']:.1f}s")

                    elif msg_type == "ack":
                        logger.success(f"✓ ACK: {data.get('message', 'acknowledged')}")

                    elif msg_type == "error":
                        logger.error(f"❌ ERROR: {data.get('message', 'unknown error')}")

                    else:
                        logger.debug(f"← Received: {json.dumps(data, indent=2)}")

                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message: {message}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    logger.debug(f"Raw message: {message}")

    except websockets.exceptions.ConnectionRefused:
        logger.error("❌ Connection refused. Is the backend running?")
        logger.info("Start the backend with: python main.py")
    except Exception as e:
        logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("WebSocket Debug Client")
    print("=" * 80)
    print("\nThis script connects to the backend and displays all WebSocket messages.")
    print("Use this to debug voice input and see what the backend receives.\n")

    try:
        asyncio.run(debug_websocket())
    except KeyboardInterrupt:
        logger.info("\n✓ Debug client stopped")
