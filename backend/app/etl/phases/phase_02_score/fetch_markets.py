import asyncio

from kalshi_python_async import KalshiClient

from app.etl.shared.retry import with_retry


async def fetch_open_markets_for_series(
    client: KalshiClient,
    series_ticker: str,
) -> list:
    """Paginate GET /markets until cursor is empty."""
    markets: list = []
    cursor: str | None = None

    while True:
        response = await with_retry(
            lambda c=cursor: client.get_markets(
                series_ticker=series_ticker,
                status="open",
                limit=1000,
                mve_filter="exclude",
                cursor=c,
            )
        )
        markets.extend(response.markets)
        if not response.cursor:
            break
        cursor = response.cursor
        await asyncio.sleep(0.1)

    return markets
