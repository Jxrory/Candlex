# Issue tracker: 本地 Markdown

本仓库的 issue 和 PRD 以 Markdown 文件形式存放在 `.scratch/` 目录下。

## 约定

- 每个功能一个目录：`.scratch/<feature-slug>/`
- PRD 文件：`.scratch/<feature-slug>/PRD.md`
- 实现 issue：`.scratch/<feature-slug>/issues/<NN>-<slug>.md`，从 `01` 开始编号
- Triage 状态通过文件头部附近的 `Status:` 行记录（具体取值见 `triage-labels.md`）
- 评论和讨论历史追加到文件末尾的 `## Comments` 标题下

## 当技能要求"发布到 issue tracker"

在 `.scratch/<feature-slug>/` 下创建新文件（如目录不存在则自动创建）。

## 当技能要求"获取相关 ticket"

读取指定路径的文件。用户通常会直接传入路径或 issue 编号。
