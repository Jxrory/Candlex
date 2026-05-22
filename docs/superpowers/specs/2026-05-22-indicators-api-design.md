# Indicators API Design

Add a standalone `/indicators/{symbol}` route that returns K-line data plus
computed technical indicators in a single time-series response.

## Route

```
GET /indicators/{symbol}?start=&end=&adjust=&i=ma:5&i=ma:10&i=macd
```

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `symbol` | path | yes | — | `^(SH\|SZ\|BJ)\.[0-9]{6}$` |
| `start` | query | no | 1 year ago | start date |
| `end` | query | no | today | end date |
| `adjust` | query | no | — | `qfq` / `hfq` |
| `i` | query | no | — | repeatable, see "Indicator Spec" |

## Indicator Spec (`i` param)

Two formats supported, `i` can be mixed:

1. **Shorthand** — `ma:5`, `ma:10,20` (colon-separated name and positional params)
2. **JSON** — URL-encoded JSON array of objects:
   `i=[{"name":"ma","params":{"n":5}}]`

When `i` is omitted → returns raw K-line only (same shape as `/kline` but as
dict list).

### Supported indicators

| Name | Default params | Positional | Output columns |
|------|---------------|------------|----------------|
| `ma` | `n=20` | `n` | `ma{n}` |
| `ema` | `n=20` | `n` | `ema{n}` |
| `macd` | `fast=12,slow=26,signal=9` | `fast,slow,signal` | `macd_dif`, `macd_dea`, `macd_hist` |
| `rsi` | `n=14` | `n` | `rsi{n}` |
| `boll` | `n=20,k=2` | `n,k` | `boll_mid`, `boll_upper`, `boll_lower` |
| `atr` | `n=14` | `n` | `atr{n}` |
| `kdj` | `n=9,m1=3,m2=3` | `n,m1,m2` | `kdj_k`, `kdj_d`, `kdj_j` |

## Response

```json
[
  {
    "date": "2024-01-02",
    "open": 105.0,
    "high": 106.5,
    "low": 104.5,
    "close": 105.8,
    "volume": 123456,
    "amount": 13000000.0,
    "ma5": 105.2,
    "ma10": 104.8,
    "macd_dif": 1.2,
    "macd_dea": 0.8,
    "macd_hist": 0.4
  }
]
```

`list[dict]` — each entry contains `date` + raw K-line columns + requested
indicator columns. NaN values serialize as `null`.

## Architecture

```
router.py
  └─ indicators_service.py  (NEW)
       ├─ parse_specs(i_params) → list[IndicatorSpec]
       └─ get_indicators(symbol, start, end, adjust, specs)
            ├─ query_cached()        # from service.py — reads kline_data
            ├─ _apply_adjust()       # from service.py — optional adjust
            ├─ calendar_service      # align to trading days
            └─ compute_many(df, specs)  # from tools/indicators.py
```

### `indicators_service.py`

```python
async def get_indicators(
    symbol: str, start: date, end: date,
    adjust: str | None, specs: list[IndicatorSpec],
) -> list[dict]:
    records = await get_kline(symbol, start, end, adjust)
    if not records:
        return []
    df = pd.DataFrame([r.model_dump() for r in records])
    if specs:
        df = compute_many(df, specs)
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")
```

### `parse_specs(i_params: list[str]) -> list[IndicatorSpec]`

- For each value in `i_params`:
  - If starts with `[` → `json.loads(urllib.parse.unquote(val))`
  - Else → shorthand parse: split on `:` → name + comma-separated positional params
- Validate each name is in `SUPPORTED` set, raise 422 if not
- Dedup identical specs (same logic as `compute_many`)

### Reuse existing code

| Component | Location | How |
|-----------|----------|-----|
| `get_kline` | `service.py` | full flow: cache → auto-sync → adjust |
| `compute_many` | `tools/indicators.py` | direct call on DataFrame |
| `IndicatorSpec` | `tools/indicators.py` | dataclass for spec definition |

## Error handling

| Condition | Status | Detail |
|-----------|--------|--------|
| Unknown indicator name | 422 | `unsupported indicator: xxx, supported: {SUPPORTED}` |
| Invalid shorthand format | 422 | parse error message |
| No K-line data in range | 200 | `[]` |
| DB unavailable | 500 | propagated from asyncpg |

## Files changed

| File | Action |
|------|--------|
| `app/indicators_service.py` | **CREATE** — parse + compute logic |
| `app/router.py` | **EDIT** — add `/indicators/{symbol}` route |
| `tests/test_router.py` | **EDIT** — add integration tests |
| `tests/test_indicators.py` | **CREATE** — unit tests for parse_specs |

## Testing

| Test | Level | File |
|------|-------|------|
| `parse_specs` single shorthand | unit | `test_indicators.py` |
| `parse_specs` multi shorthand | unit | `test_indicators.py` |
| `parse_specs` JSON format | unit | `test_indicators.py` |
| `parse_specs` mixed format | unit | `test_indicators.py` |
| `parse_specs` unknown → error | unit | `test_indicators.py` |
| `parse_specs` empty → `[]` | unit | `test_indicators.py` |
| `/indicators` returns 200 | integration | `test_router.py` |
| `/indicators` bad symbol → 422 | integration | `test_router.py` |
| `/indicators` unknown indicator → 422 | integration | `test_router.py` |
| `/indicators` with adjust | integration | `test_router.py` |
| `/indicators` no `i` → raw kline | integration | `test_router.py` |
