#!/usr/bin/env python3
"""
Test multiple voice questions
"""
import asyncio
import websockets
import json

async def test_question(question):
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        msg = {"type": "voice_question", "data": {"text": question, "timestamp": 123}}
        await websocket.send(json.dumps(msg))
        response = await websocket.recv()
        data = json.loads(response)
        if data.get("type") == "command":
            print(f"Q: {question}")
            print(f"A: {data['data']['icon']} {data['data']['message']}\n")

async def main():
    questions = [
        "Should I recall?",
        "When should I roam?",
        "How do I beat Garen?",
        "What should I build?",
        "How do I farm better?",
        "When should I trade?",
        "Where should I ward?",
        "What do I do now?"
    ]

    for q in questions:
        await test_question(q)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
