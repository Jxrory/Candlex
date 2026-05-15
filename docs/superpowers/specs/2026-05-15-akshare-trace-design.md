# Akshare 调用追踪设计

## 概述

对所有 akshare API 调用进行统一追踪：日志记录完整返回体，PG 记录调用摘要。

## 追踪范围

| 文件 | API | 方式 |
|------|-----|------|
| `app/sources/sina.py` | `ak.stock_zh_a_daily` | 装饰器 |
| `app/sources/tencent.py` | `ak.stock_zh_a_hist_tx` | 装饰器 |
| `app/sources/eastmoney.py` | `ak.stock_zh_a_hist` | 装饰器 |
| `app/sources/dividend.py` | `ak.stock_history_dividend_detail` ×2 | 装饰器（拆两个私有方法） |
| `app/calendar.py` | `ak.tool_trade_date_hist_sina` | 装饰器（普通函数） |

## PG 表

```sql
CREATE TABLE IF NOT EXISTS api_request_log (
    id          BIGSERIAL,
    api_name    TEXT    NOT NULL,
    symbol      TEXT,              -- 股票代码（如有）
    params      JSONB,             -- 调用参数
    status      TEXT    NOT NULL,   -- 'success' | 'error'
    row_count   INTEGER,           -- 返回行数
    duration_ms INTEGER,           -- 耗时(毫秒)
    error_msg   TEXT,              -- 错误信息
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

SELECT create_hypertable('api_request_log', 'created_at', if_not_exists => TRUE);
```

## 模块：app/ak_trace.py

### trace_akshare 装饰器

```python
def trace_akshare(api_name: str):
    """装饰 Source.fetch() 或任意 akshare 调用函数。兼容 async/sync、有self/无self。"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            params = _extract_params(api_name, args, kwargs)
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                elapsed, row_count = ...

                logger.info("akshare %s ...", api_name, params, ...)
                logger.debug("akshare %s response_body=%s", api_name, ...)

                _schedule_pg_insert(...)
                return result
            except Exception as e:
                elapsed = ...
                logger.error("akshare %s FAILED ...", ...)
                _schedule_pg_insert(..., error=str(e))
                raise
        return wrapper
    return decorator
```

### 异步 PG 写入

- 全局 `asyncio.Queue` 接收日志条目
- 单个 writer 协程消费队列，批量 Insert
- FastAPI lifespan 中启动/停止 writer

## 日志输出

| 级别 | 内容 | 控制方式 |
|------|------|---------|
| INFO | api_name, params, status, rows, duration_ms | 默认 |
| ERROR | api_name, params, error, duration_ms | 错误时 |
| DEBUG | 完整 response body | LOG_LEVEL=DEBUG |

## 集成方式

**SinaSource**: `@trace_akshare("stock_zh_a_daily")` on `fetch()`
**TencentSource**: `@trace_akshare("stock_zh_a_hist_tx")` on `fetch()`
**EastMoneySource**: `@trace_akshare("stock_zh_a_hist")` on `fetch()`
**DividendSource**: `@trace_akshare("stock_history_dividend_detail")` on `_fetch_dividend()` and `_fetch_rights()`
**CalendarService**: `@trace_akshare("tool_trade_date_hist_sina")` on `_fetch_all()`（同步函数，装饰器适配）

## 项目结构变化

```
app/
├── ak_trace.py          # 新增：装饰器 + 异步 writer
├── main.py              # + log_writer task 启停
├── sources/
│   ├── sina.py          # + @trace_akshare
│   ├── tencent.py       # + @trace_akshare
│   ├── eastmoney.py     # + @trace_akshare
│   └── dividend.py      # + @trace_akshare（拆方法）
├── calendar.py          # + @trace_akshare
scripts/
└── init_db.sql          # + api_request_log 表
```

## 错误处理

- PG 写入失败不抛异常（`logger.warning` 降级），不阻塞业务
- akshare 调用失败由装饰器捕获并记录，再重新抛出给调用方
- Queue 满时 `put_nowait` 丢弃（队列大小设 1000）
