"""
Import daily K-line data from CSV files back into kline_data.

Input: data/kline-d/{symbol}-{start_date}-{end_date}.csv
CSV must match export_kline.py output: date,open,high,low,close,volume,amount,source

Usage:
    python scripts/import_kline.py                         # import all CSVs
    python scripts/import_kline.py --dry-run                # count rows without inserting
    python scripts/import_kline.py data/kline-d/SH.6005*.csv
"""

import argparse
import asyncio
import logging
import re
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
logger = logging.getLogger("import_kline")

UPSERT = """INSERT INTO kline_data
             (symbol, date, open, high, low, close, volume, amount, source)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
             ON CONFLICT (symbol, date) DO UPDATE SET
                 open=EXCLUDED.open, high=EXCLUDED.high,
                 low=EXCLUDED.low, close=EXCLUDED.close,
                 volume=EXCLUDED.volume, amount=EXCLUDED.amount,
                 source=EXCLUDED.source"""

FILENAME_RE = re.compile(r"^([A-Z]{2}\.\d{6})-\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}\.csv$")


def parse_symbol_from_name(name: str) -> str | None:
    m = FILENAME_RE.match(name)
    return m.group(1) if m else None


async def import_file(
    pool: asyncpg.Pool, filepath: Path, *, dry_run: bool
) -> int:
    name = filepath.name
    symbol = parse_symbol_from_name(name)
    if not symbol:
        logger.warning("  skipping %s: cannot parse symbol from filename", name)
        return 0

    df = pd.read_csv(filepath)
    required = {"date", "open", "high", "low", "close", "volume", "amount", "source"}
    missing = required - set(df.columns)
    if missing:
        logger.warning(
            "  skipping %s: missing columns %s", name, sorted(missing)
        )
        return 0

    rows: list[tuple] = []
    for _, row in df.iterrows():
        rows.append((
            symbol,
            row["date"],
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            int(row["volume"]) if pd.notna(row["volume"]) else None,
            row["amount"],
            row["source"],
        ))

    if dry_run:
        logger.info(
            "  %s: %d rows (dry run, skipped)", name, len(rows)
        )
        return len(rows)

    async with pool.acquire() as conn:
        await conn.executemany(UPSERT, rows)

    logger.info("  %s: %d rows upserted", name, len(rows))
    return len(rows)


def collect_files(patterns: list[str]) -> list[Path]:
    if not patterns:
        return sorted(Path(_project_root / "data" / "kline-d").glob("*.csv"))
    files: list[Path] = []
    for p in patterns:
        pp = Path(p)
        if pp.is_absolute():
            files.extend(sorted(pp.parent.glob(pp.name)))
        else:
            files.extend(sorted(Path(_project_root).glob(p)))
    return sorted(set(files))


async def main():
    parser = argparse.ArgumentParser(description="Import kline CSV to database")
    parser.add_argument("files", nargs="*", help="CSV file(s) or glob patterns")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count rows without inserting",
    )
    args = parser.parse_args()

    files = collect_files(args.files)
    if not files:
        logger.warning("no CSV files found")
        return

    logger.info(
        "found %d file(s), dry_run=%s", len(files), args.dry_run
    )

    pool = await asyncpg.create_pool(
        dsn=settings.db_dsn,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
    )

    total_rows = 0
    total_files = 0
    try:
        for fp in files:
            n = await import_file(pool, fp, dry_run=args.dry_run)
            if n:
                total_files += 1
                total_rows += n
    finally:
        await pool.close()

    action = "would upsert" if args.dry_run else "upserted"
    logger.info("done: %d files, %d rows %s", total_files, total_rows, action)


if __name__ == "__main__":
    asyncio.run(main())
