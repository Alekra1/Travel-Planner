import httpx
from cachetools import TTLCache

BASE_URL = "https://api.artic.edu/api/v1"

_cache: TTLCache[int, dict] = TTLCache(maxsize=1024, ttl=86400)


class ArticNotFound(Exception):
    """Raised when the requested artwork id does not exist in the Art Institute API."""


class ArticUpstreamError(Exception):
    """Raised when the Art Institute API returns a server error or is unreachable."""


async def fetch_artwork(artwork_id: int) -> dict:
    """Fetch an artwork by its Art Institute id, with in-process TTL-LRU caching.

    Returns: {"external_id": int, "title": str}
    Raises:  ArticNotFound (404), ArticUpstreamError (5xx / network).
    """
    if artwork_id in _cache:
        return _cache[artwork_id]

    url = f"{BASE_URL}/artworks/{artwork_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, params={"fields": "id,title"})
    except httpx.RequestError as e:
        raise ArticUpstreamError(f"Could not reach Art Institute API: {e}") from e

    if response.status_code == 404:
        raise ArticNotFound(f"Artwork {artwork_id} not found in Art Institute API")
    if response.status_code >= 500:
        raise ArticUpstreamError(f"Art Institute API error ({response.status_code})")
    response.raise_for_status()

    data = response.json()["data"]
    result = {"external_id": data["id"], "title": data["title"]}
    _cache[artwork_id] = result
    return result
