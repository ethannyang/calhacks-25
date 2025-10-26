"""
LLM-powered coaching engine for strategic decisions
Uses Anthropic Claude (primary) and OpenAI GPT-4 (fallback)
Target latency: <500ms
Handles F2: Wave Management, F4: Objective Coaching
"""

import asyncio
import time
from typing import Optional, Dict, Any
from anthropic import AsyncAnthropic
import openai
from loguru import logger
import json

from ..models.game_state import GameState, CoachingCommand, DirectiveV1, DirectivePrimary, AggregatedState


class LLMEngine:
    """Strategic coaching using LLM for context-aware decisions"""

    def __init__(self, anthropic_key: str, openai_key: Optional[str] = None):
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
        if openai_key:
            openai.api_key = openai_key
        self.cache: Dict[str, Any] = {}  # Simple LRU cache
        self.cache_max_size = 1000
        self.cache_ttl = 10  # Cache for 10 seconds
        self.last_llm_call_time = 0
        self.min_call_interval = 2.0  # Debouncing: ≤1 call per 2 seconds

        # Directive history tracking
        self.directive_history = []  # List of (timestamp, directive_type, text) tuples
        self.history_window = 30  # Don't repeat similar directives within 30 seconds
        self.max_history_size = 20  # Keep last 20 directives

    def _should_trigger_llm(self, game_state: GameState) -> bool:
        """
        Trigger gates for LLM calls (avoid spam, only call when strategic decision needed)
        Returns True if LLM should be invoked
        """
        # Debouncing: ≤1 call per 2 seconds
        now = time.time()
        if now - self.last_llm_call_time < self.min_call_interval:
            return False

        # Gate 1: Wave position changes (more frequent coaching)
        wave_positions_of_interest = ["ally_tower", "enemy_tower", "midfield", "enemy_side"]
        if game_state.wave.wave_position in wave_positions_of_interest:
            # Trigger every 10 seconds when wave is in key position
            if now - self.last_llm_call_time > 10:
                return True

        # Gate 2: Objective spawning within 2 minutes (expanded window)
        objective_soon = (
            (game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 120) or
            (game_state.objectives.baron_spawn_time and game_state.objectives.baron_spawn_time < 120) or
            (game_state.objectives.herald_spawn_time and game_state.objectives.herald_spawn_time < 120)
        )
        if objective_soon:
            return True

        # Gate 3: Power spike (800+ gold, lowered threshold)
        if game_state.player.gold >= 800:
            return True

        # Gate 4: Vision-based coaching (2+ enemies missing)
        if game_state.vision.enemy_missing_count >= 2:
            return True

        # Gate 5: HP/Mana thresholds for backing decisions
        hp_low = game_state.player.hp / game_state.player.hp_max < 0.4
        mana_low = game_state.player.mana_max > 0 and (game_state.player.mana / game_state.player.mana_max < 0.3)
        if hp_low or mana_low:
            return True

        # Gate 6: Regular interval coaching (every 15s for consistent guidance)
        if now - self.last_llm_call_time > 15:
            return True

        return False

    def _add_to_history(self, directive_type: str, text: str):
        """Add a directive to history and maintain size limit"""
        now = time.time()
        self.directive_history.append((now, directive_type, text))

        # Remove old entries beyond history window
        cutoff_time = now - self.history_window * 2  # Keep 2x window for reference
        self.directive_history = [
            (t, dt, txt) for t, dt, txt in self.directive_history
            if t > cutoff_time
        ]

        # Maintain max size
        if len(self.directive_history) > self.max_history_size:
            self.directive_history = self.directive_history[-self.max_history_size:]

    def _was_recently_used(self, directive_type: str) -> bool:
        """Check if this directive type was used recently"""
        now = time.time()
        cutoff_time = now - self.history_window

        for timestamp, dtype, _ in self.directive_history:
            if timestamp > cutoff_time and dtype == directive_type:
                return True
        return False

    def _build_context(self, game_state: GameState) -> str:
        """Build structured context for LLM"""
        context = {
            "game_time": f"{game_state.game_time // 60}:{game_state.game_time % 60:02d}",
            "game_phase": game_state.game_phase,
            "player": {
                "champion": game_state.player.champion_name,
                "level": game_state.player.level,
                "hp_percent": round(game_state.player.hp / game_state.player.hp_max * 100),
                "mana_percent": round(game_state.player.mana / game_state.player.mana_max * 100) if game_state.player.mana_max > 0 else 100,
                "gold": game_state.player.gold,
                "cs": game_state.player.cs,
                "kda": f"{game_state.player.kills}/{game_state.player.deaths}/{game_state.player.assists}"
            },
            "wave": {
                "position": game_state.wave.wave_position,
                "allied_minions": game_state.wave.allied_minions,
                "enemy_minions": game_state.wave.enemy_minions,
                "cannon_wave": game_state.wave.cannon_wave
            },
            "vision": {
                "enemies_visible": game_state.vision.enemy_visible_count,
                "enemies_missing": game_state.vision.enemy_missing_count,
            },
            "objectives": {
                "dragon_spawn": game_state.objectives.dragon_spawn_time,
                "baron_spawn": game_state.objectives.baron_spawn_time,
            },
            "team_state": {
                "gold_lead": game_state.team_gold_lead,
                "score": f"{game_state.team_score}:{game_state.enemy_score}",
                "towers": f"{game_state.team_towers}:{game_state.enemy_towers}"
            }
        }
        return json.dumps(context, indent=2)

    async def wave_management_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        F2: Wave Management
        LLM-powered wave management coaching based on game context
        Returns DirectiveV1 format with primary/backup/micro/timers
        """

        # Check trigger gates
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("wave_management"):
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players (beginner/intermediate). Return structured directives in under 60 words. Focus on one clear action with setup steps and risk awareness."""

        prompt = f"""Game State:
{context}

Provide a wave management directive in this JSON format:
{{
  "window": "Now→+90s",
  "text": "Main directive (what to do now)",
  "setup": "How to prepare for this",
  "requirements": "What you need (gold/HP/vision)",
  "success": "Expected outcome",
  "risk": "Potential danger",
  "confidence": 0.8,
  "backupA": "Alternative plan if this fails",
  "backupB": "Safe fallback option",
  "micro": {{"jg": "hint for jungler", "sup": "hint for support"}},
  "timers": {{"dragon": 45, "baron": 120}},
  "priority": "medium"
}}

Consider wave position, objectives, gold, and enemy visibility. Keep it simple and actionable for beginner players."""

        try:
            # Try Anthropic Claude first
            start_time = time.time()

            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,  # Increased to prevent truncation
                temperature=0.3,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            latency = (time.time() - start_time) * 1000
            logger.info(f"LLM wave management response time: {latency:.0f}ms")

            # Update last call time
            self.last_llm_call_time = time.time()

            # Parse response
            response_text = message.content[0].text
            logger.debug(f"LLM raw response: {response_text[:500]}")  # Log first 500 chars

            # Try to extract JSON
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                logger.debug(f"Extracted JSON string: {json_str[:500]}")

                try:
                    data = json.loads(json_str)
                    logger.debug(f"Parsed JSON data: {data}")
                except json.JSONDecodeError as je:
                    logger.error(f"JSON parse error: {je}")
                    logger.error(f"Failed JSON string: {json_str}")
                    return None

                # Build DirectivePrimary
                primary = DirectivePrimary(
                    window=data.get("window", "Now→+60s"),
                    text=data.get("text", "Manage wave position"),
                    setup=data.get("setup", "Watch minimap, track enemies"),
                    requirements=data.get("requirements", "Map awareness"),
                    success=data.get("success", "Better wave control"),
                    risk=data.get("risk", "Jungle gank"),
                    confidence=data.get("confidence", 0.7)
                )

                # Build DirectiveV1
                # Fix None values in timers dict
                timers_raw = data.get("timers", {})
                timers_clean = {k: v for k, v in timers_raw.items() if v is not None}

                directive = DirectiveV1(
                    t="directive.v1",  # Required field!
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Play safe, farm under tower"),
                    backupB=data.get("backupB", "Ward, group with team"),
                    micro=data.get("micro", {}),
                    timers=timers_clean,  # Only include non-None timers
                    priority=data.get("priority", "medium")
                )

                # Add to history to prevent repetition
                self._add_to_history("wave_management", directive.primary.text)

                logger.info(f"Successfully created directive: {directive.primary.text}")
                return directive
            else:
                logger.error(f"No JSON found in response: {response_text[:200]}")
                return None

        except Exception as e:
            logger.error(f"LLM wave management failed: {e}")

        return None

    async def objective_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        F4: Objective Coaching
        LLM-powered objective priority and setup coaching
        Returns DirectiveV1 format
        """

        # Only give objective coaching if objective spawning soon
        dragon_time = game_state.objectives.dragon_spawn_time
        baron_time = game_state.objectives.baron_spawn_time
        herald_time = game_state.objectives.herald_spawn_time

        if not ((dragon_time and dragon_time < 60) or
                (baron_time and baron_time < 90) or
                (herald_time and herald_time < 90)):
            return None

        # Check trigger gates
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("objective"):
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players (beginner/intermediate). Return structured directives in under 60 words. Focus on one clear action with setup steps and risk awareness."""

        prompt = f"""Game State:
{context}

An objective is spawning soon. Provide a directive in this JSON format:
{{
  "window": "Now→+60s",
  "text": "Main objective directive",
  "setup": "How to prepare (warding, grouping)",
  "requirements": "What you need (vision, teammates)",
  "success": "Expected outcome",
  "risk": "Potential danger",
  "confidence": 0.8,
  "backupA": "Alternative if can't contest",
  "backupB": "Safe fallback option",
  "micro": {{"jg": "jungler hint", "sup": "support hint"}},
  "timers": {{"dragon": 30, "baron": 120}},
  "priority": "high"
}}

Consider team numbers, vision, and gold lead. Keep it simple for beginner players."""

        try:
            start_time = time.time()

            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,  # Increased to prevent truncation
                temperature=0.3,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            latency = (time.time() - start_time) * 1000
            logger.info(f"LLM objective coaching response time: {latency:.0f}ms")

            # Update last call time
            self.last_llm_call_time = time.time()

            # Parse response
            response_text = message.content[0].text
            logger.debug(f"LLM objective raw response: {response_text[:500]}")

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]

                try:
                    data = json.loads(json_str)
                    logger.debug(f"Parsed objective JSON: {data}")
                except json.JSONDecodeError as je:
                    logger.error(f"Objective JSON parse error: {je}")
                    return None

                # Build DirectivePrimary
                primary = DirectivePrimary(
                    window=data.get("window", "Now→+60s"),
                    text=data.get("text", "Prepare for objective"),
                    setup=data.get("setup", "Group with team, ward area"),
                    requirements=data.get("requirements", "Team presence, vision"),
                    success=data.get("success", "Secure objective"),
                    risk=data.get("risk", "Enemy contest, teamfight"),
                    confidence=data.get("confidence", 0.7)
                )

                # Build DirectiveV1
                # Fix None values in timers dict
                timers_raw = data.get("timers", {})
                timers_clean = {k: v for k, v in timers_raw.items() if v is not None}

                directive = DirectiveV1(
                    t="directive.v1",  # Required field!
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Ward and disengage if outnumbered"),
                    backupB=data.get("backupB", "Give up objective, push lanes"),
                    micro=data.get("micro", {}),
                    timers=timers_clean,  # Only include non-None timers
                    priority=data.get("priority", "high")
                )

                # Add to history to prevent repetition
                self._add_to_history("objective", directive.primary.text)

                return directive

        except Exception as e:
            logger.error(f"LLM objective coaching failed: {e}")

        return None

    async def team_fighting_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        Team fighting positioning and engagement coaching
        """
        # Check trigger gates
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("team_fight"):
            return None

        # Only give team fight coaching when multiple enemies visible
        if game_state.vision.enemy_visible_count < 2:
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players. Return structured directives in under 60 words. Focus on team fight positioning and target selection."""

        prompt = f"""Game State:
{context}

Provide a team fighting directive in this JSON format:
{{
  "window": "Now→+45s",
  "text": "Team fight positioning and engagement",
  "setup": "How to position before fight",
  "requirements": "What you need to engage",
  "success": "Expected outcome",
  "risk": "What to avoid",
  "confidence": 0.7,
  "backupA": "Alternative if fight goes bad",
  "backupB": "Disengage plan",
  "micro": {{"adc": "focus priority", "tank": "peel or engage"}},
  "timers": {{}},
  "priority": "high"
}}"""

        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            self.last_llm_call_time = time.time()
            response_text = message.content[0].text

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                data = json.loads(response_text[json_start:json_end])

                primary = DirectivePrimary(
                    window=data.get("window", "Now→+45s"),
                    text=data.get("text", "Position for team fight"),
                    setup=data.get("setup", "Group with team"),
                    requirements=data.get("requirements", "Team presence"),
                    success=data.get("success", "Win team fight"),
                    risk=data.get("risk", "Getting caught out"),
                    confidence=data.get("confidence", 0.7)
                )

                directive = DirectiveV1(
                    t="directive.v1",
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Disengage if losing"),
                    backupB=data.get("backupB", "Split push instead"),
                    micro=data.get("micro", {}),
                    timers={k: v for k, v in data.get("timers", {}).items() if v is not None},
                    priority=data.get("priority", "high")
                )

                # Add to history to prevent repetition
                self._add_to_history("team_fight", directive.primary.text)

                logger.info(f"[LLM] Team fight directive: {directive.primary.text}")
                return directive

        except Exception as e:
            logger.error(f"Team fighting coaching failed: {e}")

        return None

    async def vision_control_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        Vision and map control coaching
        """
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("vision"):
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players. Focus on vision control and map awareness."""

        prompt = f"""Game State:
{context}

Provide a vision control directive in this JSON format:
{{
  "window": "Now→+60s",
  "text": "Ward placement and vision control",
  "setup": "Where to place wards",
  "requirements": "Control wards or stealth wards",
  "success": "Better map control",
  "risk": "Getting caught warding",
  "confidence": 0.8,
  "backupA": "Alternative ward spots",
  "backupB": "Play safe without vision",
  "micro": {{"sup": "deep ward spots", "jg": "clear enemy vision"}},
  "timers": {{}},
  "priority": "medium"
}}"""

        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            self.last_llm_call_time = time.time()
            response_text = message.content[0].text

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                data = json.loads(response_text[json_start:json_end])

                primary = DirectivePrimary(
                    window=data.get("window", "Now→+60s"),
                    text=data.get("text", "Control vision"),
                    setup=data.get("setup", "Buy control ward"),
                    requirements=data.get("requirements", "Wards available"),
                    success=data.get("success", "Map control"),
                    risk=data.get("risk", "Face checking"),
                    confidence=data.get("confidence", 0.8)
                )

                directive = DirectiveV1(
                    t="directive.v1",
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Ward safely"),
                    backupB=data.get("backupB", "Group for vision"),
                    micro=data.get("micro", {}),
                    timers={k: v for k, v in data.get("timers", {}).items() if v is not None},
                    priority=data.get("priority", "medium")
                )

                # Add to history to prevent repetition
                self._add_to_history("vision", directive.primary.text)

                logger.info(f"[LLM] Vision directive: {directive.primary.text}")
                return directive

        except Exception as e:
            logger.error(f"Vision control coaching failed: {e}")

        return None

    async def itemization_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        Item build and purchase coaching
        """
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("itemization"):
            return None

        # Only suggest items when player has enough gold
        if game_state.player.gold < 400:
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players. Focus on item purchases and build paths."""

        prompt = f"""Game State:
{context}

Provide an itemization directive in this JSON format:
{{
  "window": "Next back",
  "text": "Item to buy next",
  "setup": "Farm for gold or back now",
  "requirements": "Gold amount needed",
  "success": "Power spike achieved",
  "risk": "Delaying core items",
  "confidence": 0.75,
  "backupA": "Alternative item if can't afford",
  "backupB": "Components to buy instead",
  "micro": {{}},
  "timers": {{}},
  "priority": "medium"
}}"""

        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            self.last_llm_call_time = time.time()
            response_text = message.content[0].text

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                data = json.loads(response_text[json_start:json_end])

                primary = DirectivePrimary(
                    window=data.get("window", "Next back"),
                    text=data.get("text", "Buy next item"),
                    setup=data.get("setup", "Farm efficiently"),
                    requirements=data.get("requirements", f"{game_state.player.gold} gold"),
                    success=data.get("success", "Stronger in fights"),
                    risk=data.get("risk", "Wrong item choice"),
                    confidence=data.get("confidence", 0.75)
                )

                directive = DirectiveV1(
                    t="directive.v1",
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Buy components"),
                    backupB=data.get("backupB", "Save for big item"),
                    micro=data.get("micro", {}),
                    timers={k: v for k, v in data.get("timers", {}).items() if v is not None},
                    priority=data.get("priority", "medium")
                )

                # Add to history to prevent repetition
                self._add_to_history("itemization", directive.primary.text)

                logger.info(f"[LLM] Item directive: {directive.primary.text}")
                return directive

        except Exception as e:
            logger.error(f"Itemization coaching failed: {e}")

        return None

    async def backing_timing_coaching(self, game_state: GameState) -> Optional[DirectiveV1]:
        """
        Optimal backing timing coaching
        """
        if not self._should_trigger_llm(game_state):
            return None

        # Skip if this type was recently used
        if self._was_recently_used("backing"):
            return None

        # Check if backing makes sense
        hp_percent = game_state.player.hp / game_state.player.hp_max
        mana_percent = game_state.player.mana / game_state.player.mana_max if game_state.player.mana_max > 0 else 1.0

        # Don't suggest backing if healthy
        if hp_percent > 0.7 and mana_percent > 0.5 and game_state.player.gold < 800:
            return None

        context = self._build_context(game_state)

        system_prompt = """You are a concise LoL coach for Iron–Silver players. Focus on optimal recall timing."""

        prompt = f"""Game State:
{context}

Provide a backing/recall directive in this JSON format:
{{
  "window": "Now→+30s",
  "text": "When and how to recall",
  "setup": "Push wave before backing",
  "requirements": "Wave state needed",
  "success": "Efficient back timing",
  "risk": "Losing CS or plates",
  "confidence": 0.8,
  "backupA": "Stay and farm more",
  "backupB": "Back immediately if urgent",
  "micro": {{}},
  "timers": {{}},
  "priority": "medium"
}}"""

        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            self.last_llm_call_time = time.time()
            response_text = message.content[0].text

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                data = json.loads(response_text[json_start:json_end])

                primary = DirectivePrimary(
                    window=data.get("window", "Now→+30s"),
                    text=data.get("text", "Back to base timing"),
                    setup=data.get("setup", "Push wave first"),
                    requirements=data.get("requirements", "Safe wave state"),
                    success=data.get("success", "Good back timing"),
                    risk=data.get("risk", "Lost resources"),
                    confidence=data.get("confidence", 0.8)
                )

                directive = DirectiveV1(
                    t="directive.v1",
                    ts_ms=int(time.time() * 1000),
                    primary=primary,
                    backupA=data.get("backupA", "Farm more first"),
                    backupB=data.get("backupB", "Back now if low"),
                    micro=data.get("micro", {}),
                    timers={k: v for k, v in data.get("timers", {}).items() if v is not None},
                    priority=data.get("priority", "medium")
                )

                # Add to history to prevent repetition
                self._add_to_history("backing", directive.primary.text)

                logger.info(f"[LLM] Backing directive: {directive.primary.text}")
                return directive

        except Exception as e:
            logger.error(f"Backing timing coaching failed: {e}")

        return None
