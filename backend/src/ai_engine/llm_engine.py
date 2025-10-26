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

    def _should_trigger_llm(self, game_state: GameState) -> bool:
        """
        Trigger gates for LLM calls (avoid spam, only call when strategic decision needed)
        Returns True if LLM should be invoked
        """
        # Debouncing: ≤1 call per 2 seconds
        now = time.time()
        if now - self.last_llm_call_time < self.min_call_interval:
            return False

        # Gate 1: Wave near tower + objective <75s
        wave_near_tower = game_state.wave.wave_position in ["ally_tower", "enemy_tower"]
        objective_soon = (
            (game_state.objectives.dragon_spawn_time and game_state.objectives.dragon_spawn_time < 75) or
            (game_state.objectives.baron_spawn_time and game_state.objectives.baron_spawn_time < 75) or
            (game_state.objectives.herald_spawn_time and game_state.objectives.herald_spawn_time < 75)
        )
        if wave_near_tower and objective_soon:
            return True

        # Gate 2: Power spike (1200+ gold, can buy item)
        if game_state.player.gold >= 1200:
            return True

        # Gate 3: Multiple enemies missing + past river
        if game_state.vision.enemy_missing_count >= 3 and game_state.wave.wave_position == "enemy_tower":
            return True

        # Gate 4: Early game laning phase (every 30s for wave management)
        if game_state.game_time < 900 and now - self.last_llm_call_time > 30:
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

                return directive

        except Exception as e:
            logger.error(f"LLM objective coaching failed: {e}")

        return None
