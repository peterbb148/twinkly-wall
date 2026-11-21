"""Danish Superliga standings datasource using TheSportsDB API."""

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

# TheSportsDB free API
API_BASE_URL = "https://www.thesportsdb.com/api/v1/json/3"
DANISH_SUPERLIGA_ID = "4340"


@dataclass
class TeamStanding:
    """Single team's standing in the league."""

    rank: int
    team_id: str
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: str  # e.g., "WWDLW"


@dataclass
class SuperligaData:
    """Danish Superliga standings data."""

    season: str
    standings: list[TeamStanding]
    timestamp: float


class SuperligaError(Exception):
    """Error fetching Superliga data."""

    pass


class SuperligaDataSource:
    """Fetch Danish Superliga standings from TheSportsDB API."""

    def __init__(
        self,
        season: str | None = None,
        cache_duration: int = 1800,  # 30 minutes
        timeout: float = 10.0,
    ):
        """Initialize Superliga datasource.

        Args:
            season: Season string (e.g., "2024-2025"). If None, uses current season.
            cache_duration: How long to cache results in seconds.
            timeout: Request timeout in seconds.
        """
        self.season = season
        self.cache_duration = cache_duration
        self.timeout = timeout
        self._cache: SuperligaData | None = None
        self._cache_time: float = 0

    def _get_current_season(self) -> str:
        """Determine current season based on current date."""
        now = time.localtime()
        year = now.tm_year
        month = now.tm_mon
        # Season runs Aug-May, so after July we're in new season
        if month >= 7:
            return f"{year}-{year + 1}"
        else:
            return f"{year - 1}-{year}"

    def _fetch(self) -> SuperligaData:
        """Fetch standings from API."""
        season = self.season or self._get_current_season()
        url = f"{API_BASE_URL}/lookuptable.php"
        params = {
            "l": DANISH_SUPERLIGA_ID,
            "s": season,
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise SuperligaError(f"Failed to fetch Superliga standings: {e}") from e

        table = data.get("table")
        if not table:
            raise SuperligaError("No standings data available")

        standings = []
        for entry in table:
            standings.append(
                TeamStanding(
                    rank=int(entry.get("intRank", 0)),
                    team_id=entry.get("idTeam", ""),
                    team_name=entry.get("strTeam", "Unknown"),
                    played=int(entry.get("intPlayed", 0)),
                    wins=int(entry.get("intWin", 0)),
                    draws=int(entry.get("intDraw", 0)),
                    losses=int(entry.get("intLoss", 0)),
                    goals_for=int(entry.get("intGoalsFor", 0)),
                    goals_against=int(entry.get("intGoalsAgainst", 0)),
                    goal_difference=int(entry.get("intGoalDifference", 0)),
                    points=int(entry.get("intPoints", 0)),
                    form=entry.get("strForm", ""),
                )
            )

        return SuperligaData(
            season=season,
            standings=standings,
            timestamp=time.time(),
        )

    def get_standings(self) -> SuperligaData:
        """Get current standings, using cache if available.

        Returns:
            SuperligaData with current standings.
        """
        now = time.time()

        # Return cached data if still valid
        if self._cache and (now - self._cache_time) < self.cache_duration:
            return self._cache

        # Fetch fresh data
        try:
            self._cache = self._fetch()
            self._cache_time = now
            logger.info(f"Superliga standings updated: {len(self._cache.standings)} teams")
        except SuperligaError as e:
            logger.warning(f"Superliga fetch failed: {e}")
            # Return stale cache if available
            if self._cache:
                return self._cache
            raise

        return self._cache

    def get_top_teams(self, count: int = 6) -> list[TeamStanding]:
        """Get top N teams in the standings."""
        standings = self.get_standings()
        return standings.standings[:count]
