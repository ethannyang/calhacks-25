"""
League Game Client API - Real-time in-game data
Connects to the local game client running on https://127.0.0.1:2999
Provides real-time ability cooldowns, positions, and combat data
"""

import aiohttp
import ssl
from typing import Optional, Dict, List
from loguru import logger


class GameClientAPI:
    """
    Connects to League game client's local API
    https://developer.riotgames.com/docs/lol#game-client-api
    """

    def __init__(self):
        self.base_url = "https://127.0.0.1:2999/liveclientdata"
        # Game client uses self-signed certificate, so we need to disable SSL verification
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Create session if it doesn't exist"""
        if not self.session:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)

    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, endpoint: str) -> Optional[Dict]:
        """Make request to game client API"""
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.debug(f"Game client API returned {response.status}")
                    return None
        except aiohttp.ClientError:
            # Game not running or API not available
            return None
        except Exception as e:
            logger.debug(f"Game client API error: {e}")
            return None

    async def is_game_running(self) -> bool:
        """Check if game is currently running"""
        data = await self._request("/gamestats")
        return data is not None

    async def get_all_game_data(self) -> Optional[Dict]:
        """
        Get all game data in one request (most efficient)
        Returns: {
            'activePlayer': {...},  # Your champion
            'allPlayers': [...],     # All champions in game
            'events': {...},         # Game events
            'gameData': {...}        # Game state
        }
        """
        return await self._request("/allgamedata")

    async def get_active_player(self) -> Optional[Dict]:
        """
        Get your champion's data
        Returns: {
            'abilities': {
                'Q': {'abilityLevel': 5, 'displayName': '...', 'id': '...', 'rawDescription': '...'},
                'W': {...},
                'E': {...},
                'R': {...},
                'Passive': {...}
            },
            'championStats': {
                'abilityPower': 0,
                'armor': 36.0,
                'armorPenetrationFlat': 0,
                'attackDamage': 66.0,
                'attackRange': 175.0,
                'currentHealth': 683.0,
                'healthRegenRate': 10.0,
                'magicResist': 32.0,
                'maxHealth': 683.0,
                'moveSpeed': 340.0,
                'resourceMax': 0.0,
                'resourceValue': 0.0
            },
            'currentGold': 500.0,
            'level': 1,
            'summonerName': '...'
        }
        """
        return await self._request("/activeplayer")

    async def get_active_player_abilities(self) -> Optional[Dict]:
        """Get your champion's ability cooldowns"""
        return await self._request("/activeplayerabilities")

    async def get_all_players(self) -> Optional[List[Dict]]:
        """
        Get all champions in the game with positions
        Returns: [
            {
                'championName': 'Garen',
                'isBot': False,
                'isDead': False,
                'items': [...],
                'level': 1,
                'position': 'TOP',
                'respawnTimer': 0.0,
                'runes': {...},
                'scores': {
                    'assists': 0,
                    'creepScore': 0,
                    'deaths': 0,
                    'kills': 0,
                    'wardScore': 0.0
                },
                'summonerName': '...',
                'team': 'ORDER'
            },
            ...
        ]
        """
        return await self._request("/playerlist")

    async def get_player_scores(self, summoner_name: str) -> Optional[Dict]:
        """Get specific player's scores"""
        return await self._request(f"/playerscores?summonerName={summoner_name}")

    async def get_player_summoner_spells(self, summoner_name: str) -> Optional[Dict]:
        """Get specific player's summoner spell cooldowns"""
        return await self._request(f"/playersummonerspells?summonerName={summoner_name}")

    async def get_player_main_runes(self, summoner_name: str) -> Optional[Dict]:
        """Get specific player's main runes"""
        return await self._request(f"/playermainrunes?summonerName={summoner_name}")

    async def get_player_items(self, summoner_name: str) -> Optional[List[Dict]]:
        """Get specific player's items"""
        return await self._request(f"/playeritems?summonerName={summoner_name}")

    async def get_game_events(self) -> Optional[Dict]:
        """
        Get recent game events
        Returns events like kills, assists, tower destroyed, etc.
        """
        return await self._request("/eventdata")

    async def get_game_stats(self) -> Optional[Dict]:
        """
        Get game stats (game time, mode, etc.)
        Returns: {
            'gameMode': 'CLASSIC',
            'gameTime': 123.45,
            'mapName': 'Map11',
            'mapNumber': 11,
            'mapTerrain': 'Mountain'
        }
        """
        return await self._request("/gamestats")
