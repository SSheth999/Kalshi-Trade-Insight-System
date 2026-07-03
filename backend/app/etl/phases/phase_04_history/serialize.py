from app.etl.phases.phase_04_history.models import CandlestickSnapshot


def candlestick_to_snapshot(candlestick) -> CandlestickSnapshot:
    price = candlestick.price
    return CandlestickSnapshot(
        end_period_ts=candlestick.end_period_ts,
        open_dollars=price.open_dollars,
        high_dollars=price.high_dollars,
        low_dollars=price.low_dollars,
        close_dollars=price.close_dollars,
        volume_fp=candlestick.volume_fp,
        open_interest_fp=candlestick.open_interest_fp,
    )
