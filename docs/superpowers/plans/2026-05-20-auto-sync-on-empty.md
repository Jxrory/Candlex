# Auto-Sync on Empty Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `refresh=false` and DB returns no data, auto-sync from akshare before returning.

**Architecture:** Add `if not records and not refresh: sync + re-query` block to each of 6 route handlers in `app/router.py`. Single file change.

**Tech Stack:** FastAPI, asyncpg

---

### Task 1: Add auto-sync-on-empty to all 6 handlers

**Files:**
- Modify: `app/router.py` (6 handlers)

The change is identical for all 6 handlers. Each currently ends with:

```python
    records = await <service>.<get_method>(pool, symbol, start, end)
    logger.info("GET /%s/%s returned %d records", ...)
    return records
```

Replace the above 3 lines in each handler with:

```python
    records = await <service>.<get_method>(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /%s/%s no cached data, auto-syncing", ..., symbol)
        count = await <service>.sync_symbol(pool, symbol)
        logger.info("GET /%s/%s auto-sync completed: %d records", ..., symbol, count)
        records = await <service>.<get_method>(pool, symbol, start, end)

    logger.info("GET /%s/%s returned %d records", ...)
    return records
```

- [ ] **Step 1: Edit `/balance/{symbol}` handler**

Old code at `app/router.py:117-120`:

```python
    records = await balance_sheet_service.get_balance_sheets(pool, symbol, start, end)
    logger.info("GET /balance/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await balance_sheet_service.get_balance_sheets(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /balance/%s no cached data, auto-syncing", symbol)
        count = await balance_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /balance/%s auto-sync completed: %d records", symbol, count)
        records = await balance_sheet_service.get_balance_sheets(pool, symbol, start, end)

    logger.info("GET /balance/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 2: Edit `/profit/{symbol}` handler**

Old code at `app/router.py:134-137`:

```python
    records = await profit_sheet_service.get_profit_sheets(pool, symbol, start, end)
    logger.info("GET /profit/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await profit_sheet_service.get_profit_sheets(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /profit/%s no cached data, auto-syncing", symbol)
        count = await profit_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /profit/%s auto-sync completed: %d records", symbol, count)
        records = await profit_sheet_service.get_profit_sheets(pool, symbol, start, end)

    logger.info("GET /profit/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 3: Edit `/cash-flow/{symbol}` handler**

Old code at `app/router.py:151-154`:

```python
    records = await cash_flow_sheet_service.get_cash_flow_sheets(pool, symbol, start, end)
    logger.info("GET /cash-flow/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await cash_flow_sheet_service.get_cash_flow_sheets(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /cash-flow/%s no cached data, auto-syncing", symbol)
        count = await cash_flow_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /cash-flow/%s auto-sync completed: %d records", symbol, count)
        records = await cash_flow_sheet_service.get_cash_flow_sheets(pool, symbol, start, end)

    logger.info("GET /cash-flow/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 4: Edit `/indicator/{symbol}` handler**

Old code at `app/router.py:100-103`:

```python
    records = await financial_indicator_service.get_indicators(pool, symbol, start, end)
    logger.info("GET /indicator/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await financial_indicator_service.get_indicators(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /indicator/%s no cached data, auto-syncing", symbol)
        count = await financial_indicator_service.sync_symbol(pool, symbol)
        logger.info("GET /indicator/%s auto-sync completed: %d records", symbol, count)
        records = await financial_indicator_service.get_indicators(pool, symbol, start, end)

    logger.info("GET /indicator/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 5: Edit `/dividend/{symbol}` handler**

Old code at `app/router.py:67-70`:

```python
    records = await dividend_service.get_events(pool, symbol, start, end)
    logger.info("GET /dividend/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await dividend_service.get_events(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /dividend/%s no cached data, auto-syncing", symbol)
        count = await dividend_service.sync_symbol(pool, symbol)
        logger.info("GET /dividend/%s auto-sync completed: %d records", symbol, count)
        records = await dividend_service.get_events(pool, symbol, start, end)

    logger.info("GET /dividend/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 6: Edit `/news/{symbol}` handler**

Old code at `app/router.py:168-171`:

```python
    records = await news_service.get_news(pool, symbol, start, end)
    logger.info("GET /news/%s returned %d records", symbol, len(records))
    return records
```

Replace with:

```python
    records = await news_service.get_news(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /news/%s no cached data, auto-syncing", symbol)
        count = await news_service.sync_symbol(pool, symbol)
        logger.info("GET /news/%s auto-sync completed: %d records", symbol, count)
        records = await news_service.get_news(pool, symbol, start, end)

    logger.info("GET /news/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 7: Verify app starts**

Run: `python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Run tests**

Run: `pytest tests/ -v 2>&1 | tail -30`
Expected: same results as before (2 news unit tests pass, route tests fail with UndefinedTableError as before)

- [ ] **Step 9: Commit**

```bash
git add app/router.py
git commit -m "feat: auto-sync from akshare on empty cache for all symbol endpoints"
```
