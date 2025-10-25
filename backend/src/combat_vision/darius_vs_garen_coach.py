"""
Darius vs Garen Combat Coach
Provides real-time combat advice specific to the Darius vs Garen matchup
"""

from typing import Optional, Dict
from loguru import logger
import time
from src.models.game_state import CoachingCommand


class DariusVsGarenCoach:
    """Combat coaching specifically for Darius vs Garen matchup"""

    def __init__(self):
        # Darius state tracking
        self.darius_bleed_stacks = 0  # 0-5 stacks
        self.has_noxian_might = False
        self.last_darius_q_time = 0
        self.last_darius_e_time = 0
        self.last_darius_r_time = 0

        # Cooldowns
        self.darius_q_cd = 9.0
        self.darius_e_cd = 24.0
        self.darius_r_cd = 120.0

    def update_darius_state(self, bleed_stacks: int, has_noxian_might: bool):
        """Update Darius's current state"""
        self.darius_bleed_stacks = bleed_stacks
        self.has_noxian_might = has_noxian_might

    def record_ability_use(self, ability: str):
        """Record when Darius uses an ability"""
        now = time.time()
        if ability == 'Q':
            self.last_darius_q_time = now
        elif ability == 'E':
            self.last_darius_e_time = now
        elif ability == 'R':
            self.last_darius_r_time = now

    def get_darius_cooldowns(self) -> Dict[str, float]:
        """Get Darius's ability cooldowns"""
        now = time.time()
        return {
            'Q': max(0, self.darius_q_cd - (now - self.last_darius_q_time)),
            'E': max(0, self.darius_e_cd - (now - self.last_darius_e_time)),
            'R': max(0, self.darius_r_cd - (now - self.last_darius_r_time))
        }

    def get_combat_command(
        self,
        garen_q_active: bool,
        garen_w_active: bool,
        garen_e_active: bool,
        garen_e_duration: float,
        garen_r_active: bool,
        garen_cooldowns: Dict[str, float],
        darius_hp_percent: float,
        garen_hp_percent: float,
        distance_to_garen: str = "medium"  # close, medium, far
    ) -> Optional[CoachingCommand]:
        """
        Generate combat command based on current situation
        This is the CORE combat coaching logic for Darius vs Garen
        """

        now = time.time()

        # === CRITICAL SITUATIONS (Priority 1) ===

        # 1. Garen R incoming and you're low HP
        if garen_r_active and darius_hp_percent < 40:
            return CoachingCommand(
                priority="critical",
                category="combat",
                icon="💀",
                message="GAREN ULT! FLASH NOW or you die!",
                duration=2,
                timestamp=now
            )

        # 2. Garen E spinning on you
        if garen_e_active:
            if garen_e_duration < 1.0:
                # Spin just started - get out NOW
                return CoachingCommand(
                    priority="critical",
                    category="combat",
                    icon="🌀",
                    message="GAREN SPINNING! WALK OUT NOW!",
                    duration=1,
                    timestamp=now
                )
            else:
                # He's been spinning, almost done
                remaining = 3.0 - garen_e_duration
                return CoachingCommand(
                    priority="critical",
                    category="combat",
                    icon="⏱️",
                    message=f"Garen E ends in {remaining:.1f}s - PREPARE TO ENGAGE!",
                    duration=1,
                    timestamp=now
                )

        # 3. Garen Q coming at you
        if garen_q_active and distance_to_garen == "close":
            return CoachingCommand(
                priority="critical",
                category="combat",
                icon="⚠️",
                message="GAREN Q! BACK OFF - you'll get silenced!",
                duration=2,
                timestamp=now
            )

        # === HIGH PRIORITY OPPORTUNITIES (Priority 2) ===

        darius_cooldowns = self.get_darius_cooldowns()

        # 4. Garen just finished E - PUNISH WINDOW
        if garen_cooldowns['E'] > 5.0 and garen_cooldowns['Q'] > 3.0:
            if darius_cooldowns['E'] == 0:
                return CoachingCommand(
                    priority="high",
                    category="combat",
                    icon="🎯",
                    message="GAREN ABILITIES DOWN! PULL (E) + TRADE!",
                    duration=3,
                    timestamp=now
                )

        # 5. 4 bleed stacks on Garen - need one more for Noxian Might
        if self.darius_bleed_stacks == 4 and darius_cooldowns['Q'] == 0:
            return CoachingCommand(
                priority="high",
                category="combat",
                icon="🩸",
                message="4 STACKS! HIT Q FOR NOXIAN MIGHT!",
                duration=2,
                timestamp=now
            )

        # 6. You have Noxian Might - you win all-in
        if self.has_noxian_might and garen_hp_percent < 60:
            return CoachingCommand(
                priority="high",
                category="combat",
                icon="💪",
                message="NOXIAN MIGHT ACTIVE! ALL IN - YOU WIN!",
                duration=3,
                timestamp=now
            )

        # 7. Garen low HP and your R is up
        if garen_hp_percent < 35 and darius_cooldowns['R'] == 0:
            return CoachingCommand(
                priority="high",
                category="combat",
                icon="🔪",
                message=f"GAREN {garen_hp_percent:.0f}% HP! DUNK HIM (R)!",
                duration=2,
                timestamp=now
            )

        # === MEDIUM PRIORITY TRADING (Priority 3) ===

        # 8. Garen W shield up - wait it out
        if garen_w_active:
            return CoachingCommand(
                priority="medium",
                category="combat",
                icon="🛡️",
                message="Garen W shield up! WAIT 2s then trade",
                duration=2,
                timestamp=now
            )

        # 9. Safe to Q poke (outer ring)
        if darius_cooldowns['Q'] == 0 and distance_to_garen == "medium":
            if not garen_q_active and not garen_e_active:
                return CoachingCommand(
                    priority="medium",
                    category="combat",
                    icon="⚔️",
                    message="Hit Q (outer ring) for poke + heal!",
                    duration=2,
                    timestamp=now
                )

        # 10. Good pull angle
        if darius_cooldowns['E'] == 0 and distance_to_garen == "medium":
            if garen_cooldowns['Q'] > 2.0 and garen_cooldowns['E'] > 2.0:
                return CoachingCommand(
                    priority="medium",
                    category="combat",
                    icon="🪝",
                    message="Good pull angle! E when he's in range",
                    duration=2,
                    timestamp=now
                )

        # === DEFENSIVE POSITIONING (Priority 4) ===

        # 11. Too low HP to trade
        if darius_hp_percent < 30:
            return CoachingCommand(
                priority="medium",
                category="combat",
                icon="🏥",
                message="Low HP! Play safe near tower",
                duration=3,
                timestamp=now
            )

        # 12. Garen has all abilities up - respect him
        if garen_cooldowns['Q'] < 2.0 and garen_cooldowns['E'] < 2.0:
            return CoachingCommand(
                priority="medium",
                category="combat",
                icon="⚠️",
                message="Garen full combo up - respect spacing",
                duration=2,
                timestamp=now
            )

        return None

    def get_matchup_tips(self) -> str:
        """Get general matchup tips for Darius vs Garen"""
        return """
        Darius vs Garen Key Points:
        1. NEVER fight in Garen E - you auto-lose
        2. Hit Q outer ring only (175 range)
        3. Stack 5 bleeds for Noxian Might = you win
        4. Pull (E) when his Q/E are on cooldown
        5. Your R executes at 20-40% HP (scales with stacks)
        6. Garen W reduces your damage - wait it out
        7. Early game (1-5): Garen wins if he lands E
        8. Mid game (6-10): You win with 5 stacks
        9. Late game: Whoever gets 5 stacks first wins
        """
