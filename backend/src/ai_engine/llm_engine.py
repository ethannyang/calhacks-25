"""
LLM-powered coaching engine for strategic decisions - ENHANCED with live game context
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

    def _build_context(self, game_state: GameState, live_context: dict = None) -> str:
        """Build structured context for LLM with live game data"""
        context = {
            "game_time": f"{game_state.game_time // 60}:{game_state.game_time % 60:02d}",
            "game_phase": game_state.game_phase,
            "player": {
                "champion": game_state.player.champion_name,
                "role": live_context.get('player', {}).get('role', 'unknown') if live_context else 'unknown',
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

        # Add strategic live game context
        if live_context:
            enemy_jungler = live_context.get('enemy_jungler', {})
            enemy_laner = live_context.get('enemy_laner', {})

            context["strategic_info"] = {
                "enemy_jungler": enemy_jungler.get('champion', 'Unknown'),
                "enemy_jungler_detected": enemy_jungler.get('exists', False),
                "lane_opponent": enemy_laner.get('champion', 'Unknown'),
                "lane_opponent_detected": enemy_laner.get('exists', False),
            }

        return json.dumps(context, indent=2)

    async def wave_management_coaching(self, game_state: GameState, live_context: dict = None) -> Optional[CoachingCommand]:
        """
        F2: Wave Management
        LLM-powered wave management coaching based on game context + live data
        """

        context_str = self._build_context(game_state, live_context)
        context_dict = json.loads(context_str)

        # Build strategic context string
        strategic_note = ""
        if live_context and 'strategic_info' in context_dict:
            enemy_jungler = live_context.get('enemy_jungler', {}).get('champion', 'Unknown')
            if enemy_jungler != 'Unknown':
                strategic_note = f"\n\n🎯 STRATEGIC CONTEXT: Enemy jungler is {enemy_jungler}. Use this for pressure decisions."

        prompt = f"""You are an expert League of Legends macro coach. Use the actual game data (HP, mana, gold, CS, game time, minimap) to give SPECIFIC, DATA-DRIVEN coaching.

Game State:
{context_str}{strategic_note}

**YOUR JOB**: Generate ONE specific coaching command with a data-driven reason.

**COMMAND CATEGORIES** (be specific with actual numbers):
1. **MAP AWARENESS**: "⚠️ 3 enemies missing — back off" / reason: "No vision, high gank risk"
2. **ECONOMY**: "Recall for Phage (1100g)" / reason: "You have 1250g, item spike available"
3. **CS TIMING**: "Don't miss cannon wave" / reason: "Cannon worth 60g+, big wave incoming"
4. **RECALL TIMING**: "Push and recall" / reason: "Wave crashing, 1400g for component"
5. **HEALTH/MANA**: "Play safe, low mana" / reason: "25% mana, can't trade or escape"
6. **WAVE STATE**: "Freeze near tower" / reason: "Ahead in lane, deny enemy CS"
7. **OBJECTIVE PREP**: "Shove for dragon (45s)" / reason: "Dragon spawns soon, need priority"
8. **ITEM SPIKES**: "Back for mythic" / reason: "2800g for Trinity Force, power spike"

**MAKE IT SPECIFIC** using the actual data:
- Use exact gold amounts from game state
- Reference actual HP% and mana%
- Mention CS count if relevant (e.g. "80 CS at 10min, keep farming")
- Reference game time for objective timing
- Use enemy missing count for danger level

Response format (JSON):
{{"action": "action_type", "reason": "why (data-driven)", "message": "what to do (specific)", "priority": "critical|high|medium"}}

