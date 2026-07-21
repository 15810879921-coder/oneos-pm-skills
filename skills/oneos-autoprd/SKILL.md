---
name: oneos-autoprd
description: >-
  Generates and keeps in sync OneOS AutoPRD (PM-facing requirements) plus Axhub
  Make annotation directory Markdown/PRD; on 需求定稿/定稿/确认定稿/本次定稿 appends
  functional release changelog below the PRD since last baseline. When a Yunxiao
  requirement advances to 分析中/设计中/待开发, creates a same-titled linked task
  (tag+create-time follow the requirement; 分析中/设计中 assignee=creator, 待开发
  assignee=何斐). Use eagerly for prototypes, AutoPRD, or Yunxiao requirement
  description/更新内容/stage advance. When writing Yunxiao description, paste the
  full requirements-prd.md Markdown file verbatim into 需求说明—do not summarize.
  Do not skip annotation sync, 定稿 changelog, MD-full description paste, or
  stage-task creation.
---

# OneOS AutoPRD

为 OneOS 业务模块生成**产品经理可读、可评审、可排期**的需求说明，并**自动挂到 Axhub Make 标注工具 → 原型目录**。

另支持：**需求定稿**时汇总功能/逻辑变更记录；发云效时将 `requirements-prd.md` **全文原样写入**需求描述；需求进入**分析中 / 设计中 / 待开发**时**自动创建与需求同名的关联任务**（写在本 Skill，不改云效 Skill）。

颗粒度对齐「保险采购」全模块 PRD：讲清做什么、谁用、故事点、正逆向、流程图与关键业务逻辑；**不写**表结构、接口、字段代码名、文件路径、实现清单。

## 何时使用（含自动触发）

**主动调用时**

- AutoPRD、OneOS 需求说明、整模块 PRD、故事点 + 流程图

**改原型时必须自动跟进（全局规则）**

- 正在修改 `src/prototypes/<id>/` 下页面、交互、文案、判定、验收相关内容
- 同一轮交付内同步更新 PRD Markdown + 标注目录，不得只改代码

**需求定稿时（强制）**

- 用户回复含：`需求定稿` / `定稿` / `确认定稿` / `本次定稿`
- 执行 [references/release-changelog.md](references/release-changelog.md)：写第 10 章 + 更新基线

**云效建需求 / 完善需求时（强制组合）**

- 与 `$yunxiao-requirement-lifecycle` 一起使用时：先跑本 Skill 落盘 MD，再写云效描述
- **需求描述写入方式（强制）**：把 `.spec/requirements-prd.md` **Markdown 全文原样复制**进云效「描述」，不得只用摘要；细则见 [references/yunxiao-description.md](references/yunxiao-description.md)
- 描述拼装：`原型链接` + `需求说明`（= MD 全文）+ `更新内容`（定稿增量）+ `更新内容·历史`

**云效需求推进至分析中 / 设计中 / 待开发时（强制）**

- 无论口令来自本 Skill 还是云效 Skill，只要本轮把需求推到上述状态，就执行 [references/yunxiao-stage-tasks.md](references/yunxiao-stage-tasks.md)
- 自动建**与需求同名**的任务并正式关联；标签与创建时间口径沿用需求；分析中/设计中负责人=创建人，待开发负责人=**何斐**

不要用本 Skill 替代：需求探索访谈、设计比稿、纯样式微调（无产品语义变化时可跳过全量重写）。

## 工作流

### 主流程（写/同步 PRD）

1. **定模块**：确认 OneOS 模块名与 `src/prototypes/<prototype-id>/`。
2. **读上下文（只取产品语义）**  
   - 用户说明、已确认口径、原型标注、`.spec/`、业务条线说明（`lines.ts`）  
   - 忽略实现细节；字段名/接口改写成业务语言。
3. **收敛边界**：做什么 / 不做什么、外部依赖、与其它模块关系。
4. **按模板成文**：下方「输出结构」；缺关键信息最多问 1～2 个问题，其余写「假设」。
5. **落盘 + 标注同步（强制）** — 见 [references/annotation-sync.md](references/annotation-sync.md)。

   | 顺序 | 动作 |
   |------|------|
   | A | 写/更新 `src/prototypes/<id>/.spec/requirements-prd.md` |
   | B | 写/更新 `src/resources/prd/<id>-autoprd.md` |
   | C | 更新 `annotation-source.json` **顶层** `directory.nodes`（PRD 全文 + 推荐分章）；禁止只写 `data.directory` |
   | D | 若存在 `scripts/sync-annotation-directory.mjs`，执行之 |

