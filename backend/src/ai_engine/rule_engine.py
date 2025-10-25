"""
Rule-based coaching engine for fast, deterministic decisions
Target latency: <50ms
Handles F1: Safety Warnings and other reactive coaching
"""

from typing import Optional
import time
from loguru import logger

from ..models.game_state import GameState, CoachingCommand


class RuleEngine:
    """Fast rule-based coaching for safety and reactive decisions"""

    def __init__(self):
        self.last_warning_time = {}  # Prevent spam

    def _can_send_warning(self, category: str, cooldown: float = 10.0) -> bool:
        """Check if enough time has passed since last warning of this type"""
        now = time.time()
        last_time = self.last_warning_time.get(category, 0)
        if now - last_time >= cooldown:
            self.last_warning_time[category] = now
            return True
        return False

    def check_safety(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        F1: Safety Warnings
        Check for dangerous situations requiring immediate attention
        """

        # Rule 1: Low HP with enemies nearby
        if game_state.player.hp / game_state.player.hp_max < 0.3:
            if game_state.vision.enemy_visible_count >= 2:
                if self._can_send_warning("low_hp_danger"):
                    return CoachingCommand(
                        priority="critical",
                        category="safety",
                        icon="⚠️",
                        message=f"DANGER: Low HP ({game_state.player.hp}/{game_state.player.hp_max}) - {game_state.vision.enemy_visible_count} enemies near, BACK OFF",
                        duration=5,
                        timestamp=time.time()
                    )

        # Rule 2: Multiple enemies missing
        if game_state.vision.enemy_missing_count >= 3:
            # Extra danger if pushing past midpoint
            if game_state.wave.wave_position == "enemy_tower":
                if self._can_send_warning("enemies_missing"):
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="⚠️",
                        message=f"WARNING: {game_state.vision.enemy_missing_count} enemies missing, no vision - play safe",
                        duration=6,
                        timestamp=time.time()
                    )

        # Rule 3: Tower dive risk
        if game_state.wave.wave_position == "enemy_tower":
            visible_enemies = game_state.vision.enemy_visible_count
            if visible_enemies >= 2 and game_state.player.hp / game_state.player.hp_max < 0.5:
                if self._can_send_warning("tower_dive_risk"):
                    return CoachingCommand(
                        priority="critical",
                        category="safety",
                        icon="⚠️",
                        message=f"DANGER: Tower dive risk - {visible_enemies} enemies, low HP, RETREAT",
                        duration=5,
                        timestamp=time.time()
                    )

        # Rule 4: Outnumbered at objective
        if game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 30:
            allies_alive = sum(1 for ally in game_state.allies if ally.is_alive)
            enemies_visible = game_state.vision.enemy_visible_count

            if allies_alive < enemies_visible - 1:  # Outnumbered by 2+
                if self._can_send_warning("outnumbered_objective"):
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="⚠️",
                        message=f"WARNING: Outnumbered at dragon ({allies_alive}v{enemies_visible}) - disengage",
                        duration=5,
                        timestamp=time.time()
                    )

        return None

    def check_recall_timing(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        F6: Recall Timing
        Check if player should recall based on gold, HP, and objectives
        """

        # Rule 1: Enough gold for item, low HP, wave pushed
        gold = game_state.player.gold
        hp_percent = game_state.player.hp / game_state.player.hp_max
        mana_percent = game_state.player.mana / game_state.player.mana_max if game_state.player.mana_max > 0 else 1.0

        if gold >= 1200 and (hp_percent < 0.4 or mana_percent < 0.3):
            if game_state.wave.wave_position == "enemy_tower":  # Wave pushed, safe to recall
                if self._can_send_warning("recall_timing", cooldown=15.0):
                    return CoachingCommand(
                        priority="medium",
                        category="recall",
                        icon="🏠",
                        message=f"RECALL: {gold}g - back for items, wave pushed",
                        duration=5,
                        timestamp=time.time()
                    )

        # Rule 2: Don't recall if objective spawning soon
        if game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 45:
            if self._can_send_warning("dont_recall_objective", cooldown=20.0):
                return CoachingCommand(
                    priority="medium",
                    category="recall",
                    icon="🏠",
                    message=f"STAY: Dragon in {game_state.objectives.dragon_spawn_time}s - don't recall yet",
                    duration=5,
                    timestamp=time.time()
                )

        return None

    def check_cannon_wave(self, game_state: GameState) -> Optional[CoachingCommand]:
        """Remind player about cannon wave (higher gold)"""
        if game_state.wave.cannon_wave:
            if self._can_send_warning("cannon_wave", cooldown=30.0):
                return CoachingCommand(
                    priority="low",
                    category="wave",
                    icon="🌊",
                    message="CANNON WAVE: Don't miss cannon minion (higher gold)",
                    duration=4,
                    timestamp=time.time()
                )
        return None

    def process(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        Process game state through all rules
        Returns highest priority command
        """
        commands = []

        # Check all rule types
        safety_cmd = self.check_safety(game_state)
        if safety_cmd:
            commands.append(safety_cmd)

        recall_cmd = self.check_recall_timing(game_state)
        if recall_cmd:
            commands.append(recall_cmd)

        cannon_cmd = self.check_cannon_wave(game_state)
        if cannon_cmd:
            commands.append(cannon_cmd)

        # Return highest priority command
        if commands:
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            commands.sort(key=lambda c: priority_order.get(c.priority, 999))
            return commands[0]

        return None
