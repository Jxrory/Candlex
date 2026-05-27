# get_kline 支持可选数据源参数

## Motivation

`get_kline` 目前按 `source_priority` 列表依次尝试，无法强制使用指定数据源。需要支持传入 `source` 参数，同时保持向后兼容。

## Design

### API 签名

```python
async def get_kline(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
    source: str | None = None,       # ← 新增
) -> list[KlineRecord]:
```

- `source` 为 `None`（默认）→ 现有逻辑不变，按 `settings.source_priority` 遍历
- `source` 指定值 → 优先尝试该源，失败后回退到 `source_priority` 列表

### 实现方式

将 `source` 插入到有效优先级列表的头部：

```python
effective_priority = list(settings.source_priority)
if source:
    if source in effective_priority:
        effective_priority.remove(source)
    effective_priority.insert(0, source)
```

两处数据获取循环（partial cache miss 和 cache miss）统一使用 `effective_priority`，其余逻辑不变。

### KlineSyncService 变更

`KlineSyncService.sync_one` 增加 `source` 参数，透传给 `get_kline`：

```python
async def sync_one(self, pool: asyncpg.Pool, source: str | None = None) -> int:
    ...
    records = await get_kline(symbol, Y2000, yesterday, source=source)
```

默认 `None`，不影响现有行为。

### Router 变更

`/kline/{symbol}` 增加可选 `source` query parameter：

```python
source: str | None = Query(None)
```

传给 `get_kline`，不校验取值（由 service 层自然处理）。

### 错误处理

- `source` 不在 `SOURCES` dict 中 → `SOURCES.get(source_name)` 返回 `None` → `continue` → 回退到下一个优先级源
- 指定源自身失败 → 已在 `try/except` 中，logger 记录错误后继续下一个源

### 调用者影响

| 调用方 | 改动 |
|--------|------|
| `app/router.py` | 加 `source` query param |
| `app/indicators_service.py` | 不变（默认 None） |
| `app/kline_sync.py` | `sync_one` 也接收 `source` 参数（默认 None），传给 `get_kline` |

### 测试

**`test_service.py` — 数据源格式验证**

每个 source 的 `fetch()` 返回的 DataFrame 需满足以下契约：
- 包含列：`date`, `open`, `high`, `low`, `close`, `volume`, `amount`
- `date` 列为 datetime 或 date 类型
- `open`, `high`, `low`, `close`, `amount` 为数值类型
- `volume` 为整数或 None
- 每行满足 `high >= open, close, low`

通过 mock akshare API，模拟各源原始返回数据，验证 `fetch()` 输出格式正确。

| 测试 | 验证内容 |
|------|----------|
| `test_sina_source_format` | mock `ak.stock_zh_a_daily`，验证 DataFrame 列名、类型、列间约束 |
| `test_tencent_source_format` | mock `ak.stock_zh_a_hist_tx`，同上（注意 tencent 列顺序不同：`date,open,close,high,low,amount`，volume 为 None） |
| `test_eastmoney_source_format` | mock `ak.stock_zh_a_hist`，同上（注意 eastmoney 列名来自中文映射） |
| `test_get_kline_with_source` | mock source fetch，验证指定源被优先调用，失败后回退 |

**`test_router.py`**

- 新增测试：`/kline/{symbol}?source=sina` 路由参数传递正常

**`test_kline_sync.py`**

- `test_sync_one_with_source`：验证 `sync_one(pool, source="sina")` 透传给 `get_kline`
