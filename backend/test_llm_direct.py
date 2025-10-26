#!/usr/bin/env python3
"""
Test the LLM engine directly
"""
import asyncio
import os
from dotenv import load_dotenv
from src.ai_engine.llm_engine import LLMEngine

load_dotenv()

async def test():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"API Key: {anthropic_key[:20]}..." if anthropic_key else "No API key!")

    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return

    llm = LLMEngine(anthropic_key)

    try:
        print("\n🧪 Testing answer_coaching_question...")
        response = await llm.answer_coaching_question("Should I recall?", None)

        if response:
            print(f"\n✅ Got response!")
            print(f"   Icon: {response.icon}")
            print(f"   Message: {response.message}")
            print(f"   Priority: {response.priority}")
        else:
            print("\n❌ Got None response")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
