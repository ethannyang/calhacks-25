"""
Main Game Loop - Integrates capture, OCR, AI engines, and WebSocket broadcasting
Runs continuously while League of Legends is active
"""

import asyncio
import time
import os
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

from src.capture.macos import MacOSCapture
from src.ocr.extractor import GameDataExtractor
from src.models.game_state import (
    GameState, GamePhase, PlayerState, ChampionState,
    ObjectiveState, WaveState, VisionState, CoachingCommand
)
from src.ai_engine.rule_engine import RuleEngine
from src.ai_engine.llm_engine import LLMEngine
from src.ai_engine.command_manager import CommandManager
from src.riot_api.client import RiotAPIClient
from src.riot_api.live_game_manager import LiveGameManager

# Load environment variables
load_dotenv()


class GameLoop:
    """Main game loop coordinator"""

    def __init__(self):
        self.capture = MacOSCapture()
        self.extractor = GameDataExtractor()
        self.rule_engine = RuleEngine()
        self.command_manager = CommandManager()

        # Initialize LLM engine
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            logger.warning("ANTHROPIC_API_KEY not set, LLM coaching disabled")
            self.llm_engine = None
        else:
            self.llm_engine = LLMEngine(anthropic_key)

        # Initialize Riot API and LiveGameManager
        riot_api_key = os.getenv("RIOT_API_KEY")
        riot_region = os.getenv("RIOT_REGION", "na1")
        game_name = os.getenv("RIOT_GAME_NAME")
        tag_line = os.getenv("RIOT_TAG_LINE")

        self.riot_client = None
        self.live_game_mgr = None

        if riot_api_key and game_name and tag_line:
            self.riot_client = RiotAPIClient(riot_api_key, riot_region)
            self.live_game_mgr = LiveGameManager(self.riot_client, game_name, tag_line)
            logger.info(f"Riot API integration enabled for {game_name}#{tag_line}")
        else:
            logger.warning("Riot API credentials incomplete, live game tracking disabled")

        # Configuration
        self.capture_fps = float(os.getenv("CAPTURE_FPS", "1"))
        self.capture_interval = 1.0 / self.capture_fps

        # LLM runs less frequently (every 2.5 seconds for faster response)
        self.llm_interval = 2.5
        self.last_llm_time = 0

        # Live API fetch interval (every 10 seconds)
        self.live_api_interval = 10.0
        self.last_live_api_time = 0

        # State
        self.running = False
        self.game_detected = False
        self.frame_count = 0
        self.live_game_initialized = False

        # WebSocket callback (set externally)
        self.on_command = None

    def set_command_callback(self, callback):
        """Set callback for broadcasting coaching commands"""
        self.on_command = callback

    def _determine_game_phase(self, game_time: int) -> GamePhase:
        """Determine game phase based on time"""
        if game_time < 900:  # 15 minutes
            return GamePhase.EARLY
        elif game_time < 1500:  # 25 minutes
            return GamePhase.MID
        else:
            return GamePhase.LATE

    def _build_game_state(self, game_data: dict, frame_time: float) -> Optional[GameState]:
        """
        Build GameState from OCR extracted data + LiveGameManager context
        """
        # Validate required fields
        game_time = game_data.get('game_time')
        if game_time is None:
            logger.warning("Missing game_time, cannot build game state")
            return None

        # Get live game context if available
        live_context = {}
        if self.live_game_mgr and self.live_game_mgr.is_in_game():
            live_context = self.live_game_mgr.get_context_summary()

        # Build player state with live game data
        champion_name = live_context.get('player', {}).get('champion', 'Unknown')
        player_role = live_context.get('player', {}).get('role', 'unknown')

        player = PlayerState(
            champion_name=champion_name,
            summoner_name="Player",
            level=10,  # Mock data
            hp=int(game_data.get('hp_percent', 100)),
            hp_max=100,
            mana=int(game_data.get('mana_percent', 100)),
            mana_max=100,
            gold=game_data.get('gold', 0),
            cs=game_data.get('cs', 0),
            kills=0,
            deaths=0,
            assists=0
        )

        # Build objectives (mock data for now)
        objectives = ObjectiveState(
            dragon_spawn_time=None,
            baron_spawn_time=None,
            herald_spawn_time=None,
            dragons_killed_team=0,
            dragons_killed_enemy=0
        )

        # Build wave state (mock data)
        wave = WaveState(
            allied_minions=3,
            enemy_minions=3,
            cannon_wave=False,
            wave_position="mid"
        )

        # Build vision state (mock data)
        vision = VisionState(
            enemy_visible_count=2,
            enemy_missing_count=3,
            allied_wards_active=2
        )

        # Build full game state
        game_state = GameState(
            game_time=game_time,
            game_phase=self._determine_game_phase(game_time),
            player=player,
            team_score=5,
            enemy_score=5,
            team_towers=10,
            enemy_towers=10,
            team_gold_lead=0,
            allies=[],
            enemies=[],
            objectives=objectives,
            wave=wave,
            vision=vision,
            timestamp=frame_time
        )

        return game_state

    async def process_frame(self):
        """Process a single frame: capture -> OCR -> AI -> broadcast"""
        try:
            frame_start = time.time()

            # 1. Capture game window
            frame = self.capture.capture_game()
            if frame is None:
                if self.game_detected:
                    logger.warning("Lost game window")
                    self.game_detected = False
                return

            if not self.game_detected:
                logger.info("Game window detected!")
                self.game_detected = True
                # Setup ROIs on first detection
                self.capture.setup_lol_rois(frame.shape[1], frame.shape[0])

            # 2. Extract ROIs
            roi_extracts = self.capture.extract_rois(frame)

            # 3. Run OCR
            game_data = self.extractor.extract_game_data(roi_extracts)
            logger.debug(f"OCR Data: Gold={game_data.get('gold')}, CS={game_data.get('cs')}, "
                        f"Time={game_data.get('game_time')}s, HP={game_data.get('hp_percent'):.1f}%")

            # 4. Build game state
            game_state = self._build_game_state(game_data, frame_start)
            if game_state is None:
                return

            # 5. Check for item-based recall recommendations (HIGH priority)
            recall_command = None
            if self.live_game_mgr and self.live_game_mgr.is_in_game():
                recall_rec = self.live_game_mgr.get_recall_recommendation(game_state.player.gold)
                if recall_rec:
                    recall_command = CoachingCommand(
                        priority=recall_rec['priority'],
                        category="recall",
                        icon="🛒",
                        message=recall_rec['message'],
                        duration=8,
                        timestamp=time.time()
                    )

            # 6. Run rule engine (fast, always runs)
            rule_command = self.rule_engine.process(game_state)

            # 7. Run LLM engine (slower, periodic) with live game context
            llm_command = None
            if self.llm_engine and time.time() - self.last_llm_time >= self.llm_interval:
                self.last_llm_time = time.time()

                # Get live context for AI (pass player gold for build recommendations)
                live_ctx = None
                if self.live_game_mgr and self.live_game_mgr.is_in_game():
                    live_ctx = self.live_game_mgr.get_context_summary(current_gold=game_state.player.gold)

                # Try wave management coaching with enhanced context
                llm_command = await self.llm_engine.wave_management_coaching(game_state, live_ctx)

            # 8. Determine which command to use (priority: recall > LLM > rule)
            proposed_command = recall_command if recall_command else (llm_command if llm_command else rule_command)

            # 8. Use CommandManager to decide if we should issue this command
            if proposed_command:
                should_issue = self.command_manager.should_issue_command(proposed_command, game_state)
                if should_issue:
                    # Get the actual command to broadcast (might be completion message)
                    command_to_send = self.command_manager.get_current_command()
                    if command_to_send and self.on_command:
                        await self.on_command(command_to_send)
                        logger.info(f"📢 Command: [{command_to_send.priority}] {command_to_send.message}")

            # Performance metrics
            frame_time = (time.time() - frame_start) * 1000
            self.frame_count += 1
            logger.debug(f"Frame {self.frame_count} processed in {frame_time:.0f}ms")

        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)

    async def run(self):
        """Main game loop - runs continuously"""
        self.running = True
        logger.info(f"🎮 Game loop started (FPS: {self.capture_fps})")

        # Initialize LiveGameManager if available
        if self.live_game_mgr and not self.live_game_initialized:
            try:
                await self.live_game_mgr.initialize()
                self.live_game_initialized = True
                logger.info("✅ LiveGameManager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LiveGameManager: {e}")
                self.live_game_mgr = None

        try:
            while self.running:
                loop_start = time.time()

                # Fetch live game data periodically
                if self.live_game_mgr and time.time() - self.last_live_api_time >= self.live_api_interval:
                    self.last_live_api_time = time.time()
                    try:
                        in_game = await self.live_game_mgr.fetch_live_game()
                        if in_game:
                            logger.debug(f"Live game data updated - Role: {self.live_game_mgr.player_role}, "
                                       f"Champion: {self.live_game_mgr.player_champion_name}")
                    except Exception as e:
                        logger.error(f"Error fetching live game data: {e}")

                # Process one frame
                await self.process_frame()

                # Sleep to maintain target FPS
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.capture_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Game loop interrupted by user")
        except Exception as e:
            logger.error(f"Game loop error: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("🛑 Game loop stopped")

    def stop(self):
        """Stop the game loop"""
        self.running = False


async def main():
    """Standalone test of game loop (no WebSocket)"""
    logger.info("Starting standalone game loop test...")

    game_loop = GameLoop()

    # Mock callback for testing
    async def mock_command_callback(command: CoachingCommand):
        print(f"\n{'='*60}")
        print(f"🎯 COACHING COMMAND")
        print(f"Priority: {command.priority.upper()}")
        print(f"Category: {command.category}")
        print(f"Message: {command.icon} {command.message}")
        print(f"{'='*60}\n")

    game_loop.set_command_callback(mock_command_callback)

    try:
        await game_loop.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        game_loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
