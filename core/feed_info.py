import threading
import time

from common.logger import get_logger

logger = get_logger(__name__)

# Miniflux's webhook payload carries a reduced feed object (id, title, feed_url, site_url, checked_at): no category,
# no hide_globally. The filters need both, so the full feed is fetched from the API and cached for a while.
CACHE_SECONDS = 600

_cache = {}
_lock = threading.Lock()


def full_feed(miniflux_client, feed, cache_seconds=CACHE_SECONDS):
    """The webhook's feed object completed with the fields the API returns (category, hide_globally, …).
    Falls back to the object as given when the lookup fails."""
    feed = feed or {}
    feed_id = feed.get('id')
    if feed_id is None:
        return feed
    now = time.time()
    with _lock:
        cached = _cache.get(feed_id)
        if cached and now - cached[0] < cache_seconds:
            return {**feed, **cached[1]}
    try:
        fetched = miniflux_client.get_feed(feed_id) or {}
    except Exception as exc:
        logger.warning('Could not fetch feed %s from Miniflux, using the webhook feed object: %s', feed_id, exc)
        return feed
    with _lock:
        _cache[feed_id] = (now, fetched)
    return {**feed, **fetched}


def clear_cache():
    with _lock:
        _cache.clear()
