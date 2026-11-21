"""RSS feed datasource."""

import logging
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html import unescape

import requests

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """Single item from RSS feed."""

    title: str
    description: str = ""
    link: str = ""
    pub_date: str = ""


@dataclass
class FeedData:
    """RSS feed data."""

    title: str
    items: list[FeedItem] = field(default_factory=list)
    timestamp: float = 0.0  # Unix timestamp when fetched


class RSSError(Exception):
    """Error fetching RSS feed."""

    pass


def _clean_text(text: str | None) -> str:
    """Clean text from RSS feed."""
    if not text:
        return ""
    # Unescape HTML entities
    text = unescape(text)
    # Remove extra whitespace
    text = " ".join(text.split())
    return text


def _get_text(
    element: ET.Element | None, tag: str, namespaces: dict[str, str] | None = None
) -> str:
    """Get text from an XML element."""
    if element is None:
        return ""
    child = element.find(tag, namespaces)
    if child is not None and child.text:
        return _clean_text(child.text)
    return ""


class RSSDataSource:
    """Fetch and parse RSS feeds.

    Supports standard RSS 2.0 and Atom feeds.
    """

    def __init__(
        self,
        feed_url: str,
        cache_duration: int = 300,  # 5 minutes
        timeout: float = 10.0,
        max_items: int = 10,
    ):
        """Initialize RSS datasource.

        Args:
            feed_url: URL of the RSS feed
            cache_duration: How long to cache results in seconds
            timeout: Request timeout in seconds
            max_items: Maximum number of items to keep
        """
        self.feed_url = feed_url
        self.cache_duration = cache_duration
        self.timeout = timeout
        self.max_items = max_items
        self._cache: FeedData | None = None
        self._cache_time: float = 0

    def _parse_rss(self, root: ET.Element) -> FeedData:
        """Parse RSS 2.0 format."""
        channel = root.find("channel")
        if channel is None:
            raise RSSError("No channel element found")

        feed_title = _get_text(channel, "title")
        items: list[FeedItem] = []

        for item_elem in channel.findall("item")[: self.max_items]:
            items.append(
                FeedItem(
                    title=_get_text(item_elem, "title"),
                    description=_get_text(item_elem, "description"),
                    link=_get_text(item_elem, "link"),
                    pub_date=_get_text(item_elem, "pubDate"),
                )
            )

        return FeedData(title=feed_title, items=items, timestamp=time.time())

    def _parse_atom(self, root: ET.Element) -> FeedData:
        """Parse Atom format."""
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        feed_title = _get_text(root, "atom:title", ns)
        items: list[FeedItem] = []

        for entry in root.findall("atom:entry", ns)[: self.max_items]:
            # Get link - Atom uses href attribute
            link = ""
            link_elem = entry.find("atom:link", ns)
            if link_elem is not None:
                link = link_elem.get("href", "")

            items.append(
                FeedItem(
                    title=_get_text(entry, "atom:title", ns),
                    description=_get_text(entry, "atom:summary", ns)
                    or _get_text(entry, "atom:content", ns),
                    link=link,
                    pub_date=_get_text(entry, "atom:updated", ns)
                    or _get_text(entry, "atom:published", ns),
                )
            )

        return FeedData(title=feed_title, items=items, timestamp=time.time())

    def _fetch(self) -> FeedData:
        """Fetch and parse the RSS feed."""
        try:
            response = requests.get(
                self.feed_url,
                timeout=self.timeout,
                headers={"User-Agent": "TwinklyWall/1.0"},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RSSError(f"Failed to fetch feed: {e}") from e

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            raise RSSError(f"Failed to parse feed: {e}") from e

        # Determine feed type
        if root.tag == "rss":
            return self._parse_rss(root)
        elif root.tag == "{http://www.w3.org/2005/Atom}feed":
            return self._parse_atom(root)
        else:
            # Try RSS anyway
            channel = root.find("channel")
            if channel is not None:
                return self._parse_rss(root)
            raise RSSError(f"Unknown feed format: {root.tag}")

    def get_feed(self) -> FeedData:
        """Get the RSS feed, using cache if available.

        Returns:
            FeedData object with feed title and items
        """
        now = time.time()

        # Return cached data if still valid
        if self._cache and (now - self._cache_time) < self.cache_duration:
            return self._cache

        # Fetch fresh data
        try:
            self._cache = self._fetch()
            self._cache_time = now
            logger.info(f"RSS updated: {self._cache.title}, {len(self._cache.items)} items")
        except RSSError as e:
            logger.warning(f"RSS fetch failed: {e}")
            # Return stale cache if available
            if self._cache:
                return self._cache
            raise

        return self._cache

    def get_headlines(self) -> list[str]:
        """Get list of headline titles.

        Returns:
            List of headline strings
        """
        feed = self.get_feed()
        return [item.title for item in feed.items if item.title]
