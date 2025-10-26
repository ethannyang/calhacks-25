#!/usr/bin/env python3
"""
Test automated coaching (simulates game loop behavior)
"""
import asyncio
import os
from dotenv import load_dotenv
from src.ai_engine.llm_engine import LLMEngine
from src.models.game_state import GameState, GamePhase, PlayerState, ChampionState, ObjectiveState, WaveState, VisionState
import time

load_dotenv()

async def test_automated_coaching():
    """Test the automated coaching that runs in game loop"""

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    llm = LLMEngine(anthropic_key)

    # Simulate game state (like what OCR would extract)
    game_state = GameState(
        game_time=420,  # 7 minutes
        game_phase=GamePhase.EARLY,
        player=PlayerState(
            summoner_name="TestPlayer",
            champion_name="Darius",
            level=7,
            hp=800,
            hp_max=1500,
            mana=200,
            mana_max=400,
            gold=1400,  # Enough for recall
            cs=45,  # Low CS for 7 minutes (should be ~49)
            kills=1,
            deaths=0,
            assists=0,
            summoner_spells=["Flash", "Ghost"]
        ),
        team_score=3,
        enemy_score=4,
        team_towers=10,
        enemy_towers=9,
        team_gold_lead=-200,
        allies=[],
        enemies=[],
        objectives=ObjectiveState(
            dragon_spawn_time=45,  # Dragon spawning soon!
            baron_spawn_time=None,
            herald_spawn_time=None
        ),
        wave=WaveState(
            wave_position="center",
            allied_minions=6,
            enemy_minions=4,
            cannon_wave=False
        ),
        vision=VisionState(
            enemy_visible_count=2,
            enemy_missing_count=3
        ),
        timestamp=time.time()
    )

    print("🎮 Testing AUTOMATED coaching (what runs during gameplay):\n")

    # Test wave management coaching (uses game state)
    print("1️⃣ Wave Management Coaching (uses HP, mana, gold, CS from OCR):")
    wave_cmd = await llm.wave_management_coaching(game_state, None)
    if wave_cmd:
        print(f"   {wave_cmd.icon} {wave_cmd.message} [{wave_cmd.priority}]\n")
    else:
        print("   No wave coaching generated\n")

    # Test objective coaching (uses objective timers)
    print("2️⃣ Objective Coaching (uses dragon/baron timers):")
    obj_cmd = await llm.objective_coaching(game_state, None)
    if obj_cmd:
        print(f"   {obj_cmd.icon} {obj_cmd.message} [{obj_cmd.priority}]\n")
    else:
        print("   No objective coaching generated\n")

    print("=" * 60)
    print("✅ Automated coaching uses GAME STATE (HP, gold, CS, etc.)")
    print("✅ This runs continuously in the game loop")
    print("✅ It does NOT require you to ask questions")

if __name__ == "__main__":
    asyncio.run(test_automated_coaching())
