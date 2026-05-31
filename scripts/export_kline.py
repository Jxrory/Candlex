"""
Export all daily K-line data from kline_data to CSV files.

Output: data/kline-d/{symbol}-{start_date}-{end_date}.csv
One file per symbol, sorted by date ascending.

Usage:
    python scripts/export_kline.py
    python scripts/export_kline.py --symbol SH.600519
    python scripts/export_kline.py --limit 10
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncpg
import pandas as pd

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("export_kline")

OUTPUT_DIR = Path(_project_root) / "data" / "kline-d"


async def export_symbol(
    conn: asyncpg.Connection, symbol: str, output_dir: Path
) -> int:
    rows = await conn.fetch(
        """SELECT date, open, high, low, close, volume, amount, source
           FROM kline_data
           WHERE symbol = $1
           ORDER BY date""",
        symbol,
    )
    if not rows:
        logger.info("  %s: no data", symbol)
        return 0

    start = rows[0]["date"]
    end = rows[-1]["date"]
    filepath = output_dir / f"{symbol}-{start}-{end}.csv"

    df = pd.DataFrame.from_records(rows, columns=[
        "date", "open", "high", "low", "close", "volume", "amount", "source",
    ])
    df.to_csv(filepath, index=False, float_format="%.3f")

    logger.info("  %s: %d rows -> %s", symbol, len(rows), filepath.name)
    return len(rows)


async def main():
    parser = argparse.ArgumentParser(description="Export kline data to CSV")
    parser.add_argument("--symbol", help="Export only this symbol (e.g. SH.600519)")
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max number of symbols to export (0 = all)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pool = await asyncpg.create_pool(
        dsn=settings.db_dsn,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
    )

    try:
        if args.symbol:
            total_rows = 0
            async with pool.acquire() as conn:
                total_rows += await export_symbol(conn, args.symbol, OUTPUT_DIR)
            logger.info("done: 1 symbol, %d total rows", total_rows)
            return

        if args.limit:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT DISTINCT symbol FROM kline_data ORDER BY symbol LIMIT $1",
                    args.limit,
                )
            symbols = [r["symbol"] for r in rows]
            logger.info("exporting %d symbols to %s", len(symbols), OUTPUT_DIR)
            total_rows = 0
            for symbol in symbols:
                async with pool.acquire() as conn:
                    total_rows += await export_symbol(conn, symbol, OUTPUT_DIR)
            logger.info("done: %d symbols, %d total rows", len(symbols), total_rows)
            return

        logger.info("exporting all symbols to %s", OUTPUT_DIR)
        total_symbols = 0
        total_rows = 0
        async with pool.acquire() as conn:
            async with conn.transaction():
                async for row in conn.cursor(
                    "SELECT DISTINCT symbol FROM kline_data ORDER BY symbol",
                    prefetch=200,
                ):
                    symbol = row["symbol"]
                    total_symbols += 1
                    total_rows += await export_symbol(conn, symbol, OUTPUT_DIR)
        logger.info("done: %d symbols, %d total rows", total_symbols, total_rows)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
