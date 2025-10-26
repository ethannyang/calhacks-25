"""
Combat Coaching Module - Integrates audio detection with combat coach
Runs audio detection in background and provides coaching commands
"""

import asyncio
import time
from typing import Optional, Dict
from loguru import logger

from src.combat_vision.audio_template_detector import AudioTemplateDetector
from src.combat_vision.darius_vs_garen_coach import DariusVsGarenCoach
from src.models.game_state import CoachingCommand, GameState


class CombatCoachModule:
    """
    Integrates audio-based ability detection with combat coaching
    Runs continuously in background during matches
    """

    def __init__(self, audio_device_index: Optional[int] = None, detection_threshold: float = 0.6):
        """
        Initialize combat coach module

        Args:
            audio_device_index: Audio device for capture (BlackHole for system audio)
            detection_threshold: Correlation threshold for audio detection (0-1)
        """
        # Audio template files for Garen abilities
        self.audio_files = {
            'Q': '/Users/ethan/Desktop/projects/calhacks-25/45_garen_base_q_oc_01.wav',
            'W': '/Users/ethan/Desktop/projects/calhacks-25/66_garen_base_w_obd_01.wav',
            'E': '/Users/ethan/Desktop/projects/calhacks-25/25_garen_base_e_oba_01.wav',
            'R': '/Users/ethan/Desktop/projects/calhacks-25/58_garen_base_r_oc_01.wav'
        }

        # Initialize audio detector
        self.audio_detector = AudioTemplateDetector(
            audio_files=self.audio_files,
            sample_rate=44100,
            threshold=detection_threshold
        )

        # Initialize combat coach
        self.coach = DariusVsGarenCoach()

        # Audio device configuration
        self.audio_device_index = audio_device_index

        # State
        self.running = False
        self.audio_capture_active = False

        # Last detected abilities
        self.garen_q_active = False
        self.garen_w_active = False
        self.garen_e_result = {'spinning': False, 'duration': 0}
        self.garen_r_active = False

        logger.info("Combat coach module initialized")

    async def start(self):
        """Start the combat coaching module"""
        self.running = True

        # Start audio capture
        if self.audio_device_index is not None:
            success = self.audio_detector.start_capture(device_index=self.audio_device_index)
            if success:
                self.audio_capture_active = True
                logger.info("✅ Audio capture started for combat coaching")
            else:
                logger.error("❌ Failed to start audio capture - combat coaching disabled")
                logger.error("   Make sure BlackHole is installed and configured")
                return False
        else:
            logger.warning("No audio device configured - combat coaching disabled")
            logger.warning("Set AUDIO_DEVICE_INDEX in .env to enable audio detection")
            return False

        return True

    def stop(self):
        """Stop the combat coaching module"""
        self.running = False
        if self.audio_capture_active:
            self.audio_detector.stop_capture()
            self.audio_capture_active = False
            logger.info("Combat coaching module stopped")

    def update_ability_detections(self):
        """
        Update current ability detection state
        Called frequently to check for new ability casts
        """
        if not self.audio_capture_active:
            return

        # Detect all Garen abilities
        self.garen_q_active = self.audio_detector.detect_garen_q()
        self.garen_w_active = self.audio_detector.detect_garen_w()
        self.garen_e_result = self.audio_detector.detect_garen_e()
        self.garen_r_active = self.audio_detector.detect_garen_r()

    def get_combat_command(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        Get combat coaching command based on current game state and detected abilities

        Args:
            game_state: Current game state from main game loop

        Returns:
            CoachingCommand if there's advice to give, None otherwise
        """
        if not self.audio_capture_active:
            return None

        # Update ability detections
        self.update_ability_detections()

        # Get Garen's cooldowns from audio detector
        garen_cooldowns = self.audio_detector.get_ability_cooldowns()

        # Extract relevant data from game state
        darius_hp_percent = game_state.player.hp if game_state.player.hp else 100

        # Mock Garen HP (in real implementation, would use OCR or game data)
        garen_hp_percent = 70.0  # TODO: Extract from game state

        # Distance estimate based on combat context (could be improved with visual detection)
        distance_to_garen = "medium"  # TODO: Estimate from game context

        # Get coaching command from Darius vs Garen coach
        command = self.coach.get_combat_command(
            garen_q_active=self.garen_q_active,
            garen_w_active=self.garen_w_active,
            garen_e_active=self.garen_e_result['spinning'],
            garen_e_duration=self.garen_e_result['duration'],
            garen_r_active=self.garen_r_active,
            garen_cooldowns=garen_cooldowns,
            darius_hp_percent=darius_hp_percent,
            garen_hp_percent=garen_hp_percent,
            distance_to_garen=distance_to_garen
        )

        return command

    def is_active(self) -> bool:
        """Check if combat coaching is active"""
        return self.running and self.audio_capture_active

    def get_status(self) -> Dict:
        """Get current status for debugging"""
        if not self.audio_capture_active:
            return {
                'active': False,
                'reason': 'Audio capture not active'
            }

        return {
            'active': True,
            'audio_device': self.audio_device_index,
            'detections': {
                'garen_q': self.garen_q_active,
                'garen_w': self.garen_w_active,
                'garen_e': self.garen_e_result['spinning'],
                'garen_e_duration': self.garen_e_result['duration'],
                'garen_r': self.garen_r_active
            },
            'cooldowns': self.audio_detector.get_ability_cooldowns() if self.audio_capture_active else {}
        }


async def test_combat_coach():
    """Test the combat coach module standalone"""
    print("\n" + "=" * 60)
    print("COMBAT COACH MODULE TEST")
    print("=" * 60)
    print("\nThis test requires:")
    print("1. BlackHole installed and configured")
    print("2. League of Legends running")
    print("3. In a game against Garen\n")

    # List available audio devices
    print("Available audio devices:")
    AudioTemplateDetector.list_audio_devices()

    print("\nEnter BlackHole device index: ", end='')
    device_index = int(input().strip())

    print("\nStarting combat coach...\n")

    # Initialize module
    module = CombatCoachModule(audio_device_index=device_index)

    # Start module
    success = await module.start()
    if not success:
        print("❌ Failed to start combat coach")
        return

    print("✅ Combat coach started!")
    print("🎮 Fight Garen and watch for coaching commands\n")
    print("Press Ctrl+C to stop\n")

    try:
        from src.models.game_state import GameState, GamePhase, PlayerState

        # Mock game state
        mock_player = PlayerState(
            champion_name="Darius",
            summoner_name="TestPlayer",
            level=10,
            hp=75,
            hp_max=100,
            mana=50,
            mana_max=100,
            gold=2500,
            cs=100,
            kills=2,
            deaths=1,
            assists=3
        )

        mock_game_state = GameState(
            game_time=600,
            game_phase=GamePhase.EARLY,
            player=mock_player,
            team_score=5,
            enemy_score=5,
            team_towers=10,
            enemy_towers=10,
            team_gold_lead=0,
            allies=[],
            enemies=[],
            objectives=None,
            wave=None,
            vision=None,
            timestamp=time.time()
        )

        frame_count = 0
        while module.is_active():
            frame_count += 1

            # Get combat command
            command = module.get_combat_command(mock_game_state)

            # Display status
            status = module.get_status()
            detections = status['detections']
            cooldowns = status['cooldowns']

            q_status = f"Q:{'✓' if detections['garen_q'] else '-'}({cooldowns['Q']:.0f}s)"
            w_status = f"W:{'✓' if detections['garen_w'] else '-'}({cooldowns['W']:.0f}s)"
            e_status = f"E:{'SPIN!' if detections['garen_e'] else '-'}({cooldowns['E']:.0f}s)"
            r_status = f"R:{'✓' if detections['garen_r'] else '-'}({cooldowns['R']:.0f}s)"

            print(f"\r[Frame {frame_count}] {q_status} | {w_status} | {e_status} | {r_status}", end='', flush=True)

            # Show coaching command if present
            if command:
                print(f"\n\n{'='*60}")
                print(f"🎯 COACHING COMMAND [{command.priority.upper()}]")
                print(f"{command.icon} {command.message}")
                print(f"{'='*60}\n")

            await asyncio.sleep(0.033)  # ~30 Hz

    except KeyboardInterrupt:
        print("\n\n✅ Test stopped")
    finally:
        module.stop()


if __name__ == "__main__":
    asyncio.run(test_combat_coach())
