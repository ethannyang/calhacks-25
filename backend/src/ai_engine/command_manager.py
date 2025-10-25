"""
Command Manager - Handles command priority, state tracking, and completion detection
Only issues new commands when:
1. Higher priority command needs attention (CRITICAL > HIGH > NORMAL)
2. Current command is completed
3. Current command is no longer relevant
"""

import time
from typing import Optional, Dict
from enum import IntEnum
from loguru import logger
from src.models.game_state import GameState, CoachingCommand


class CommandPriority(IntEnum):
    """Command priority levels - higher number = higher priority"""
    NORMAL = 1      # General wave management, farming
    HIGH = 2        # Recall timing, objective setup, good trades
    CRITICAL = 3    # Danger (enemy jungler nearby), immediate retreat, must-attend objectives


class CommandState:
    """Tracks state of an active command"""
    def __init__(self, command: CoachingCommand, priority: CommandPriority):
        self.command = command
        self.priority = priority
        self.issued_time = time.time()
        self.completed = False
        self.game_state_snapshot = None  # Store state when command was issued

    def is_stale(self, max_age: float = 30.0) -> bool:
        """Check if command has been active too long without completion"""
        return time.time() - self.issued_time > max_age

    def should_keep_displaying(self) -> bool:
        """Should we keep showing this command?"""
        return not self.completed and not self.is_stale()


