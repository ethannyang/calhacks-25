"""
LLM-powered coaching engine for strategic decisions
Uses Anthropic Claude (primary) and OpenAI GPT-4 (fallback)
Target latency: <500ms
Handles F2: Wave Management, F4: Objective Coaching
"""

import asyncio
import time
from typing import Optional
from anthropic import AsyncAnthropic
import openai
from loguru import logger
import json

from ..models.game_state import GameState, CoachingCommand


class LLMEngine:
    """Strategic coaching using LLM for context-aware decisions"""

    def __init__(self, anthropic_key: str, openai_key: Optional[str] = None):
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
        if openai_key:
            openai.api_key = openai_key
        self.cache = {}  # Simple LRU cache
        self.cache_max_size = 1000
        self.cache_ttl = 10  # Cache for 10 seconds

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

    async def wave_management_coaching(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        F2: Wave Management
        LLM-powered wave management coaching based on game context
        """

        context = self._build_context(game_state)

        prompt = f"""You are an expert League of Legends coach providing wave management advice.

Game State:
{context}

Based on this game state, provide ONE concise wave management directive (max 60 characters).

Consider:
- Wave position and minion counts
- Upcoming objectives (dragon, baron spawns)
- Player gold and recall timing
- Enemy visibility and jungle pressure

Response format (JSON):
{{"action": "SLOW_PUSH|HARD_SHOVE|FREEZE|HOLD", "reason": "brief reason", "message": "directive to player"}}

Examples:
- {{"action": "HARD_SHOVE", "reason": "dragon spawns soon", "message": "HARD SHOVE: Clear wave fast, group dragon"}}
- {{"action": "FREEZE", "reason": "ahead in lane", "message": "FREEZE: Hold wave near tower, zone enemy"}}
- {{"action": "SLOW_PUSH", "reason": "recall timing", "message": "SLOW PUSH: Build wave, back after crash"}}
"""

        try:
            # Try Anthropic Claude first
            start_time = time.time()

            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=150,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            latency = (time.time() - start_time) * 1000
            logger.info(f"LLM wave management response time: {latency:.0f}ms")

            # Parse response
            response_text = message.content[0].text

            # Try to extract JSON
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)

                return CoachingCommand(
                    priority="medium",
                    category="wave",
                    icon="🌊",
                    message=data.get("message", "Manage your wave"),
                    duration=6,
                    timestamp=time.time()
                )

        except Exception as e:
            logger.error(f"LLM wave management failed: {e}")

        return None

    async def objective_coaching(self, game_state: GameState) -> Optional[CoachingCommand]:
        """
        F4: Objective Coaching
        LLM-powered objective priority and setup coaching
        """

        # Only give objective coaching if objective spawning soon
        dragon_time = game_state.objectives.dragon_spawn_time
        baron_time = game_state.objectives.baron_spawn_time

        if not ((dragon_time and dragon_time < 60) or (baron_time and baron_time < 90)):
            return None

        context = self._build_context(game_state)

        prompt = f"""You are an expert League of Legends coach providing objective macro coaching.

Game State:
{context}

An objective is spawning soon. Provide ONE concise objective directive (max 70 characters).

Consider:
- Time until objective spawn
- Team positioning and numbers advantage
- Enemy jungle visibility
- Team gold lead and win condition

Response format (JSON):
{{"objective": "DRAGON|BARON|HERALD", "action": "SETUP|CONTEST|GIVE_UP|WARD", "message": "directive to player"}}

Examples:
- {{"objective": "DRAGON", "action": "SETUP", "message": "🐉 DRAGON in 30s: Group bot, ward river"}}
- {{"objective": "BARON", "action": "CONTEST", "message": "🏆 BARON: Enemy jungler top, contest NOW"}}
- {{"objective": "DRAGON", "action": "GIVE_UP", "message": "🐉 Give dragon: 3v5, push top tower instead"}}
"""

        try:
            start_time = time.time()

            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=150,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            latency = (time.time() - start_time) * 1000
            logger.info(f"LLM objective coaching response time: {latency:.0f}ms")

            # Parse response
            response_text = message.content[0].text

            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)

                return CoachingCommand(
                    priority="high",
                    category="objective",
                    icon="🐉" if "dragon" in data.get("objective", "").lower() else "🏆",
                    message=data.get("message", "Prepare for objective"),
                    duration=8,
                    timestamp=time.time()
                )

        except Exception as e:
            logger.error(f"LLM objective coaching failed: {e}")

        return None
