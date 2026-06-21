"""Re-export ETL settings for app-wide use (e.g. FastAPI)."""

from app.etl.config import EtlSettings, settings

__all__ = ["EtlSettings", "settings"]
