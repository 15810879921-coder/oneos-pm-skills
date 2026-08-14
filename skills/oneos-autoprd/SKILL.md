---
name: oneos-autoprd
description: >-
  OneOS AutoPRD: generates PM-facing requirements (总览/目标/边界/角色/用户故事
  起点→运作→闭环/故事点/正逆向/流程图/关键逻辑/状态/风险/交付) and syncs Axhub Make
  annotation PRD. On 需求定稿/本轮定稿 appends functional changelog with auto
  V主.副.子 (user 主/副/子 override wins). With YunxiaoPM design-complete,
  writes Markdown into 【交付】 by task number (not at create; placeholder until then).
  Use for AutoPRD, prototypes, 产品说明, 本轮定稿. Never create same-titled stage
  tasks; never load retired yunxiao-requirement-lifecycle; cloud combo is YunxiaoPM only.
---

# AutoPRD（oneos-autoprd）

为 OneOS 业务模块生成**产品经理可读、可评审、可排期**的需求说明，并**自动挂到 Axhub Make 标注工具 → 原型目录**。

另支持：**本轮定稿 / 需求定稿**时汇总功能变更并**自动递增 PRD 版本号**；与 **`$YunxiaoPM`** 组合时，在**设计完成**（或显式同步交付）把 Markdown 写入【交付】任务描述。

旧包 `yunxiao-requirement-lifecycle` **已下架**勿加载。云效状态机与【交付】/【分析】/【设计】树**只**由 YunxiaoPM 负责；本 Skill **不**建同名无前缀阶段任务。

颗粒度：讲清做什么、谁用、故事点、正逆向、流程图与关键业务逻辑；**不写**表结构、接口、字段代码名、文件路径、实现清单。

## 何时使用（含自动触发）

**主动调用**

- AutoPRD、OneOS 需求说明、整模块 PRD、故事点 + 流程图、产品说明

**改原型时必须自动跟进**

- 修改 `src/prototypes/<id>/` 下页面、交互、文案、判定、验收相关内容
- 同一轮同步更新 PRD Markdown + 标注目录；**纯样式且无产品语义变化可跳过全量重写**

**需求定稿时（强制）**

- 关键字：`需求定稿` / `定稿` / `确认定稿` / `本次定稿` / **`本轮定稿`**
- 执行 [references/release-changelog.md](references/release-changelog.md)：第 10 章 + `prdVersion` 基线

**与 YunxiaoPM 组合（强制 · 唯一云效组合）**

- 设计完成或完善「产品说明」：先本 Skill 落盘 MD，再由 YunxiaoPM / 本 Skill 按 [yunxiao-description.md](references/yunxiao-description.md) 写入需求 `## 产品说明（AutoPRD）`（**不覆盖** `## 原始诉求（AutoRDO）` / `## 工作项编号（系统）`）
- **创建【交付】时不写 PRD 正文**（占位由 YunxiaoPM 写入）；设计完成或口令「同步交付说明」时按 [yunxiao-delivery-sync.md](references/yunxiao-delivery-sync.md) 用任务**编号**回填【交付】
- 入库前聊天/录音清洗：先 `$AutoRDO`，再 YunxiaoPM 记录需求

**跨 Skill 逻辑交接（强制）**

- 只向 `YunxiaoPM` 传递正式 Skill 名、需求/交付任务编号、PRD 版本、正文或对象存储证据标识；不得传递安装位置。
- 禁止定位或读取其他 Skill 的安装目录。每个 Skill 只读取自身包内资源；缺少云效上下文时，按编号实时查询或要求上游补齐逻辑交接字段。
- 下一跳只能输出正式选择器 `$YunxiaoPM`。

## 工作流

### 主流程（写/同步 PRD）

1. **定模块**：OneOS 模块名与 `src/prototypes/<prototype-id>/`。
2. **读上下文（只取产品语义）**  
   - 用户说明、已确认口径、原型标注、`.spec/`、业务条线说明（`lines.ts`）  
   - 忽略实现细节；字段名/接口改写成业务语言。
