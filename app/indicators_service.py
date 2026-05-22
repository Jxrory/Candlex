import json
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from app.service import get_kline
from app.tools.indicators import IndicatorSpec, SUPPORTED, compute_many

logger = logging.getLogger(__name__)

INDICATOR_PARAMS: dict[str, list[str]] = {
    "ma": ["n"],
    "ema": ["n"],
    "macd": ["fast", "slow", "signal"],
    "rsi": ["n"],
    "boll": ["n", "k"],
    "atr": ["n"],
    "kdj": ["n", "m1", "m2"],
}


def parse_specs(raw: list[str]) -> list[IndicatorSpec]:
    specs: list[IndicatorSpec] = []
    for val in raw:
        val = val.strip()
        if not val:
            continue
        if val.startswith("["):
            parsed = json.loads(val)
            for item in parsed:
                name = item["name"].lower()
                if name not in SUPPORTED:
                    raise ValueError(f"unsupported indicator: {name}")
                specs.append(IndicatorSpec(name, item.get("params")))
        else:
            parts = val.split(":")
            name = parts[0].lower()
            if name not in SUPPORTED:
                raise ValueError(f"unsupported indicator: {name}")
            params = None
            if len(parts) > 1 and parts[1]:
                raw_params = parts[1].split(",")
                param_names = INDICATOR_PARAMS.get(name, [])
                params = {}
                for i, p in enumerate(raw_params):
                    p = p.strip()
                    if i < len(param_names):
                        key = param_names[i]
                        try:
                            params[key] = int(p) if "." not in p else float(p)
                        except ValueError:
                            params[key] = p
            specs.append(IndicatorSpec(name, params if params else None))

    seen: set[tuple] = set()
    deduped: list[IndicatorSpec] = []
    for s in specs:
        items = tuple(sorted((s.params or {}).items()))
        key = (s.name, items)
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped


async def get_indicators(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
    specs: list[IndicatorSpec] | None = None,
) -> list[dict[str, Any]]:
    records = await get_kline(symbol, start, end, adjust)
    if not records:
        return []
    df = pd.DataFrame([r.model_dump() for r in records])
    if specs:
        df = compute_many(df, specs)
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")
