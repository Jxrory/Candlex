"""
Import TDX financial data from mootdx .zip/.dat files into 6 flat tables.

Usage:
    python scripts/ingest_financial.py --period=20260331
    python scripts/ingest_financial.py --file=/abs/path/gpcw20260331.zip
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path for direct invocation
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncpg
import pandas as pd
from mootdx.financial import financial

from app.config import settings
from app.financial_v2_mapping import TABLE_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ingest_financial")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "affair"


def _code_to_symbol(code: object) -> str | None:
    """Convert mootdx 6-digit code to SH/SZ/BJ.xxxxxx format."""
    s = str(code).strip().zfill(6)
    if not s.isdigit() or len(s) != 6:
        return None
    c = s[0]
    if c == "6":
        return f"SH.{s}"
    elif c in ("0", "3"):
        return f"SZ.{s}"
    elif c in ("8", "4"):
        return f"BJ.{s}"
    return None


def _safe_val(v: object) -> object:
    """Convert a mootdx value for PG insertion. NaN->None, numpy->native."""
    if v is None:
        return None
    if isinstance(v, float):
        if pd.isna(v) or pd.isnull(v):
            return None
        if pd.isinf(v):
            return None
        return v
    if hasattr(v, "item"):
        return v.item()
    return v


def _split_row(row: pd.Series) -> dict[str, dict[str, object]]:
    """
    Split one mootdx row into 6 table dicts.

    Returns {table_name: {english_col: value, ...}}
    """
    result: dict[str, dict[str, object]] = {}
    for table_name, cols in TABLE_COLUMNS.items():
        table_data: dict[str, object] = {}
        for col_def in cols:
            if col_def.chinese_name in row.index:
                v = _safe_val(row[col_def.chinese_name])
                if v is not None:
                    table_data[col_def.english_name] = v
        if table_data:
            result[table_name] = table_data
    return result


async def _upsert_table(
    conn, table_name: str, symbol: str, report_date, data: dict
) -> None:
    if not data:
        return
    cols = ["symbol", "report_date"] + list(data.keys()) + ["source"]
    placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
    column_names = ", ".join(cols)

    updates = ", ".join(
        f"{k} = EXCLUDED.{k}" for k in data.keys()
    )
    updates += ", updated_at = NOW()"

    values = [symbol, report_date] + list(data.values()) + ["mootdx"]

    sql = f"""INSERT INTO {table_name} ({column_names})
              VALUES ({placeholders})
              ON CONFLICT (symbol, report_date) DO UPDATE SET {updates}"""
    await conn.execute(sql, *values)


async def ingest(
    pool: asyncpg.Pool,
    file_path: str,
) -> dict[str, int]:
    logger.info("reading %s", file_path)
    df = financial.FinancialReader().to_data(file_path)
    logger.info("read %d rows, %d columns", len(df), len(df.columns))

    total_by_table: dict[str, int] = {}
    inserted = 0
    skip_reason: dict[str, int] = {"bad_code": 0, "no_data": 0}

    async with pool.acquire() as conn:
        for code, row in df.iterrows():
            symbol = _code_to_symbol(code)
            if symbol is None:
                skip_reason["bad_code"] += 1
                continue

            rd_raw = row.get("report_date")
            if rd_raw is None or pd.isna(rd_raw):
                skip_reason["no_data"] += 1
                continue
            rd = pd.to_datetime(str(int(rd_raw)), format="%Y%m%d").date()

            table_dicts = _split_row(row)
            if not table_dicts:
                skip_reason["no_data"] += 1
                continue

            for table_name, data in table_dicts.items():
                await _upsert_table(conn, table_name, symbol, rd, data)
                total_by_table[table_name] = total_by_table.get(table_name, 0) + 1

            inserted += 1

    logger.info("inserted %d stocks", inserted)
    for table_name, count in sorted(total_by_table.items()):
        logger.info("  %s: %d rows", table_name, count)
    for reason, count in skip_reason.items():
        if count:
            logger.warning("  skipped %d: %s", count, reason)
    return total_by_table


async def main():
    parser = argparse.ArgumentParser(description="Import TDX financial data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--period", help="Report period, e.g. 20260331")
    group.add_argument("--file", help="Full path to .zip/.dat file")
    args = parser.parse_args()

    if args.period:
        file_path = str(DATA_DIR / f"gpcw{args.period}.zip")
    else:
        file_path = args.file

    if not Path(file_path).exists():
        logger.error("file not found: %s", file_path)
        sys.exit(1)

    pool = await asyncpg.create_pool(
        dsn=settings.db_dsn,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
    )
    try:
        await ingest(pool, file_path)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
