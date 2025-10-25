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

# Load environment variables
load_dotenv()


class GameLoop:
    """Main game loop coordinator"""

    def __init__(self):
        self.capture = MacOSCapture()
        self.extractor = GameDataExtractor()
        self.rule_engine = RuleEngine()

        # Initialize LLM engine
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            logger.warning("ANTHROPIC_API_KEY not set, LLM coaching disabled")
            self.llm_engine = None
        else:
            self.llm_engine = LLMEngine(anthropic_key)

        # Configuration
        self.capture_fps = float(os.getenv("CAPTURE_FPS", "1"))
        self.capture_interval = 1.0 / self.capture_fps

        # LLM runs less frequently (every 5 seconds)
        self.llm_interval = 5.0
        self.last_llm_time = 0

        # State
        self.running = False
        self.game_detected = False
        self.frame_count = 0

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
        Build GameState from OCR extracted data
        Note: This is simplified - in production you'd integrate with Riot API
        """
        # Validate required fields
        game_time = game_data.get('game_time')
        if game_time is None:
            logger.warning("Missing game_time, cannot build game state")
            return None

        # Build player state (simplified)
        player = PlayerState(
            champion_name="Unknown",  # Would come from Riot API
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

            # 5. Run rule engine (fast, always runs)
            command = self.rule_engine.process(game_state)

            # 6. Run LLM engine (slower, periodic)
            if self.llm_engine and time.time() - self.last_llm_time >= self.llm_interval:
                self.last_llm_time = time.time()

                # Try wave management coaching
                llm_command = await self.llm_engine.wave_management_coaching(game_state)
                if llm_command:
                    command = llm_command  # Override with LLM command if available

            # 7. Broadcast command if available
            if command and self.on_command:
                await self.on_command(command)
                logger.info(f"📢 Command: [{command.priority}] {command.message}")

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

        try:
            while self.running:
                loop_start = time.time()

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
