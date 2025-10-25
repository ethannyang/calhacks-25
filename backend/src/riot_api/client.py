"""
Riot API Client with rate limiting and caching
Implements spectator, summoner, and match endpoints
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from loguru import logger
import time
from collections import deque


class RateLimiter:
    """Token bucket rate limiter for Riot API"""

    def __init__(self, rate_per_second: int = 20, rate_per_two_minutes: int = 100):
        self.rate_per_second = rate_per_second
        self.rate_per_two_minutes = rate_per_two_minutes
        self.short_window = deque(maxlen=rate_per_second)
        self.long_window = deque(maxlen=rate_per_two_minutes)

    async def acquire(self):
        """Wait until a request can be made within rate limits"""
        now = time.time()

        # Clean old timestamps
        while self.short_window and now - self.short_window[0] > 1:
            self.short_window.popleft()
        while self.long_window and now - self.long_window[0] > 120:
            self.long_window.popleft()

        # Check if we need to wait
        if len(self.short_window) >= self.rate_per_second:
            sleep_time = 1 - (now - self.short_window[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        if len(self.long_window) >= self.rate_per_two_minutes:
            sleep_time = 120 - (now - self.long_window[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Record this request
        now = time.time()
        self.short_window.append(now)
        self.long_window.append(now)


class RiotAPIClient:
    """Async Riot API client with rate limiting and error handling"""

    BASE_URLS = {
        "na1": "https://na1.api.riotgames.com",
        "euw1": "https://euw1.api.riotgames.com",
        "kr": "https://kr.api.riotgames.com",
        "americas": "https://americas.api.riotgames.com",
        "europe": "https://europe.api.riotgames.com",
        "asia": "https://asia.api.riotgames.com",
    }

    def __init__(self, api_key: str, region: str = "na1"):
        self.api_key = api_key
        self.region = region.lower()
        self.base_url = self.BASE_URLS.get(self.region, self.BASE_URLS["na1"])
        self.rate_limiter = RateLimiter()
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, tuple[Any, float]] = {}  # (data, timestamp)
        self.cache_ttl = 60  # Cache for 60 seconds

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None

    def _set_cache(self, key: str, data: Any):
        """Cache data with timestamp"""
        self._cache[key] = (data, time.time())

    async def _request(self, endpoint: str, params: Optional[Dict] = None, use_cache: bool = True) -> Optional[Dict]:
        """Make rate-limited request to Riot API"""
        cache_key = f"{endpoint}:{params}"

        # Check cache first
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit: {endpoint}")
                return cached

        # Acquire rate limit token
        await self.rate_limiter.acquire()

        # Make request
        url = f"{self.base_url}{endpoint}"
        headers = {"X-Riot-Token": self.api_key}

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    self._set_cache(cache_key, data)
                    return data
                elif response.status == 404:
                    logger.warning(f"Not found: {endpoint}")
                    return None
                elif response.status == 429:
                    logger.error("Rate limit exceeded despite rate limiting")
                    await asyncio.sleep(5)
                    return None
                else:
                    logger.error(f"API error {response.status}: {endpoint}")
                    return None

        except asyncio.TimeoutError:
            logger.error(f"Timeout: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            return None

    async def get_summoner_by_name(self, summoner_name: str) -> Optional[Dict]:
        """
        Get summoner data by name
        Note: Use URL-encoded name. For special characters, use get_summoner_by_riot_id instead.
        """
        import urllib.parse
        encoded_name = urllib.parse.quote(summoner_name)
        endpoint = f"/lol/summoner/v4/summoners/by-name/{encoded_name}"
        return await self._request(endpoint)

    async def get_summoner_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """
        Get summoner data by Riot ID (GameName#TAG)
        This is the new preferred method for Riot's unified platform

        Args:
            game_name: The game name (e.g., "Faker")
            tag_line: The tag line (e.g., "KR1", "NA1")

        Example: get_summoner_by_riot_id("Faker", "KR1")
        """
        # Get regional routing base
        regional_base = self._get_regional_base()

        # First, get account info (PUUID) from account-v1
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

        # Temporarily switch to regional base
        original_base = self.base_url
        self.base_url = regional_base
        account_data = await self._request(endpoint)
        self.base_url = original_base

        if not account_data:
            logger.error(f"Account not found: {game_name}#{tag_line}")
            return None

        # Get PUUID
        puuid = account_data.get('puuid')
        if not puuid:
            logger.error(f"No PUUID in account data for {game_name}#{tag_line}")
            return None

        # Then get summoner data from PUUID
        endpoint = f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        summoner_data = await self._request(endpoint)

        if summoner_data:
            logger.info(f"✅ Found summoner: {game_name}#{tag_line}")

        return summoner_data

    def _get_regional_base(self) -> str:
        """Get regional base URL for account-v1 API"""
        region_mapping = {
            'na1': 'americas',
            'br1': 'americas',
            'la1': 'americas',
            'la2': 'americas',
            'euw1': 'europe',
            'eun1': 'europe',
            'tr1': 'europe',
            'ru': 'europe',
            'kr': 'asia',
            'jp1': 'asia',
        }
        regional_key = region_mapping.get(self.region, 'americas')
        return self.BASE_URLS.get(regional_key, self.BASE_URLS['americas'])

    async def get_active_game(self, encrypted_summoner_id: str) -> Optional[Dict]:
        """
        Get active game data for a summoner
        Args:
            encrypted_summoner_id: Can be either encryptedSummonerId or encryptedPUUID
        """
        endpoint = f"/lol/spectator/v5/active-games/by-summoner/{encrypted_summoner_id}"
        return await self._request(endpoint, use_cache=False)

    async def get_match_history(self, puuid: str, start: int = 0, count: int = 20) -> Optional[list]:
        """Get match history IDs for a player"""
        # Use regional routing for match-v5
        regional_base = self.BASE_URLS.get("americas")  # Americas for NA
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": start, "count": count}

        # Temporarily switch base URL for this request
        original_base = self.base_url
        self.base_url = regional_base
        result = await self._request(endpoint, params=params)
        self.base_url = original_base

        return result

    async def get_champion_rotations(self) -> Optional[Dict]:
        """Get free champion rotations"""
        endpoint = "/lol/platform/v3/champion-rotations"
        return await self._request(endpoint)

    async def get_champion_data(self) -> Optional[Dict]:
        """
        Get static champion data from Data Dragon (no rate limit)
        Returns: {champion_id: {name, title, abilities, ...}}
        """
        url = "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/champion.json"

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Loaded {len(data.get('data', {}))} champions from Data Dragon")
                    return data
                else:
                    logger.error(f"Failed to fetch champion data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch champion data: {e}")
            return None

    async def get_summoner_spell_data(self) -> Optional[Dict]:
        """
        Get summoner spell data (Flash, Ignite, TP, etc.) from Data Dragon
        Returns: {spell_id: {name, cooldown, ...}}
        """
        url = "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/summoner.json"

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Loaded {len(data.get('data', {}))} summoner spells from Data Dragon")
                    return data
                else:
                    logger.error(f"Failed to fetch summoner spell data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch summoner spell data: {e}")
            return None

    async def get_item_data(self) -> Optional[Dict]:
        """
        Get item data from Data Dragon for build tracking
        Returns: {item_id: {name, gold, stats, ...}}
        """
        url = "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/item.json"

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Loaded {len(data.get('data', {}))} items from Data Dragon")
                    return data
                else:
                    logger.error(f"Failed to fetch item data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch item data: {e}")
            return None
