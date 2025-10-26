"""
Pydantic models for League of Legends game state
Represents all data needed for coaching decisions
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Severity(Enum):
    """Directive severity levels"""
    INFO = 0
    WARN = 1
    DANGER = 2


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


# ============================================================================
# Enhanced Models (Spec-aligned)
# ============================================================================

class ROI(BaseModel):
    """Region of Interest for screen capture"""
    name: Literal["gold", "cs", "hp", "mana", "timer", "minimap"]
    x: int
    y: int
    w: int
    h: int


class OcrSnapshot(BaseModel):
    """OCR extraction snapshot"""
    ts_ms: int
    res: str  # e.g., "1920x1080@100%"
    values: Dict[str, Any]  # {"gold":1250, "cs":68, "timer":"11:40", ...}


class RiotLive(BaseModel):
    """Live data from Riot API"""
    ts_ms: int
    game_time: float
    dragons: Dict[str, int]  # {"ally":1, "enemy":0}
    baron_alive: bool
    participants: List[Dict[str, Any]]  # id, champ, lvl, items, sums_cd, etc.


class AggregatedState(BaseModel):
    """Unified game state for decision making"""
    ts_ms: int
    lane: str  # top/mid/bot/jg/supp
    role: str  # adc/support/...
    hp: float
    mana: float
    gold: int
    cs: int
    waves: Dict[str, str]  # {"top":"slow_push_to_enemy", ...}
    mm_missing: int
    jg_last_seen: Optional[str] = None
    timers: Dict[str, int]  # {"dragon":70, "herald":-1, "baron":420}
    vision: Dict[str, bool]  # {"bot_river":True, ...}
    spikes: Dict[str, bool]  # {"lvl6":True, "mythic_ready":False}


class DirectivePrimary(BaseModel):
    """Primary coaching directive"""
    window: str  # e.g., "Now→+90s"
    text: str  # Main directive
    setup: str  # How to prepare
    requirements: str  # What you need
    success: str  # Expected outcome
    risk: str  # Potential danger
    confidence: float  # 0.0-1.0


class DirectiveV1(BaseModel):
    """Complete directive message (wire format)"""
    t: Literal["directive.v1"] = "directive.v1"
    ts_ms: int
    primary: DirectivePrimary
    backupA: str
    backupB: str
    micro: Dict[str, str]  # {"top":"hold TP", "jg":"hover mid→bot", ...}
    timers: Dict[str, int]  # {"dragon":45, "malphiteR":40, ...}
    priority: Literal["low", "medium", "high", "critical"]
