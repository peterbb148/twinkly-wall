"""Quote datasource using ZenQuotes API."""

import logging
import random
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

# Fallback quotes (famous scientists/philosophers) if API fails
FALLBACK_QUOTES = [
    ("The important thing is not to stop questioning.", "Albert Einstein"),
    ("Science is organized knowledge.", "Herbert Spencer"),
    ("Nothing in life is to be feared.", "Marie Curie"),
    ("I think, therefore I am.", "René Descartes"),
    ("Knowledge is power.", "Francis Bacon"),
    ("The only true wisdom is knowing you know nothing.", "Socrates"),
    ("Imagination is more important than knowledge.", "Albert Einstein"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("Science is a way of thinking.", "Carl Sagan"),
    ("The good life is guided by reason.", "Bertrand Russell"),
]


@dataclass
class QuoteData:
    """Quote data."""

    quote: str
    author: str
    timestamp: float  # Unix timestamp when fetched


class QuoteError(Exception):
    """Error fetching quote data."""

    pass


class QuoteDataSource:
    """Fetch quotes from ZenQuotes API.

    ZenQuotes is free and doesn't require an API key.
    https://zenquotes.io/
    """

    BASE_URL = "https://zenquotes.io/api"

    def __init__(
        self,
        cache_duration: int = 3600,  # 1 hour
        timeout: float = 10.0,
    ):
        """Initialize quote datasource.

        Args:
            cache_duration: How long to cache results in seconds
            timeout: Request timeout in seconds
        """
        self.cache_duration = cache_duration
        self.timeout = timeout
        self._cache: QuoteData | None = None
        self._cache_time: float = 0

    def _fetch(self) -> QuoteData:
        """Fetch a random quote from API."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/random",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise QuoteError(f"Failed to fetch quote: {e}") from e

        if not data or len(data) == 0:
            raise QuoteError("Empty response from API")

        quote_data = data[0]
        quote = quote_data.get("q", "")
        author = quote_data.get("a", "Unknown")

        if not quote:
            raise QuoteError("No quote in response")

        return QuoteData(
            quote=quote,
            author=author,
            timestamp=time.time(),
        )

    def get_quote(self) -> QuoteData:
        """Get a quote, using cache if available.

        Returns:
            QuoteData object with quote and author
        """
        now = time.time()

        # Return cached data if still valid
        if self._cache and (now - self._cache_time) < self.cache_duration:
            return self._cache

        # Fetch fresh data
        try:
            self._cache = self._fetch()
            self._cache_time = now
            logger.info(f"Quote updated: {self._cache.author}")
        except QuoteError as e:
            logger.warning(f"Quote fetch failed: {e}")
            # Return stale cache if available
            if self._cache:
                return self._cache
            # Fall back to local quotes
            quote, author = random.choice(FALLBACK_QUOTES)
            return QuoteData(quote=quote, author=author, timestamp=now)

        return self._cache

    def get_today_quote(self) -> QuoteData:
        """Get today's quote (cached for the day).

        Returns:
            QuoteData object with quote and author
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/today",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                quote_data = data[0]
                return QuoteData(
                    quote=quote_data.get("q", ""),
                    author=quote_data.get("a", "Unknown"),
                    timestamp=time.time(),
                )
        except requests.exceptions.RequestException as e:
            logger.warning(f"Today's quote fetch failed: {e}")

        # Fall back to random quote
        return self.get_quote()