3. **收敛边界**：做什么 / 不做什么、外部依赖、与其它模块关系。
4. **按模板成文**：见「输出结构」与 [references/template.md](references/template.md)。
5. **落盘 + 标注同步（强制）** — [references/annotation-sync.md](references/annotation-sync.md)。

   | 顺序 | 动作 |
   |------|------|
   | A | 写/更新 `src/prototypes/<id>/.spec/requirements-prd.md` |
   | B | 写/更新 `src/resources/prd/<id>-autoprd.md` |
   | C | 更新 `annotation-source.json` **顶层** `directory.nodes`（PRD 全文 + 推荐分章） |
   | D | 若存在 `scripts/sync-annotation-directory.mjs`，执行之 |

6. **交付说明**：路径、标注入口、故事点合计、开放问题/假设。

### 定稿流程

见 [references/release-changelog.md](references/release-changelog.md)。含自动 `V主.副.子`；**用户显式指定主/副/子时以用户为准**。

### 云效需求「产品说明」（与 YunxiaoPM 双段模板）

见 [references/yunxiao-description.md](references/yunxiao-description.md)。

### 云效【交付】回填（设计完成 · 非创建时）

见 [references/yunxiao-delivery-sync.md](references/yunxiao-delivery-sync.md)。

## 写作硬约束

**必须写（映射用户概要）**

| 概要能力 | 落在章节 |
|---|---|
| 总览 | §1 一句话与目标 |
| 目标 / 边界 | §1–2 |
| 角色 | §3 |
| 用户故事（起点→运作→闭环）+ 故事点 | §4 |
| 正逆向流程 | §5 |
| 关键逻辑 / 状态 / 风险 | §6（及验收相关） |
| 流程图 | §7 |
| 交付 | §9 交付口径 |
| 定稿变更 | §10 |

另：验收清单 §8；对象存储预览链接形态 `{baseUrl}/{prototype-id}/index.html`（禁止加 `prototypes/` 前缀、禁止去掉 `index.html`）。

**禁止写**

- 数据库表、字段名、接口路径、代码路径、组件名、存储 key
- 变更记录里的样式/UI/表结构优化
- 引导加载已下架 lifecycle 或「同名阶段任务」建单

## 用户故事口径（强制 · 对齐业务条线说明）

真相源：业务条线说明（`lease-business-line-overview` / `lines.ts`）。  
主叙述：**起点 → 怎么运作 → 闭环**（不要用「作为…我希望…」宽表作主叙述）。

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
## 10. 功能变更记录   ← 定稿维护；含 V主.副.子
```

## 质量自检

- [ ] 产品经理不看代码也能评审
- [ ] 用户故事为起点 / 怎么运作 / 闭环
- [ ] `.spec/requirements-prd.md` + 标注目录已同步
- [ ] 定稿时：第 10 章含版本号 + `autoprd-baseline.json` 含 `prdVersion`
- [ ] 与 YunxiaoPM 设计完成：【交付】按**编号**回填，创建时未提前灌 MD
- [ ] 全文无已下架 lifecycle 引导；无同名阶段任务建单
- [ ] 变更记录无样式/UI/表结构废话

## 参考

- 定稿与版本：[references/release-changelog.md](references/release-changelog.md)
- 云效产品说明：[references/yunxiao-description.md](references/yunxiao-description.md)
- 【交付】回填：[references/yunxiao-delivery-sync.md](references/yunxiao-delivery-sync.md)
- 标注同步：[references/annotation-sync.md](references/annotation-sync.md)
- 模板：[references/template.md](references/template.md)
- 故事示例：[references/granularity-example.md](references/granularity-example.md)
- 业务条线：`src/prototypes/lease-business-line-overview/lines.ts`
- 云效组合（唯一）：`$YunxiaoPM`
- 入库清洗：`$AutoRDO`