**Examples with real data**:
- {{"action": "RECALL", "reason": "You have 1550g for Phage + boots", "message": "Recall for Phage (1100g)", "priority": "high"}}
- {{"action": "CS_FOCUS", "reason": "Cannon wave + 3 melees = 150g", "message": "Don't miss cannon wave", "priority": "medium"}}
- {{"action": "RETREAT", "reason": "35% HP, 3 enemies missing", "message": "Play safe — low HP, enemies missing", "priority": "critical"}}
- {{"action": "FREEZE", "reason": "Lane ahead, wave near tower", "message": "Freeze wave — deny enemy CS", "priority": "medium"}}
"""

        try:
            # Try Anthropic Claude first
            start_time = time.time()

            message = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet",
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

                # Get priority from LLM response or default to medium
                llm_priority = data.get("priority", "medium")

                return CoachingCommand(
                    priority=llm_priority,
                    category="wave",
                    icon="🌊",
                    message=data.get("message", "Manage your wave"),
                    reason=data.get("reason", ""),
                    duration=6,
                    timestamp=time.time()
                )

        except Exception as e:
            logger.error(f"LLM wave management failed: {e}")

            # Fallback: Use game state to generate rule-based coaching
            if game_state:
                # Low HP warning
                hp_percent = (game_state.player.hp / game_state.player.hp_max * 100) if game_state.player.hp_max > 0 else 100
                if hp_percent < 40:
                    return CoachingCommand(
                        priority="high",
                        category="safety",
                        icon="❤️",
                        message=f"Low HP ({int(hp_percent)}%) - play safe or recall",
                        duration=6,
                        timestamp=time.time()
                    )

                # Recall for gold
                if game_state.player.gold >= 1300:
                    return CoachingCommand(
                        priority="medium",
                        category="economy",
                        icon="🛒",
                        message=f"You have {game_state.player.gold}g - consider recalling for items",
                        duration=6,
                        timestamp=time.time()
                    )

                # CS reminder
                expected_cs = (game_state.game_time // 60) * 7  # 7 CS per minute
                if game_state.game_time > 180 and game_state.player.cs < expected_cs * 0.7:
                    return CoachingCommand(
                        priority="medium",
                        category="farming",
                        icon="🌾",
                        message=f"CS at {game_state.player.cs} - focus on farming",
                        duration=6,
                        timestamp=time.time()
                    )

        return None

    async def objective_coaching(self, game_state: GameState, live_context: dict = None) -> Optional[CoachingCommand]:
        """
        F4: Objective Coaching
        LLM-powered objective priority and setup coaching
        """

        # Only give objective coaching if objective spawning soon
        dragon_time = game_state.objectives.dragon_spawn_time
        baron_time = game_state.objectives.baron_spawn_time

        if not ((dragon_time and dragon_time < 60) or (baron_time and baron_time < 90)):
            return None

        context_str = self._build_context(game_state, live_context)

        prompt = f"""You are an expert League of Legends coach providing objective macro coaching.

Game State:
{context_str}

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
                model="claude-3-5-sonnet",
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

            # Fallback: Basic objective warnings
            if dragon_time and dragon_time < 60:
                return CoachingCommand(
                    priority="high",
                    category="objective",
                    icon="🐉",
                    message=f"Dragon spawns in {int(dragon_time)}s - get vision",
                    duration=8,
                    timestamp=time.time()
                )
            elif baron_time and baron_time < 90:
                return CoachingCommand(
                    priority="high",
                    category="objective",
                    icon="🏆",
                    message=f"Baron spawns in {int(baron_time)}s - prepare",
                    duration=8,
                    timestamp=time.time()
                )

        return None

    async def answer_coaching_question(self, question: str, game_state: Optional[GameState] = None) -> Optional[CoachingCommand]:
        """
        Answer general coaching questions from voice input
        Uses simple pattern matching for common questions
        """

        question_lower = question.lower()

        # Pattern matching for common questions
        if "recall" in question_lower or "back" in question_lower:
            return CoachingCommand(
                priority="high",
                category="advice",
                icon="🔄",
                message="Recall after pushing wave or when low HP/mana",
                duration=8,
                timestamp=time.time()
            )

        elif "roam" in question_lower or "gank" in question_lower:
            return CoachingCommand(
                priority="medium",
                category="advice",
                icon="🗺️",
                message="Push wave first, then roam - get prio before leaving",
                duration=8,
                timestamp=time.time()
            )

        elif "garen" in question_lower or "beat" in question_lower or "counter" in question_lower:
            return CoachingCommand(
                priority="medium",
                category="advice",
                icon="⚔️",
                message="Kite Garen - avoid Q silence, punish E cooldown",
                duration=8,
                timestamp=time.time()
            )

        elif "build" in question_lower or "item" in question_lower:
            return CoachingCommand(
                priority="low",
                category="advice",
                icon="🛡️",
                message="Rush Black Cleaver vs Garen for armor shred",
                duration=8,
                timestamp=time.time()
            )

        elif "farm" in question_lower or "cs" in question_lower:
            return CoachingCommand(
                priority="medium",
                category="advice",
                icon="🌾",
                message="Focus on last-hitting - aim for 7+ CS per minute",
                duration=8,
                timestamp=time.time()
            )

        elif "trade" in question_lower or "fight" in question_lower:
            return CoachingCommand(
                priority="medium",
                category="advice",
                icon="⚔️",
                message="Trade when enemy abilities are on cooldown",
                duration=8,
                timestamp=time.time()
            )

        elif "ward" in question_lower or "vision" in question_lower:
            return CoachingCommand(
                priority="medium",
                category="advice",
                icon="👁️",
                message="Ward river bush and tri-bush for jungle tracking",
                duration=8,
                timestamp=time.time()
            )

        else:
            # Generic response for unrecognized questions
            return CoachingCommand(
                priority="low",
                category="advice",
                icon="💭",
                message="Focus on CS, map awareness, and trading smart",
                duration=6,
                timestamp=time.time()
            )
