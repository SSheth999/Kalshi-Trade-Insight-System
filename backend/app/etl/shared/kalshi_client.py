from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from kalshi_python_async import Configuration, KalshiClient

from app.etl.config import settings


def _load_private_key_pem() -> str | None:
    if not settings.kalshi_private_key_path:
        return None
    return Path(settings.kalshi_private_key_path).read_text()


@asynccontextmanager
async def kalshi_client() -> AsyncIterator[KalshiClient]:
    config = Configuration(host=settings.kalshi_base_url)
    if settings.kalshi_api_key_id:
        private_key_pem = _load_private_key_pem()
        if private_key_pem:
            config.api_key_id = settings.kalshi_api_key_id
            config.private_key_pem = private_key_pem
    client = KalshiClient(config)
    try:
        yield client
    finally:
        await client.close()
