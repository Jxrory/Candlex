# News Endpoint Design

**Goal:** Add `GET /news/{symbol}` endpoint caching individual stock news articles via `ak.stock_news_em`.

## Route

```
GET /news/{symbol}?start=&end=&refresh=
```

`start`/`end` are ISO datetime (filters on `publish_time`). `refresh=true` triggers akshare fetch.

## Schema

```sql
CREATE TABLE IF NOT EXISTS news (
    symbol       TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    publish_time TIMESTAMPTZ,
    source_name  TEXT,
    url          TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, url)
);
```

Plain table (not a hypertable) — news is not time-series data that needs partitioning.

## Data model

```python
class NewsRecord(BaseModel):
    symbol: str
    title: str
    content: str
    publish_time: datetime | None = None
    source_name: str | None = None
    url: str
```

## Deduplication

`PRIMARY KEY (symbol, url)` + `ON CONFLICT DO UPDATE` — same URL never creates duplicate rows, overwrites all columns on re-fetch.

## Source (`app/sources/news.py`)

Wraps `ak.stock_news_em(symbol="600519")`. Extracts bare 6-digit code via `symbol.split(".")[1]`.

The akshare API accepts both bare `600519` and `SH600519`; the spec follows the documented bare-code interface.

Column mapping:
| akshare column | Internal field |
|---|---|
| 关键词 | → `symbol` (e.g. `SH600519`) |
| 新闻标题 | → `title` |
| 新闻内容 | → `content` |
| 发布时间 | → `publish_time` (parsed to datetime) |
| 文章来源 | → `source_name` |
| 新闻链接 | → `url` |

## Service (`app/news.py`)

- `get_news(pool, symbol, start, end)` — SELECT with optional datetime filters
- `sync_symbol(pool, symbol)` — fetch from akshare, upsert into DB

## Files

| File | Action |
|------|--------|
| `app/sources/news.py` | Create — NewsSource |
| `app/news.py` | Create — NewsService |
| `app/schemas.py` | Add NewsRecord |
| `app/router.py` | Add GET /news/{symbol} |
| `app/ak_trace.py` | Add `stock_news_em` to `_extract_params` |
| `tests/test_news.py` | Create — unit + route smoke tests |
| `scripts/init_db.sql` | Append `news` table |
