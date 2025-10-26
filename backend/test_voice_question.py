#!/usr/bin/env python3
"""
Test script to send a voice question to the backend WebSocket
"""
import asyncio
import websockets
import json

async def test_voice_question():
    uri = "ws://localhost:8000/ws"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to backend WebSocket")

            # Send a test voice question
            test_question = {
                "type": "voice_question",
                "data": {
                    "text": "Should I recall?",
                    "timestamp": 1234567890
                }
            }

            print(f"📤 Sending test question: {test_question}")
            await websocket.send(json.dumps(test_question))

            # Wait for response
            print("⏳ Waiting for response...")
            response = await websocket.recv()
            print(f"📥 Received response: {response}")

            # Parse and display
            data = json.loads(response)
            if data.get("type") == "command":
                print(f"\n✅ Got coaching command!")
                print(f"   Icon: {data['data']['icon']}")
                print(f"   Message: {data['data']['message']}")
                print(f"   Priority: {data['data']['priority']}")
            else:
                print(f"\n❓ Got response: {data}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_voice_question())
