# CandleX

Daily K-line caching service for Chinese A-stocks, using akshare with multi-source failover.

## Quick start

```bash
source ./.venv/bin/activate
uvicorn app.main:app    # runs on :8000
pytest                  # asyncio_mode=auto, no extra flags needed
pytest tests/test_foo.py -k test_name
```

## Agent skills

### Issue tracker

本仓库使用本地 Markdown 文件跟踪 issue，存放在 `.scratch/` 目录下。详见 `docs/agents/issue-tracker.md`。

### Triage labels

五个标准 triage 角色使用默认标签名。详见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文布局 — 根目录下有 `CONTEXT.md`，暂无 `docs/adr/`。详见 `docs/agents/domain.md`。

## 默认语言

交互和输出文档请使用中文