6. **交付说明**：路径、标注目录入口、故事点合计、开放问题/假设。

### 定稿流程（关键字触发）

见 [references/release-changelog.md](references/release-changelog.md)。摘要：

1. 读 PRD + `.spec/autoprd-baseline.json`
2. 汇总自上次定稿以来的**功能/逻辑**变更（排除样式/UI/表结构）
3. 追加到 `## 10. 功能变更记录`（最新在上）
4. 更新基线 JSON + 标注目录
5. 若同时发云效：按 [references/yunxiao-description.md](references/yunxiao-description.md) 将 **MD 全文**写入描述「需求说明」；本次定稿块 →「更新内容」；旧段 →「更新内容·历史」

### 云效需求描述（MD 全文直写 · 强制）

见 [references/yunxiao-description.md](references/yunxiao-description.md)。

**不要**摘要粘贴。标准动作：

1. 读 `src/prototypes/<id>/.spec/requirements-prd.md`
2. 将文件 **完整 Markdown 正文**写入云效描述的「需求说明」区
3. 上方可加「原型链接」；下方加「更新内容 / 更新内容·历史」

```markdown
## 原型链接
<URL>

## 需求说明
<requirements-prd.md 全文原样粘贴>

## 更新内容
<最新定稿块或「首版定稿 / 本轮无功能增量」>

## 更新内容·历史
<旧更新内容倒序，勿删除>
```

### 云效阶段任务（状态推进时强制）

见 [references/yunxiao-stage-tasks.md](references/yunxiao-stage-tasks.md)。摘要：

| 需求状态 | 任务标签 | 负责人 | 标题 |
|----------|----------|--------|------|
| 分析中 | 分析 | 需求创建人 | 与需求同名 |
| 设计中 | 设计 | 需求创建人 | 与需求同名 |
| 待开发 | 交付（或开发） | 何斐 | 与需求同名 |

正式关联需求；创建时间口径沿用需求；同阶段未取消任务不重复建。

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
- 定稿后：**功能变更记录**（第 10 章）

**禁止写**

- 数据库表、字段名、接口路径、代码路径、组件名、存储 key
- 研发实现指令（可写「正式环境由审批中心回写」这类业务依赖）
- 在变更记录里写样式/UI/表结构优化

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
## 10. 功能变更记录   ← 定稿后维护；日常改原型不强制每改必写
```

## 质量自检

- [ ] 产品经理不看代码也能评审
- [ ] 用户故事为起点 / 怎么运作 / 闭环
- [ ] `.spec/requirements-prd.md` 已更新
- [ ] 标注目录「产品需求说明（PRD）」已同步且正文一致
- [ ] 定稿时：第 10 章 + `autoprd-baseline.json` 已更新
- [ ] 发云效时：描述「需求说明」为 `requirements-prd.md` **全文原样**，非摘要
- [ ] 推进至分析中/设计中/待开发时：同名任务已创建或复用，正式关联，负责人正确
- [ ] 无表结构 / 接口 / 代码路径；变更记录无样式/UI 废话

## 参考

- 定稿变更日志：[references/release-changelog.md](references/release-changelog.md)
- 云效描述 MD 直写：[references/yunxiao-description.md](references/yunxiao-description.md)
- 云效阶段任务：[references/yunxiao-stage-tasks.md](references/yunxiao-stage-tasks.md)
- 标注同步细则：[references/annotation-sync.md](references/annotation-sync.md)
- 章节模板：[references/template.md](references/template.md)
- 故事示例：[references/granularity-example.md](references/granularity-example.md)
- 业务条线：`src/prototypes/lease-business-line-overview/lines.ts`
- 复杂判定规格：配合项目规则 `business-logic-documentation`
- 云效组合：`$yunxiao-requirement-lifecycle`（建需求时先本 Skill）
