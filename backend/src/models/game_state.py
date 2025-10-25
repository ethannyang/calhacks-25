"""
Pydantic models for League of Legends game state
Represents all data needed for coaching decisions
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class GamePhase(str, Enum):
    """Game phase enum"""
    EARLY = "early"  # 0-15 minutes
    MID = "mid"      # 15-25 minutes
    LATE = "late"    # 25+ minutes


class Position(BaseModel):
    """Position coordinates"""
    x: float
    y: float


class ChampionState(BaseModel):
    """Individual champion state"""
    champion_name: str
    summoner_name: str
    level: int
    hp: int
    hp_max: int
    mana: int
    mana_max: int
    position: Optional[Position] = None
    is_alive: bool = True
    death_timer: Optional[int] = None  # seconds until respawn
    gold: int = 0
    cs: int = 0  # creep score
    kills: int = 0
    deaths: int = 0
    assists: int = 0


class PlayerState(ChampionState):
    """Player (user) specific state"""
    summoner_spell_1_cd: Optional[int] = None  # cooldown in seconds
    summoner_spell_2_cd: Optional[int] = None
    recall_status: bool = False
    vision_score: int = 0
    wards_placed: int = 0
    wards_available: int = 2


class ObjectiveState(BaseModel):
    """Dragon, Baron, Herald objectives"""
    dragon_spawn_time: Optional[int] = None  # seconds
    baron_spawn_time: Optional[int] = None
    herald_spawn_time: Optional[int] = None
    dragons_killed_team: int = 0
    dragons_killed_enemy: int = 0
    barons_killed_team: int = 0
    barons_killed_enemy: int = 0


class WaveState(BaseModel):
    """Minion wave state"""
    allied_minions: int = 0
    enemy_minions: int = 0
    cannon_wave: bool = False
    wave_position: str = "mid"  # "ally_tower", "mid", "enemy_tower"


class VisionState(BaseModel):
    """Vision and map control"""
    enemy_visible_count: int = 0  # enemies visible on minimap
    enemy_missing_count: int = 5  # enemies missing from vision
    allied_wards_active: int = 0
    vision_near_objective: bool = False


class GameState(BaseModel):
    """Complete game state snapshot"""
    game_time: int = Field(..., description="Game time in seconds")
    game_phase: GamePhase

    # Player data
    player: PlayerState

    # Team data
    team_score: int = 0  # team kills
    enemy_score: int = 0  # enemy kills
    team_towers: int = 11
    enemy_towers: int = 11
    team_gold_lead: int = 0  # positive = ahead, negative = behind

    # Allies and enemies
    allies: List[ChampionState] = []
    enemies: List[ChampionState] = []

    # Objectives
    objectives: ObjectiveState

    # Wave and vision
    wave: WaveState
    vision: VisionState

    # Metadata
    timestamp: float = Field(..., description="Unix timestamp of capture")


class CoachingCommand(BaseModel):
    """Coaching command to display to player"""
    priority: str = Field(..., description="low, medium, high, critical")
    category: str = Field(..., description="safety, wave, trade, objective, rotation, recall, vision, position")
    icon: str = Field(..., description="Emoji icon")
    message: str = Field(..., description="Directive coaching message")
    duration: int = Field(default=5, description="Display duration in seconds")
    timestamp: float = Field(..., description="Unix timestamp")
