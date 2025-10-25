"""
Test script for LiveGameManager
Run this to verify live game detection works

Usage:
    python test_live_game.py
"""

import asyncio
import os
from dotenv import load_dotenv
from loguru import logger

from src.riot_api.client import RiotAPIClient
from src.riot_api.live_game_manager import LiveGameManager


async def main():
    # Load environment variables
    load_dotenv()

    api_key = os.getenv('RIOT_API_KEY')
    region = os.getenv('RIOT_REGION', 'na1')
    game_name = os.getenv('RIOT_GAME_NAME')
    tag_line = os.getenv('RIOT_TAG_LINE')

    if not api_key:
        logger.error("❌ RIOT_API_KEY not found in .env")
        return

    if not game_name or not tag_line:
        logger.error("❌ RIOT_GAME_NAME and RIOT_TAG_LINE not found in .env")
        return

    logger.info(f"🔍 Testing LiveGameManager for: {game_name}#{tag_line} ({region})")
    logger.info("=" * 60)

    # Initialize Riot API client
    async with RiotAPIClient(api_key=api_key, region=region) as riot_client:

        # Initialize LiveGameManager
        live_mgr = LiveGameManager(riot_client, game_name, tag_line)

        try:
            await live_mgr.initialize()
        except ValueError as e:
            logger.error(f"❌ Initialization failed: {e}")
            return

        logger.info("")
        logger.info("✅ LiveGameManager initialized successfully!")
        logger.info("")
        logger.info("📊 Static Data Loaded:")
        logger.info(f"   - Champions: {len(live_mgr.champion_data.get('data', {}))}")
        logger.info(f"   - Items: {len(live_mgr.item_data.get('data', {}))}")
        logger.info(f"   - Summoner Spells: {len(live_mgr.spell_data.get('data', {}))}")
        logger.info("")

        # Check for active game
        logger.info("🎮 Checking for active game...")
        in_game = await live_mgr.fetch_live_game(force=True)

        if not in_game:
            logger.warning("❌ No active game found")
            logger.info("")
            logger.info("💡 To test:")
            logger.info("   1. Start a League of Legends game")
            logger.info("   2. Run this script again")
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info("🎮 ACTIVE GAME DETECTED!")
        logger.info("=" * 60)
        logger.info("")

        # Display player info
        logger.info("👤 Your Info:")
        logger.info(f"   Role: {live_mgr.player_role}")
        logger.info(f"   Champion: {live_mgr.player_champion_name}")
        logger.info(f"   Champion ID: {live_mgr.player_champion_id}")
        logger.info("")

        # Display game info
        logger.info("🎯 Game Info:")
        logger.info(f"   Mode: {live_mgr.get_game_mode()}")
        logger.info(f"   Time: {live_mgr.get_game_time()}s")
        logger.info("")

        # Display allies
        logger.info("🟦 Your Team:")
        for ally in live_mgr.ally_participants:
            spell1_name = live_mgr.get_summoner_spell_name(ally['spell1_id'])
            spell2_name = live_mgr.get_summoner_spell_name(ally['spell2_id'])
            logger.info(
                f"   [{ally['role']:7s}] {ally['champion_name']:15s} - "
                f"{spell1_name}/{spell2_name}"
            )
        logger.info("")

        # Display enemies
        logger.info("🟥 Enemy Team:")
        for enemy in live_mgr.enemy_participants:
            spell1_name = live_mgr.get_summoner_spell_name(enemy['spell1_id'])
            spell2_name = live_mgr.get_summoner_spell_name(enemy['spell2_id'])
            logger.info(
                f"   [{enemy['role']:7s}] {enemy['champion_name']:15s} - "
                f"{spell1_name}/{spell2_name}"
            )
        logger.info("")

        # Display strategic info
        enemy_jungler = live_mgr.get_enemy_jungler()
        enemy_laner = live_mgr.get_enemy_laner()

        logger.info("🎯 Strategic Info:")
        if enemy_jungler:
            logger.info(f"   Enemy Jungler: {enemy_jungler['champion_name']}")
        else:
            logger.info("   Enemy Jungler: Not detected")

        if enemy_laner:
            logger.info(f"   Your Lane Opponent: {enemy_laner['champion_name']}")
        else:
            logger.info("   Your Lane Opponent: Not detected")
        logger.info("")

        # Display AI context
        context = live_mgr.get_context_summary()
        logger.info("🤖 AI Context Summary:")
        logger.info(f"   {context}")
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ Test completed successfully!")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
