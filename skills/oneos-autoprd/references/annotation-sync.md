# Axhub 标注目录同步（强制）

使用 OneOS AutoPRD 时，除资源库归档外，**必须**把 PRD 挂到 Axhub Make 标注工具的「原型目录」里，用户才能在右侧面板直接打开。

## 落点（三份必须一致）

| # | 路径 | 作用 |
|---|------|------|
| 1 | `src/prototypes/<prototype-id>/.spec/requirements-prd.md` | **主真相**：产品可读 PRD 全文 |
| 2 | `src/prototypes/<prototype-id>/annotation-source.json` → **顶层** `directory.nodes` | **标注目录入口**：面板里可见的 Markdown/PRD |
| 3 | `src/resources/prd/<prototype-id>-autoprd.md` | 资源库归档（可选但默认写） |

可选：复杂判定另写 `.spec/<topic>.md`，目录里再挂一条，并在 PRD 里链过去（与 `business-logic-documentation` 一致）。

## ⚠️ 目录必须写在文档顶层（常见踩坑）

Wire format（与 `prototype-annotation` 一致）：

```json
{
  "documentVersion": 1,
  "format": "axhub-annotation-source",
  "data": { "version": 2, "prototypeName": "...", "nodes": [] },
  "markdownMap": {},
  "assetMap": {},
  "directory": { "nodes": [] }
}
```

| 正确 | 错误 |
|------|------|
| 顶层 `directory.nodes` | 只写在 `data.directory` |
| `PrototypeAnnotationHost` / Make 读的是 `source.directory` | 写在 `data` 下时右侧「原型目录」为空 |

若误写在 `data.directory`：迁移到顶层 `directory`，并删除 `data.directory`，避免双源。

## 目录节点写法（推荐）

在说明根 `folder` 的 `children` **靠前**插入或更新：

```json
{
  "type": "markdown",
  "id": "<prefix>-doc-prd",
  "title": "产品需求说明（PRD）",
  "markdownPath": ".spec/requirements-prd.md",
  "markdown": "<与 .spec/requirements-prd.md 相同的全文>"
}
```

### 分章节 PRD（推荐，便于右侧目录浏览）

在「产品需求说明（PRD）」旁增加文件夹 **「PRD 分章」**，按 PRD 的 `##` 一级标题拆成多个 `markdown` 子节点（标题用章节名，正文为该章全文）。专题规格（`.spec/<topic>.md`）放在 **「专题规格」** 文件夹。

参考结构：

```text
folder  <模块>说明
  markdown  产品需求说明（PRD）     ← 全文
  folder    PRD 分章
    markdown  1. 一句话与目标
    markdown  2. 模块边界
    …
  folder    专题规格
    markdown  <topic 标题>
```

有 `scripts/sync-annotation-directory.mjs` 的原型：改 PRD / `.spec` 后**必须执行**该脚本再生目录。

定稿后第 10 章「功能变更记录」必须进入 PRD 全文节点；若有「PRD 分章」，同步该章节点。详见 [release-changelog.md](release-changelog.md)。

约定：

- `id`：`<短前缀>-doc-prd`（如 `ipc-doc-prd`、`wb-doc-prd`、`h5-va-doc-prd`）
- `title`：优先「产品需求说明（PRD）」；已有「PRD」可保留不改名
- **同时写** `markdownPath` + `markdown`：构建可内联路径，运行时目录也能直接读到正文
- 若已有同 id / 同标题节点：只更新正文与 path，不新建重复入口
- 遵守 `prototype-annotation-layout`：目录以 `markdown` 为主，不要用 `link`/`route` 顶替 PRD

## 增量改原型时怎么更新

1. 根据改动的文件路径确定 `<prototype-id>`。
2. 读现有 `.spec/requirements-prd.md`（没有则按 AutoPRD 模板新建）。
3. 只改受影响章节（故事、正逆向、关键逻辑、验收）；其余保留。
4. 回写 `.spec` + `resources/prd` + **顶层** `annotation-source.json` → `directory`（正文与文件一致；含分章节点）。
5. 若原型有 `scripts/sync-annotation-directory.mjs`，改完后执行它。

## 可跳过全量重写的情况

纯样式、无文案/无流程/无判定变化的微调：不必重写整份 PRD，但若改了用户可见文案或交互结果，仍须同步对应段落与目录节点。

## 验收

- [ ] `.spec/requirements-prd.md` 存在且为最新
- [ ] `annotation-source.json` **顶层**有 `directory.nodes`（不是只在 `data` 下）
- [ ] 标注目录能打开「产品需求说明（PRD）」且内容与文件一致
- [ ] 若有「PRD 分章」：各章可单独打开
- [ ] 用户故事仍为业务条线说明口径（起点 / 怎么运作 / 闭环）
