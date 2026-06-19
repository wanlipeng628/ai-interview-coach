from collections.abc import Generator

from redis import Redis

from app.shared.config import settings


def create_redis_client() -> Redis:
    """Create a Redis client.

    The client is created lazily and does not perform network I/O until used.
    """
    return Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis_client() -> Generator[Redis, None, None]:
    """FastAPI dependency for Redis access."""
    client = create_redis_client()
    try:
        yield client
    finally:
        client.close()
