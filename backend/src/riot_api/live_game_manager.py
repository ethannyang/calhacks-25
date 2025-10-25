"""
Live game state manager
Polls Riot API to track:
- Champion identities and roles
- Team composition
- Summoner spell IDs
- Game mode and time
"""

from typing import Optional, Dict, List, Tuple
from loguru import logger
import asyncio
import time

from .client import RiotAPIClient
from src.ai_engine.build_tracker import BuildTracker


class LiveGameManager:
    """Manages live game data from Riot API"""

    # Common summoner spell IDs
    SMITE_ID = 11  # Jungle indicator
    TELEPORT_ID = 12  # Often top lane
    FLASH_ID = 4
    IGNITE_ID = 14
    EXHAUST_ID = 3
    HEAL_ID = 7

    def __init__(self, riot_client: RiotAPIClient, game_name: str, tag_line: str):
        self.riot_client = riot_client
        self.game_name = game_name
        self.tag_line = tag_line
        self.riot_id = f"{game_name}#{tag_line}"
        self.game_data: Optional[Dict] = None

        # Static data caches
        self.champion_data: Dict = {}
        self.item_data: Dict = {}
        self.spell_data: Dict = {}

        # Player info
        self.summoner_id: Optional[str] = None
        self.player_participant_id: Optional[int] = None
        self.player_team_id: Optional[int] = None
        self.player_role: Optional[str] = None
        self.player_champion_id: Optional[int] = None
        self.player_champion_name: Optional[str] = None

        # Team tracking
        self.ally_participants: List[Dict] = []
        self.enemy_participants: List[Dict] = []

        # Build tracker
        self.build_tracker: Optional[BuildTracker] = None

        # Timestamps
        self.last_api_fetch: float = 0
        self.fetch_interval: float = 10.0  # Fetch every 10 seconds

    async def initialize(self):
        """Load static data and summoner info on startup"""
        logger.info(f"Initializing LiveGameManager for Riot ID: {self.riot_id}")

        # Load Data Dragon assets (no rate limit, can be cached long-term)
        logger.info("Loading static game data from Data Dragon...")
        self.champion_data = await self.riot_client.get_champion_data() or {}
        self.item_data = await self.riot_client.get_item_data() or {}
        self.spell_data = await self.riot_client.get_summoner_spell_data() or {}

        # Get summoner info using Riot ID
        summoner = await self.riot_client.get_summoner_by_riot_id(self.game_name, self.tag_line)
        if not summoner:
            raise ValueError(f"Riot ID '{self.riot_id}' not found in region {self.riot_client.region}")

        # Modern Riot API uses PUUID instead of encrypted summoner ID
        self.summoner_id = summoner.get('puuid') or summoner.get('id')
        if not self.summoner_id:
            logger.error(f"Summoner data missing 'puuid' field. Keys: {list(summoner.keys())}")
            raise ValueError(f"Invalid summoner data for '{self.riot_id}'")

        logger.info(f"✅ Summoner found: {self.riot_id} (PUUID: {self.summoner_id[:8]}...)")

        # Initialize BuildTracker with item data
        self.build_tracker = BuildTracker(self.item_data)
        logger.info("✅ BuildTracker initialized")

    async def fetch_live_game(self, force: bool = False) -> bool:
        """
        Fetch current live game data
        Returns True if player is in game, False otherwise

        Args:
            force: Bypass the fetch interval cooldown
        """
        now = time.time()

        # Rate limit our API calls (don't spam every frame)
        if not force and (now - self.last_api_fetch) < self.fetch_interval:
            return self.game_data is not None

        self.last_api_fetch = now

        # Fetch active game
        game = await self.riot_client.get_active_game(self.summoner_id)

        if not game:
            if self.game_data is not None:
                logger.info("❌ Player left the game")
            self.game_data = None
            return False

        self.game_data = game

        # Parse game data
        self._parse_game_data()

        logger.info(
            f"🎮 Live game detected - "
            f"Role: {self.player_role}, "
            f"Champion: {self.player_champion_name}, "
            f"Game Time: {game.get('gameLength', 0)}s"
        )

        return True

    def _parse_game_data(self):
        """Parse game data and identify player, allies, enemies"""
        if not self.game_data:
            return

        # Find player in participant list (match by PUUID in V5 API)
        for participant in self.game_data['participants']:
            # V5 API uses 'puuid' and 'riotId' instead of 'summonerId' and 'summonerName'
            participant_puuid = participant.get('puuid')
            participant_riot_id = participant.get('riotId', '')  # Format: "GameName#TAG"

            if participant_puuid == self.summoner_id or participant_riot_id.lower() == self.riot_id.lower():
                self.player_participant_id = participant.get('participantId')
                self.player_champion_id = participant['championId']
                self.player_champion_name = self.get_champion_name(self.player_champion_id)
                self.player_team_id = participant['teamId']
                self.player_role = self._detect_role(participant)
                break

        if not self.player_participant_id:
            logger.warning(f"Could not find player '{self.riot_id}' in participant list")
            return

        # Separate allies and enemies
        self.ally_participants = []
        self.enemy_participants = []

        for p in self.game_data['participants']:
            formatted = self._format_participant(p)

            if p['teamId'] == self.player_team_id:
                if p['participantId'] != self.player_participant_id:
                    self.ally_participants.append(formatted)
            else:
                self.enemy_participants.append(formatted)

        # Set build path for player champion + role
        if self.build_tracker and self.player_champion_name and self.player_role:
            enemy_laner = self.get_enemy_laner()
            enemy_champ = enemy_laner.get('champion_name') if enemy_laner else None
            self.build_tracker.set_build_path(
                champion=self.player_champion_name.lower(),
                role=self.player_role,
                enemy_champion=enemy_champ
            )

    def _format_participant(self, participant: Dict) -> Dict:
        """Format participant data into a clean dict"""
        # V5 API uses 'riotId' instead of 'summonerName'
        riot_id = participant.get('riotId', 'Unknown')
        summoner_name = riot_id.split('#')[0] if '#' in riot_id else riot_id

        return {
            'summoner_name': summoner_name,
            'riot_id': riot_id,
            'champion_id': participant['championId'],
            'champion_name': self.get_champion_name(participant['championId']),
            'team_id': participant['teamId'],
            'spell1_id': participant.get('spell1Id'),
            'spell2_id': participant.get('spell2Id'),
            'role': self._detect_role(participant),
        }

    def _detect_role(self, participant: Dict) -> str:
        """
        Detect player role from participant data
        Uses summoner spells as primary indicator
        """
        spell1 = participant.get('spell1Id')
        spell2 = participant.get('spell2Id')

        # Smite = Jungle
        if spell1 == self.SMITE_ID or spell2 == self.SMITE_ID:
            return "jungle"

        # Teleport typically = Top lane (or mid in some metas)
        if spell1 == self.TELEPORT_ID or spell2 == self.TELEPORT_ID:
            return "top"

        # Exhaust often = Support
        if spell1 == self.EXHAUST_ID or spell2 == self.EXHAUST_ID:
            return "support"

        # Heal often = ADC (bot carry)
        if spell1 == self.HEAL_ID or spell2 == self.HEAL_ID:
            return "adc"

        # Default to unknown (could be mid or other roles)
        return "mid"  # Fallback assumption

    def get_champion_name(self, champion_id: int) -> str:
        """Convert champion ID to champion name"""
        if not self.champion_data.get('data'):
            return f"Champion{champion_id}"

        for champ in self.champion_data['data'].values():
            if int(champ['key']) == champion_id:
                return champ['name']

        return f"Champion{champion_id}"

    def get_enemy_jungler(self) -> Optional[Dict]:
        """Get enemy jungler champion info"""
        for enemy in self.enemy_participants:
            if enemy['role'] == 'jungle':
                return enemy
        return None

    def get_enemy_laner(self) -> Optional[Dict]:
        """
        Get the enemy laner in your lane (same role as player)
        Returns enemy champion in your lane
        """
        for enemy in self.enemy_participants:
            if enemy['role'] == self.player_role:
                return enemy
        return None

    def get_all_participants(self) -> List[Dict]:
        """Get all participants (allies + enemies)"""
        return self.ally_participants + self.enemy_participants

    def is_in_game(self) -> bool:
        """Check if player is currently in an active game"""
        return self.game_data is not None

    def get_game_time(self) -> int:
        """Get current game time in seconds"""
        if not self.game_data:
            return 0
        return self.game_data.get('gameLength', 0)

    def get_game_mode(self) -> str:
        """Get game mode (CLASSIC, ARAM, etc.)"""
        if not self.game_data:
            return "UNKNOWN"
        return self.game_data.get('gameMode', 'UNKNOWN')

    def get_summoner_spell_name(self, spell_id: int) -> str:
        """Get summoner spell name from ID"""
        if not self.spell_data.get('data'):
            return f"Spell{spell_id}"

        for spell in self.spell_data['data'].values():
            if int(spell['key']) == spell_id:
                return spell['name']

        return f"Spell{spell_id}"

    def get_item_recommendation(self, current_gold: int) -> Optional[Dict]:
        """Get next item recommendation from build tracker"""
        if not self.build_tracker:
            return None
        return self.build_tracker.get_next_item_recommendation(current_gold)

    def get_recall_recommendation(self, current_gold: int) -> Optional[Dict]:
        """Get recall recommendation based on current gold and item costs"""
        if not self.build_tracker:
            return None
        return self.build_tracker.should_recall_for_item(current_gold)

    def get_context_summary(self, current_gold: int = 0) -> Dict:
        """
        Get a summary of live game context for AI coaching
        Returns dict with key strategic info including build recommendations
        """
        if not self.is_in_game():
            return {}

        enemy_jungler = self.get_enemy_jungler()
        enemy_laner = self.get_enemy_laner()

        context = {
            'in_game': True,
            'game_time': self.get_game_time(),
            'game_mode': self.get_game_mode(),
            'player': {
                'role': self.player_role,
                'champion': self.player_champion_name,
            },
            'enemy_jungler': {
                'champion': enemy_jungler['champion_name'] if enemy_jungler else 'Unknown',
                'exists': enemy_jungler is not None,
            },
            'enemy_laner': {
                'champion': enemy_laner['champion_name'] if enemy_laner else 'Unknown',
                'exists': enemy_laner is not None,
            },
            'team_size': len(self.ally_participants) + 1,  # +1 for player
            'enemy_team_size': len(self.enemy_participants),
        }

        # Add build recommendations if gold is provided
        if current_gold > 0 and self.build_tracker:
            item_rec = self.get_item_recommendation(current_gold)
            if item_rec:
                context['build_recommendation'] = item_rec

        return context
