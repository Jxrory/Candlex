# Domain Docs

工程技能在探索代码库时，应如何消费本仓库的领域文档。

## 探索前，先阅读以下内容

- **`CONTEXT.md`**（在仓库根目录下），或
- **`CONTEXT-MAP.md`**（如果存在的话）——它指向每个上下文的 `CONTEXT.md`。阅读与当前主题相关的所有上下文。
- **`docs/adr/`**——阅读与你即将修改的领域相关的 ADR。在多上下文仓库中，还需检查 `src/<context>/docs/adr/` 下的上下文特定决策。

如果上述文件不存在，**静默处理**。不要提示缺失，也不要建议立即创建。`/grill-with-docs` 技能会在需要时按需创建它们。

## 文件结构

单上下文仓库（大多数仓库）：

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

多上下文仓库（根目录下存在 `CONTEXT-MAP.md`）：

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← 上下文特定决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用词汇表中的术语

当你的输出中命名某个领域概念时（在 issue 标题、重构建议、假设或测试名称中），请使用 `CONTEXT.md` 中定义的术语。不要使用该词汇表明确避免的同义词。

如果你需要的概念不在词汇表中，这是一个信号——要么你在使用项目不用的语言（请重新考虑），要么确实存在空白（请记录下来供 `/grill-with-docs` 处理）。

## 标记 ADR 冲突

如果你的输出与现有 ADR 矛盾，请明确指出来，而不是悄无声息地覆盖：

> _与 ADR-0007（event-sourced orders）冲突——但值得重新讨论，因为…_
