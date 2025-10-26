"""
Game state monitoring service
Captures screen, extracts game data, and generates coaching commands
"""

import asyncio
import time
import os
from typing import Optional, Dict, Any, Union
from loguru import logger
import numpy as np
from dotenv import load_dotenv

from ..capture import get_capture
from ..ocr.extractor import GameDataExtractor
from ..ai_engine.rule_engine import RuleEngine
from ..ai_engine.llm_engine import LLMEngine
from ..models.game_state import (
    GameState, PlayerState, GamePhase,
    ObjectiveState, WaveState, VisionState, CoachingCommand, DirectiveV1, DirectivePrimary
)

# Load environment variables
load_dotenv()


class GameMonitor:
    """Monitors game state and generates coaching commands"""

    def __init__(self, capture_fps: float = 1.0, use_llm: bool = True):
        """
        Initialize game monitor

        Args:
            capture_fps: Captures per second (default 1.0 = once per second)
            use_llm: Whether to use LLM engine for strategic coaching (default True)
        """
        self.capture_fps = capture_fps
        self.capture_interval = 1.0 / capture_fps

        self.capture = None
        self.extractor = GameDataExtractor()
        self.rule_engine = RuleEngine()

        # Initialize LLM engine if API key available
        self.llm_engine: Optional[LLMEngine] = None
        self.use_llm = use_llm
        if use_llm:
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                self.llm_engine = LLMEngine(anthropic_key=anthropic_key)
                logger.info("LLM engine initialized with Anthropic API")
            else:
                logger.warning("ANTHROPIC_API_KEY not found, LLM coaching disabled")

        self.running = False
        self.last_game_data: Optional[Dict[str, Any]] = None
        self.last_command: Optional[Union[CoachingCommand, DirectiveV1]] = None

    async def initialize(self):
        """Initialize capture system"""
        try:
            self.capture = get_capture()
            logger.info("Game monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize capture: {e}")
            raise

    async def find_game_window(self) -> bool:
        """Find and set the League of Legends game window"""
        try:
            window = self.capture.find_game_window()
            if window:
                self.capture.target_window = window
                logger.info(f"Found game window: {window.window_name} ({window.bounds[2]}x{window.bounds[3]})")

                # Setup ROIs based on window size
                width, height = window.bounds[2], window.bounds[3]
                self.capture.setup_lol_rois(width, height)
                logger.info(f"Setup {len(self.capture.rois)} ROIs")
                return True
            else:
                logger.warning("Game window not found")
                return False
        except Exception as e:
            logger.error(f"Error finding game window: {e}")
            return False

    async def capture_and_extract(self) -> Optional[Dict[str, Any]]:
        """Capture screen and extract game data"""
        try:
            # Capture game window
            frame = self.capture.capture_game()
            if frame is None:
                logger.debug("Failed to capture frame")
                return None

            # Extract ROIs
            roi_extracts = self.capture.extract_rois(frame)

            # Extract game data via OCR
            game_data = self.extractor.extract_game_data(roi_extracts)

            # Store for access
            self.last_game_data = game_data

            return game_data

        except Exception as e:
            logger.error(f"Error capturing and extracting: {e}")
            return None

    def build_game_state(self, game_data: Dict[str, Any]) -> Optional[GameState]:
        """Build a GameState object from extracted data"""
        try:
            # Get game time (use 0 if not available)
            game_time = game_data.get('game_time')
            if game_time is None:
                logger.debug("No game time available, using estimated time")
                # Try to estimate based on CS (rough estimate: 10 CS per minute early game)
                cs = game_data.get('cs', 0)
                if cs and cs > 0:
                    game_time = int(cs * 6)  # Rough estimate
                    logger.debug(f"Estimated game time from CS: {game_time}s")
                else:
                    game_time = 300  # Default to 5 minutes if no data

            # Determine game phase
            game_phase = GamePhase.EARLY
            if game_time > 900:  # 15 minutes
                game_phase = GamePhase.MID
            if game_time > 1500:  # 25 minutes
                game_phase = GamePhase.LATE

            # Build player state with extracted data
            hp_percent = game_data.get('hp_percent') or 100.0
            mana_percent = game_data.get('mana_percent') or 100.0

            # Estimate HP/Mana values (we don't have max values, so estimate)
            hp_max = 2000  # Rough estimate for mid-game champion
            hp = int(hp_max * (hp_percent / 100.0))

            mana_max = 1000  # Rough estimate
            mana = int(mana_max * (mana_percent / 100.0))

            player = PlayerState(
                champion_name="Unknown",  # Can't extract this yet
                summoner_name="Player",
                level=10,  # Can't extract this yet
                hp=hp,
                hp_max=hp_max,
                mana=mana,
                mana_max=mana_max,
                gold=game_data.get('gold') or 0,
                cs=game_data.get('cs') or 0,  # Default to 0 if OCR fails
                kills=0,
                deaths=0,
                assists=0
            )

            # Build objectives (placeholder data)
            objectives = ObjectiveState()

            # Build wave state (placeholder)
            wave = WaveState()

            # Build vision state (placeholder)
            vision = VisionState()

            # Create game state
            game_state = GameState(
                game_time=game_time,
                game_phase=game_phase,
                player=player,
                objectives=objectives,
                wave=wave,
                vision=vision,
                timestamp=time.time()
            )

            return game_state

        except Exception as e:
            logger.error(f"Error building game state: {e}")
            return None

    async def generate_coaching_command(self, game_state: GameState) -> Optional[Union[CoachingCommand, DirectiveV1]]:
        """
        Generate coaching command from game state
        Priority:
        1. Rule engine (safety warnings, <50ms latency) - CoachingCommand
        2. LLM engine (strategic coaching, <500ms latency) - DirectiveV1
        """
        try:
            # Priority 1: Check rule engine for safety warnings (critical, immediate)
            rule_command = self.rule_engine.process(game_state)
            if rule_command:
                self.last_command = rule_command
                logger.info(f"[RULE] Generated command: [{rule_command.priority}] {rule_command.message}")
                return rule_command

            # Priority 2: Try LLM engine for strategic coaching (wave management, objectives)
            if self.llm_engine:
                # Try wave management coaching
                wave_directive = await self.llm_engine.wave_management_coaching(game_state)
                if wave_directive:
                    self.last_command = wave_directive
                    logger.info(f"[LLM] Wave directive: [{wave_directive.priority}] {wave_directive.primary.text}")
                    return wave_directive

                # Try objective coaching
                objective_directive = await self.llm_engine.objective_coaching(game_state)
                if objective_directive:
                    self.last_command = objective_directive
                    logger.info(f"[LLM] Objective directive: [{objective_directive.priority}] {objective_directive.primary.text}")
                    return objective_directive

            return None

        except Exception as e:
            logger.error(f"Error generating command: {e}")
            return None

    async def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about current state"""
        return {
            "running": self.running,
            "has_capture": self.capture is not None,
            "has_target_window": self.capture.target_window is not None if self.capture else False,
            "has_llm_engine": self.llm_engine is not None,
            "last_game_data": self.last_game_data,
            "last_command": self.last_command.dict() if self.last_command else None,
        }


async def create_monitor(capture_fps: float = 1.0, use_llm: bool = True) -> GameMonitor:
    """Factory function to create and initialize a game monitor"""
    monitor = GameMonitor(capture_fps=capture_fps, use_llm=use_llm)
    await monitor.initialize()
    return monitor