class CommandManager:
    """Manages command lifecycle with priority and completion tracking"""

    def __init__(self):
        self.current_command: Optional[CommandState] = None
        self.last_command_time = 0
        self.min_command_interval = 3.0  # Don't spam commands faster than 3 seconds

        # State tracking for completion detection
        self.last_gold = 0
        self.last_hp = 0
        self.last_position = None
        self.last_items_count = 0

    def _get_priority(self, command: CoachingCommand) -> CommandPriority:
        """Determine command priority based on category and keywords"""
        category = command.category.lower()
        message = command.message.lower()

        # CRITICAL: Safety, immediate danger
        critical_keywords = ["retreat", "danger", "spotted", "gank", "dive", "run", "escape", "baron fight", "teamfight"]
        if any(kw in message for kw in critical_keywords):
            return CommandPriority.CRITICAL

        # CRITICAL: Must-attend objectives
        if category == "objective" and any(kw in message for kw in ["baron", "elder", "soul"]):
            return CommandPriority.CRITICAL

        # HIGH: Recall timing, good trades, important objectives
        high_keywords = ["recall", "back", "buy", "teleport", "roam", "dragon", "herald"]
        if any(kw in message for kw in high_keywords):
            return CommandPriority.HIGH

        # NORMAL: Everything else (wave management, farming, positioning)
        return CommandPriority.NORMAL

    def _detect_completion(self, game_state: GameState) -> Optional[str]:
        """
        Detect if current command was completed by analyzing game state changes
        Returns congratulatory message if completed, None otherwise
        """
        if not self.current_command:
            return None

        cmd = self.current_command.command
        category = cmd.category.lower()
        message = cmd.message.lower()

        # Recall completion: Check if player is in base (HP and mana at 100%)
        if "recall" in message or ("back" in message and "low hp" not in message.lower()):
            hp_percent = (game_state.player.hp / game_state.player.hp_max) * 100
            mana_percent = (game_state.player.mana / game_state.player.mana_max) * 100 if game_state.player.mana_max > 0 else 100

            # Player is in fountain if both HP and mana are at 100%
            if hp_percent >= 99 and mana_percent >= 99:
                logger.info("✅ Recall command completed - Player is in base")
                return "Nice! 💰 Good recall timing"

        # Retreat completion: Only if player actually retreated (HP recovered or out of danger zone)
        if "retreat" in message or "danger" in message:
            # Check if HP increased significantly (healed/regenerated)
            hp_percent_now = (game_state.player.hp / game_state.player.hp_max) * 100
            if hp_percent_now > 70:  # Player is now safe HP
                logger.info("✅ Retreat command completed - Player is safe")
                return "Well played! 🛡️ Safe now"

        # Trading/aggressive play: Check for successful damage or kill
        if "trade" in message or "aggressive" in message or "push" in message:
            time_since_command = time.time() - self.current_command.issued_time
            # If 8+ seconds passed and player is alive, likely executed
            if time_since_command > 8 and game_state.player.is_alive:
                logger.info("✅ Aggressive command executed")
                return "Good execution! 💪"

        return None

    def should_issue_command(self, new_command: CoachingCommand, game_state: GameState) -> bool:
        """
        Decide if we should issue a new command
        Returns True if:
        1. No current command
        2. New command has higher priority
        3. Current command is completed
        4. Current command is stale
        5. Minimum interval passed for NORMAL priority commands
        """
        new_priority = self._get_priority(new_command)

        # Check for command completion first
        completion_msg = self._detect_completion(game_state)
        if completion_msg:
            # Send congratulatory message
            congrats_cmd = CoachingCommand(
                priority="high",
                category="feedback",
                icon="✨",
                message=completion_msg,
                duration=3,
                timestamp=time.time()
            )
            self.current_command = CommandState(congrats_cmd, CommandPriority.HIGH)
            self.last_command_time = time.time()
            logger.info(f"🎉 Sending positive feedback: {completion_msg}")
            return True  # Issue the congratulatory message

        # No current command - issue new one
        if not self.current_command:
            logger.info(f"📢 Issuing new command (priority: {new_priority.name})")
            self.current_command = CommandState(new_command, new_priority)
            self.last_command_time = time.time()
            self._update_state_snapshot(game_state)
            return True

        # Current command is stale - replace it
        if self.current_command.is_stale():
            logger.info("⏰ Current command is stale, issuing new command")
            self.current_command = CommandState(new_command, new_priority)
            self.last_command_time = time.time()
            self._update_state_snapshot(game_state)
            return True

        # New command has higher priority - interrupt current command
        if new_priority > self.current_command.priority:
            logger.info(f"🚨 PRIORITY OVERRIDE: {new_priority.name} > {self.current_command.priority.name}")
            self.current_command = CommandState(new_command, new_priority)
            self.last_command_time = time.time()
            self._update_state_snapshot(game_state)
            return True

        # Allow replacing feedback messages after short delay
        if self.current_command.command.category == "feedback":
            time_since_feedback = time.time() - self.current_command.issued_time
            if time_since_feedback > 3.0:  # Feedback shown for 3+ seconds
                logger.info("✅ Feedback message expired, issuing new command")
                self.current_command = CommandState(new_command, new_priority)
                self.last_command_time = time.time()
                self._update_state_snapshot(game_state)
                return True

        # For NORMAL/MEDIUM priority, respect minimum interval only with same priority
        if new_priority == CommandPriority.NORMAL:
            time_since_last = time.time() - self.last_command_time
            if time_since_last < self.min_command_interval:
                logger.debug(f"⏸️  Holding NORMAL command (last: {time_since_last:.1f}s ago)")
                return False
            else:
                # Enough time passed for NORMAL priority update
                self.current_command = CommandState(new_command, new_priority)
                self.last_command_time = time.time()
                self._update_state_snapshot(game_state)
                return True

        # Current command is still valid, don't spam new commands
        logger.debug("⏸️  Current command still active, not issuing new command")
        return False

    def _update_state_snapshot(self, game_state: GameState):
        """Update state snapshot for completion detection"""
        self.last_gold = game_state.player.gold
        self.last_hp = game_state.player.hp

    def get_current_command(self) -> Optional[CoachingCommand]:
        """Get the currently active command"""
        if self.current_command and self.current_command.should_keep_displaying():
            return self.current_command.command
        return None

    def reset(self):
        """Reset command state (e.g., when game ends)"""
        self.current_command = None
        self.last_command_time = 0
