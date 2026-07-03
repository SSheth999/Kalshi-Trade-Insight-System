from pydantic_settings import BaseSettings, SettingsConfigDict


class EtlSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kalshi_base_url: str = "https://external-api.kalshi.com/trade-api/v2"
    kalshi_api_key_id: str | None = None
    kalshi_private_key_path: str | None = None
    min_series_volume: float = 1000.0
    max_series_to_score: int = 200
    top_volatile_series: int = 10
    score_concurrency: int = 3
    lookback_days: int = 30
    period_interval: int = 60
    max_markets_per_series: int = 50
    candlestick_concurrency: int = 2
    include_latest_before_start: bool = True
    data_dir: str = "data"


settings = EtlSettings()
