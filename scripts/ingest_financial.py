"""
Import TDX financial data from mootdx .zip/.dat files into 6 flat tables.

Usage:
    python scripts/ingest_financial.py --period=20260331
    python scripts/ingest_financial.py --file=/abs/path/gpcw20260331.zip
    python scripts/ingest_financial.py --all
"""

import argparse
import asyncio
import asyncpg
import logging
import math
import sys
import zipfile
from datetime import date
from pathlib import Path

# Ensure project root is on sys.path for direct invocation
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

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

# Precomputed map: chinese_name -> (english_name, pg_type, table_name)
_COL_MAP = {
    col.chinese_name: (col.english_name, col.pg_type, table_name)
    for table_name, cols in TABLE_COLUMNS.items()
    for col in cols
}


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
    elif c in ("8", "4", "9"):
        return f"BJ.{s}"
    return None


def _safe_val(v: object, pg_type: str = "NUMERIC") -> object:
    """Convert a mootdx value for PG insertion. NaN/None->None, numpy->native."""
    if v is None:
        return None
    # pandas Series from duplicate column names — take first value
    if hasattr(v, "iloc"):
        v = v.iloc[0] if len(v) > 0 else None
        if v is None or pd.isna(v):
            return None
    # numpy scalar → native Python
    if hasattr(v, "item"):
        try:
            v = v.item()
        except (ValueError, IndexError):
            return None
    # TEXT columns: always convert to string (YYMMDD codes come as float)
    if pg_type.upper().startswith("TEXT"):
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return None
            return str(int(v)) if v == int(v) else str(v)
        return str(v)
    # NUMERIC columns
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, (int, str, bool)):
        return v
    return None if pd.isna(v) else v


def _split_row(row: pd.Series) -> dict[str, dict[str, object]]:
    """Split one mootdx row into 6 table dicts.
    
    Iterates over actual values in the row (not all 399 col_defs),
    using a precomputed map for O(1) column resolution.
    """
    result: dict[str, dict[str, object]] = {}
    for cn_name, v in row.items():
        info = _COL_MAP.get(cn_name)
        if info is None:
            continue
        en_name, pg_type, table_name = info
        v = _safe_val(v, pg_type)
        if v is not None:
            result.setdefault(table_name, {})[en_name] = v
    return result


async def _batch_upsert(
    conn, table_name: str, rows: list[tuple[str, date, dict]], chunk_size: int = 200
) -> int:
    """Batch upsert all rows for one table using multi-row INSERT ON CONFLICT."""

    all_cols: set[str] = set()
    for _, _, data in rows:
        all_cols.update(data.keys())
    col_list = sorted(all_cols)
    if not col_list:
        return 0

    total = 0
    for offset in range(0, len(rows), chunk_size):
        chunk = rows[offset : offset + chunk_size]
        values: list[object] = []
        row_placeholders: list[str] = []
        idx = 1

        for symbol, rd, data in chunk:
            row_vals = [symbol, rd]
            for c in col_list:
                v = data.get(c)
                row_vals.append(v if v is not None else None)
            row_vals.append("mootdx")
            placeholders = ", ".join(f"${i}" for i in range(idx, idx + len(row_vals)))
            row_placeholders.append(f"({placeholders})")
            values.extend(row_vals)
            idx += len(row_vals)

        full_cols = ["symbol", "report_date"] + col_list + ["source"]
        columns = ", ".join(full_cols)
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in col_list)
        updates += ", updated_at = NOW()"

        sql = f"""INSERT INTO {table_name} ({columns})
                  VALUES {', '.join(row_placeholders)}
                  ON CONFLICT (symbol, report_date) DO UPDATE SET {updates}"""
        await conn.execute(sql, *values)
        total += len(chunk)

    return total


async def ingest(
    pool: asyncpg.Pool,
    file_path: str,
) -> int:
    logger.info("reading %s", file_path)
    df = financial.FinancialReader().to_data(file_path)
    logger.info("read %d rows, %d columns", len(df), len(df.columns))

    table_buckets: dict[str, dict[tuple[str, date], dict]] = {}
    bad_code = no_data = dup = 0

    for code, row in df.iterrows():
        symbol = _code_to_symbol(code)
        if symbol is None:
            bad_code += 1
            continue

        rd_raw = row.get("report_date")
        if rd_raw is None or pd.isna(rd_raw):
            no_data += 1
            continue
        rd = pd.to_datetime(str(int(rd_raw)), format="%Y%m%d").date()

        table_dicts = _split_row(row)
        if not table_dicts:
            no_data += 1
            continue

        for table_name, data in table_dicts.items():
            key = (symbol, rd)
            bucket = table_buckets.setdefault(table_name, {})
            if key in bucket:
                dup += 1
            bucket[key] = data

    total = 0
    async with pool.acquire() as conn:
        for table_name in sorted(table_buckets):
            bucket = list(table_buckets[table_name].items())
            bucket_list = [(sym, rd, data) for (sym, rd), data in bucket]
            count = await _batch_upsert(conn, table_name, bucket_list)
            logger.info("  %s: %d rows", table_name, count)
            total = count

    logger.info("inserted %d stocks", total)
    if bad_code:
        logger.warning("  skipped %d: bad_code", bad_code)
    if no_data:
        logger.warning("  skipped %d: no_data", no_data)
    if dup:
        logger.warning("  deduped %d duplicate rows", dup)
    return total


async def import_all(pool: asyncpg.Pool) -> None:
    """Import all gpcw*.zip files from DATA_DIR in order."""
    files = sorted(DATA_DIR.glob("gpcw*.zip"))
    logger.info("found %d files to import", len(files))
    for fp in files:
        t0 = asyncio.get_event_loop().time()
        await ingest(pool, str(fp))
        elapsed = asyncio.get_event_loop().time() - t0
        logger.info("  done in %.1fs\n", elapsed)


async def main():
    parser = argparse.ArgumentParser(description="Import TDX financial data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--period", help="Report period, e.g. 20260331")
    group.add_argument("--file", help="Full path to .zip/.dat file")
    group.add_argument("--all", action="store_true", help="Import all gpcw*.zip files")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(
        dsn=settings.db_dsn,
        min_size=settings.db_min_connections,
        max_size=settings.db_max_connections,
    )
    try:
        if args.all:
            await import_all(pool)
        elif args.period:
            file_path = str(DATA_DIR / f"gpcw{args.period}.zip")
            if not Path(file_path).exists():
                logger.error("file not found: %s", file_path)
                sys.exit(1)
            await ingest(pool, file_path)
        else:
            if not Path(args.file).exists():
                logger.error("file not found: %s", args.file)
                sys.exit(1)
            await ingest(pool, args.file)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
