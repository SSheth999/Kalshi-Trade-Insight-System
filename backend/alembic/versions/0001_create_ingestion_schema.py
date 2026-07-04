"""create ingestion schema

Revision ID: 0001_create_ingestion_schema
Revises:
Create Date: 2026-07-03
"""

from alembic import op

revision = "0001_create_ingestion_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("create extension if not exists pgcrypto")
    op.execute("create extension if not exists vector")

    op.execute(
        """
        create table if not exists ingestion_runs (
            id uuid primary key default gen_random_uuid(),
            started_at timestamptz not null default now(),
            completed_at timestamptz,
            through int not null,
            duration_seconds double precision,
            params jsonb not null default '{}'::jsonb,
            status text not null default 'completed',
            created_at timestamptz not null default now()
        )
        """
    )

    op.execute(
        """
        create table if not exists series (
            ticker text primary key,
            title text not null,
            category text,
            frequency text,
            tags text[] not null default '{}',
            lifetime_volume double precision,
            last_updated_ts timestamptz,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

    op.execute(
        """
        create table if not exists markets (
            ticker text primary key,
            series_ticker text not null references series(ticker) on delete cascade,
            event_ticker text,
            title text,
            status text,
            yes_bid_dollars numeric,
            yes_ask_dollars numeric,
            last_price_dollars numeric,
            previous_price_dollars numeric,
            volume_24h_fp numeric,
            open_interest_fp numeric,
            close_time timestamptz,
            rules_primary text,
            rules_secondary text,
            raw_payload jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

    op.execute(
        """
        create table if not exists series_rankings (
            run_id uuid not null references ingestion_runs(id) on delete cascade,
            series_ticker text not null references series(ticker) on delete cascade,
            rank int not null,
            score double precision not null,
            avg_spread double precision,
            max_1d_move double precision,
            mean_1d_move double precision,
            total_vol24 double precision,
            open_market_count int,
            created_at timestamptz not null default now(),
            primary key (run_id, series_ticker)
        )
        """
    )

    op.execute(
        """
        create table if not exists candlesticks (
            market_ticker text not null references markets(ticker) on delete cascade,
            end_period_ts bigint not null,
            period_interval int not null,
            open_dollars numeric,
            high_dollars numeric,
            low_dollars numeric,
            close_dollars numeric,
            volume_fp numeric,
            open_interest_fp numeric,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now(),
            primary key (market_ticker, end_period_ts, period_interval)
        )
        """
    )

    op.execute(
        """
        create table if not exists market_embeddings (
            market_ticker text primary key references markets(ticker) on delete cascade,
            embedding vector(1536),
            source_text text,
            metadata jsonb not null default '{}'::jsonb,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
    )

    op.execute(
        "create index if not exists ix_markets_series_ticker on markets(series_ticker)"
    )
    op.execute(
        "create index if not exists ix_series_rankings_run_rank "
        "on series_rankings(run_id, rank)"
    )
    op.execute(
        "create index if not exists ix_candlesticks_market_time "
        "on candlesticks(market_ticker, end_period_ts desc)"
    )
    op.execute(
        "create index if not exists ix_market_embeddings_embedding_hnsw "
        "on market_embeddings using hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("drop index if exists ix_market_embeddings_embedding_hnsw")
    op.execute("drop index if exists ix_candlesticks_market_time")
    op.execute("drop index if exists ix_series_rankings_run_rank")
    op.execute("drop index if exists ix_markets_series_ticker")
    op.execute("drop table if exists market_embeddings")
    op.execute("drop table if exists candlesticks")
    op.execute("drop table if exists series_rankings")
    op.execute("drop table if exists markets")
    op.execute("drop table if exists series")
    op.execute("drop table if exists ingestion_runs")
