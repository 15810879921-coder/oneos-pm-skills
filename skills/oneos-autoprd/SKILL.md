---
name: oneos-autoprd
description: >-
  Generates and keeps in sync OneOS AutoPRD (PM-facing requirements) plus Axhub
  Make annotation directory Markdown/PRD. Use eagerly whenever the user edits
  OneOS prototypes under src/prototypes/, asks for AutoPRD / 需求说明 / 整模块 PRD /
  用户故事与故事点 / 正向逆向 / 流程图, or when prototype behavior, copy, flows, or
  acceptance criteria change—then update .spec/requirements-prd.md and the
  annotation-source.json directory PRD entry in the same turn. Do not skip
  annotation sync after writing PRD.
---

# OneOS AutoPRD

为 OneOS 业务模块生成**产品经理可读、可评审、可排期**的需求说明，并**自动挂到 Axhub Make 标注工具 → 原型目录**。

颗粒度对齐「保险采购」全模块 PRD：讲清做什么、谁用、故事点、正逆向、流程图与关键业务逻辑；**不写**表结构、接口、字段代码名、文件路径、实现清单。

## 何时使用（含自动触发）

**主动调用时**

- AutoPRD、OneOS 需求说明、整模块 PRD、故事点 + 流程图

**改原型时必须自动跟进（全局规则）**

- 正在修改 `src/prototypes/<id>/` 下页面、交互、文案、判定、验收相关内容
- 同一轮交付内同步更新 PRD Markdown + 标注目录，不得只改代码

不要用本 Skill 替代：需求探索访谈、设计比稿、纯样式微调（无产品语义变化时可跳过全量重写，见 annotation-sync）。

## 工作流

1. **定模块**：确认 OneOS 模块名与 `src/prototypes/<prototype-id>/`。
2. **读上下文（只取产品语义）**  
   - 用户说明、已确认口径、原型标注、`.spec/`、业务条线说明（`lines.ts`）  
   - 忽略实现细节；字段名/接口改写成业务语言。
3. **收敛边界**：做什么 / 不做什么、外部依赖、与其它模块关系。
4. **按模板成文**：下方「输出结构」；缺关键信息最多问 1～2 个问题，其余写「假设」。
5. **落盘 + 标注同步（强制，缺一不可）**  
   详见 [references/annotation-sync.md](references/annotation-sync.md)。

   | 顺序 | 动作 |
   |------|------|
   | A | 写/更新 `src/prototypes/<id>/.spec/requirements-prd.md` |
   | B | 写/更新 `src/resources/prd/<id>-autoprd.md`（与 A 同文或摘要+链到 A） |
   | C | 更新 `annotation-source.json` → `directory.nodes`：确保有「产品需求说明（PRD）」`markdown` 节点，`markdownPath: ".spec/requirements-prd.md"`，且 `markdown` 正文与文件一致 |
   | D | 若存在 `scripts/sync-annotation-directory.mjs`，执行之 |

6. **交付说明**：路径、标注目录入口标题、故事点合计、开放问题/假设。

## 写作硬约束

**必须写**

- 一句话定位 + 目标 / 非目标
- 模块边界（含 mermaid 总览更好）
- 角色与目标（角色名优先对齐业务条线说明）
- **用户故事**（业务条线说明口径）+ Epic 级**故事点（SP）**粗估
- 分功能**正向**与**逆向/边界**
- 至少 1～2 个 **mermaid** 流程图
- **关键业务逻辑**（业务话）
- 验收清单 + 「交付口径」一段话

**禁止写**

- 数据库表、字段名、接口路径、代码路径、组件名、存储 key
- 研发实现指令（可写「正式环境由审批中心回写」这类业务依赖）

## 用户故事口径（强制 · 对齐业务条线说明）

真相源：原型 **业务条线说明**（`lease-business-line-overview` / `lines.ts`）。  
每条能力用「责任部门 → **起点** → **怎么运作** → **闭环**」叙述；**不要**用「作为…我希望…」宽表作主叙述。

| 块 | 写什么 |
|----|--------|
| 角色 | 谁负责、谁协同 |
| 起点 | 谁在什么前提下启动 |
| 怎么运作 | 有序步骤，含跨角色协作 |
| 关键结果 | 可选标签 |
| 闭环 | 业务终点与可追溯性 |

可选：`US-xx`、压缩句「作为…我想…以便…」、规模 S/M/L 或 SP（仅排期，不替代主叙述）。

## 输出结构

完整模板：[references/template.md](references/template.md)。

```markdown
# <模块名> · 产品需求说明（全模块）

## 1. 一句话与目标
## 2. 模块边界（最重要）
## 3. 用户与角色
## 4. 用户故事与故事点（业务条线说明口径）
## 5. 功能模块说明（正向 / 逆向）
## 6. 关键业务逻辑（必须对齐）
## 7. 总览流程图
## 8. 验收清单
## 9. 交付口径
```

## 质量自检

- [ ] 产品经理不看代码也能评审
- [ ] 用户故事为起点 / 怎么运作 / 闭环
- [ ] `.spec/requirements-prd.md` 已更新
- [ ] 标注目录「产品需求说明（PRD）」已同步且正文一致
- [ ] 无表结构 / 接口 / 代码路径

## 参考

- 标注同步细则：[references/annotation-sync.md](references/annotation-sync.md)
- 章节模板：[references/template.md](references/template.md)
- 故事示例：[references/granularity-example.md](references/granularity-example.md)
- 业务条线：`src/prototypes/lease-business-line-overview/lines.ts`
- 复杂判定规格：配合项目规则 `business-logic-documentation`（`.spec/<topic>.md`）
