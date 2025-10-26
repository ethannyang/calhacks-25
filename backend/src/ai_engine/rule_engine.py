"""
Rule-based coaching engine for fast, deterministic decisions
Target latency: <50ms
Handles F1: Safety Warnings and other reactive coaching
"""

from typing import Optional, List, Tuple
import time
from loguru import logger

from ..models.game_state import GameState, CoachingCommand, Severity


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

    def rule_safety_enhanced(self, state: GameState) -> List[Tuple[str, Severity]]:
        """
        Enhanced safety rules with severity levels (spec-aligned)
        Returns list of (message, severity) tuples
        """
        out = []

        # Rule: Multiple enemies missing + no vision + past mid
        if state.vision.enemy_missing_count >= 3:
            if state.wave.wave_position == "enemy_tower":
                out.append(("⚠️ DANGER: Back off - 3+ missing, no vision", Severity.DANGER))

        # Rule: Low HP + enemy jungler nearby
        hp_percent = state.player.hp / state.player.hp_max if state.player.hp_max > 0 else 1.0
        if hp_percent < 0.30:
            if state.vision.enemy_visible_count >= 1:
                out.append(("⚠️ WARNING: Low HP + enemies nearby, ward/hover tower", Severity.WARN))

        # Rule: Very low HP
        if hp_percent < 0.15:
            out.append(("🚨 CRITICAL: HP critical - recall or die", Severity.DANGER))

        return out

    def check_safety(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        F1: Safety Warnings
        Check for dangerous situations requiring immediate attention
        """
        hp_percent = game_state.player.hp / game_state.player.hp_max if game_state.player.hp_max > 0 else 1.0
        mana_percent = game_state.player.mana / game_state.player.mana_max if game_state.player.mana_max > 0 else 1.0

        # Rule 1: Critical HP - immediate danger
        if hp_percent < 0.2:
            if self._can_send_warning("critical_hp", cooldown=8.0):
                return CoachingCommand(
                    priority="critical",
                    category="safety",
                    icon="🚨",
                    message=f"CRITICAL HP: {int(hp_percent*100)}% - RECALL OR DIE",
                    duration=5,
                    timestamp=time.time()
                )

        # Rule 2: Low HP with enemies nearby
        if hp_percent < 0.35:
            if game_state.vision.enemy_visible_count >= 2:
                if self._can_send_warning("low_hp_danger"):
                    return CoachingCommand(
                        priority="critical",
                        category="safety",
                        icon="⚠️",
                        message=f"DANGER: {int(hp_percent*100)}% HP - {game_state.vision.enemy_visible_count} enemies visible, BACK OFF NOW",
                        duration=5,
                        timestamp=time.time()
                    )

        # Rule 3: Low mana warning
        if mana_percent < 0.2 and game_state.game_time < 900:  # Early game
            if self._can_send_warning("low_mana", cooldown=15.0):
                return CoachingCommand(
                    priority="medium",
                    category="safety",
                    icon="💧",
                    message=f"LOW MANA: {int(mana_percent*100)}% - conserve for trades/escapes",
                    duration=4,
                    timestamp=time.time()
                )

        # Rule 4: Gank warning - enemies missing in early game
        if game_state.vision.enemy_missing_count >= 2 and game_state.game_time < 900:
            if game_state.wave.wave_position != "ally_tower":
                if self._can_send_warning("gank_warning", cooldown=12.0):
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="👁️",
                        message=f"GANK ALERT: {game_state.vision.enemy_missing_count} missing - hug tower, ward",
                        duration=6,
                        timestamp=time.time()
                    )

        # Rule 5: Multiple enemies missing - roam danger
        if game_state.vision.enemy_missing_count >= 3:
            # Extra danger if pushing past midpoint
            if game_state.wave.wave_position == "enemy_tower":
                if self._can_send_warning("enemies_missing"):
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="⚠️",
                        message=f"ROAM DANGER: {game_state.vision.enemy_missing_count} missing, you're pushed - RETREAT",
                        duration=6,
                        timestamp=time.time()
                    )

        # Rule 6: Tower dive risk
        if game_state.wave.wave_position == "enemy_tower":
            visible_enemies = game_state.vision.enemy_visible_count
            if visible_enemies >= 2 and hp_percent < 0.5:
                if self._can_send_warning("tower_dive_risk"):
                    return CoachingCommand(
                        priority="critical",
                        category="safety",
                        icon="🏯",
                        message=f"DIVE RISK: {visible_enemies} enemies, {int(hp_percent*100)}% HP - GET OUT",
                        duration=5,
                        timestamp=time.time()
                    )

        # Rule 7: Outnumbered at objective
        if game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 30:
            allies_alive = sum(1 for ally in game_state.allies if ally.is_alive)
            enemies_visible = game_state.vision.enemy_visible_count

            if allies_alive < enemies_visible - 1:  # Outnumbered by 2+
                if self._can_send_warning("outnumbered_objective"):
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="⚠️",
                        message=f"OUTNUMBERED: {allies_alive}v{enemies_visible} at dragon - DISENGAGE",
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

    def check_objectives(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        Objective-specific warnings for dragon, baron, herald
        """
        # Dragon spawn warning
        if game_state.objectives.dragon_spawn_time:
            dragon_time = game_state.objectives.dragon_spawn_time

            if 45 < dragon_time < 60:
                if self._can_send_warning("dragon_prep", cooldown=20.0):
                    return CoachingCommand(
                        priority="high",
                        category="objective",
                        icon="🐉",
                        message=f"DRAGON in {int(dragon_time)}s - Start grouping, get vision bot side",
                        duration=6,
                        timestamp=time.time()
                    )

            if 15 < dragon_time < 30:
                if self._can_send_warning("dragon_imminent", cooldown=20.0):
                    return CoachingCommand(
                        priority="high",
                        category="objective",
                        icon="🐉",
                        message=f"DRAGON in {int(dragon_time)}s - GROUP NOW, ward pit",
                        duration=6,
                        timestamp=time.time()
                    )

        # Baron spawn warning
        if game_state.objectives.baron_spawn_time:
            baron_time = game_state.objectives.baron_spawn_time

            if 60 < baron_time < 90:
                if self._can_send_warning("baron_prep", cooldown=25.0):
                    return CoachingCommand(
                        priority="high",
                        category="objective",
                        icon="🦖",
                        message=f"BARON in {int(baron_time)}s - Clear vision, group for team fight",
                        duration=6,
                        timestamp=time.time()
                    )

            if 20 < baron_time < 40:
                if self._can_send_warning("baron_imminent", cooldown=25.0):
                    return CoachingCommand(
                        priority="critical",
                        category="objective",
                        icon="🦖",
                        message=f"BARON in {int(baron_time)}s - PRIORITY, don't split push",
                        duration=6,
                        timestamp=time.time()
                    )

        # Herald spawn warning
        if game_state.objectives.herald_spawn_time:
            herald_time = game_state.objectives.herald_spawn_time

            if 40 < herald_time < 60:
                if self._can_send_warning("herald_prep", cooldown=20.0):
                    return CoachingCommand(
                        priority="medium",
                        category="objective",
                        icon="👁️",
                        message=f"HERALD in {int(herald_time)}s - Rotate top, help jungler secure",
                        duration=6,
                        timestamp=time.time()
                    )

        return None

    def check_late_game(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        Late game specific warnings (60+ minutes)
        Death timers are 60+ seconds, one mistake ends the game
        """
        if game_state.game_time < 3600:  # Not late game yet
            return None

        hp_percent = game_state.player.hp / game_state.player.hp_max if game_state.player.hp_max > 0 else 1.0

        # Rule 1: Ultra late game death timer warning
        if game_state.game_time > 3600:  # 60+ minutes
            death_timer = min(70, 25 + (game_state.player.level * 2.5))  # Rough death timer calc

            if hp_percent < 0.5:
                if self._can_send_warning("late_game_death", cooldown=30.0):
                    return CoachingCommand(
                        priority="critical",
                        category="safety",
                        icon="💀",
                        message=f"LATE GAME: Death = {int(death_timer)}s timer! Play SAFE, group with team",
                        duration=8,
                        timestamp=time.time()
                    )

        # Rule 2: Elder Dragon priority
        if game_state.game_time > 2100:  # 35+ min, Elder spawns
            if game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 60:
                if self._can_send_warning("elder_dragon", cooldown=30.0):
                    return CoachingCommand(
                        priority="critical",
                        category="objective",
                        icon="🔥",
                        message=f"ELDER DRAGON in {int(game_state.objectives.dragon_spawn_time)}s - WIN CONDITION, full team needed!",
                        duration=8,
                        timestamp=time.time()
                    )

        return None

    def process(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        Process game state through all rules
        Returns highest priority command
        """
        commands = []

        # Check all rule types (order matters - safety first!)
        safety_cmd = self.check_safety(game_state)
        if safety_cmd:
            commands.append(safety_cmd)

        late_game_cmd = self.check_late_game(game_state)
        if late_game_cmd:
            commands.append(late_game_cmd)

        objective_cmd = self.check_objectives(game_state)
        if objective_cmd:
            commands.append(objective_cmd)

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
