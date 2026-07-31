---
name: AutoRDO
description: >-
  AutoRDO (Requirement Description Optimization): cleans fragmented chat logs,
  voice transcripts, oral notes, and feedback ledgers into written title and description;
  auto-detects 类型/优先级/标签/提交部门/提交人 from content; maps OneOS modules via oneos-domain.md;
  splits multi-line into multiple results; if any 待确认 exists, MUST switch to Plan mode
  for choice-based confirmation. Does not change Yunxiao status or create tasks.
  Pair with YunxiaoPM for cloud write; never load retired lifecycle skill.
---

# AutoRDO

**Requirement Description Optimization**（需求描述优化）。  
将碎片化、通俗化文字（聊天/录音/反馈台账）在**保留原意**前提下拆解为**标题、描述**，并**自动识别**类型、优先级、标签、提交部门、提交人，供入库写入云效需求。  
多行/多条独立诉求 → **自动拆成多份**转译结果。  

**强制**：清洗结果中**只要存在任意「待确认」**，Agent **必须立刻** `SwitchMode` → **plan**，逐条用选择题消解；**无需**用户再说「确认待确认」。无待确认则可直接交定稿。

## 交付任务专用（YunxiaoPM 调用）

生成/回填 **【交付】** 描述时，YunxiaoPM **必须直接调用本 Skill**，按 [references/delivery-rules-chapter.md](references/delivery-rules-chapter.md) 产出**单独一章**：

```markdown
## 规则对照（AutoRDO）

### 修改前规则
- …

### 修改后规则
- …
```

需求侧「原始诉求」仍用下文常规模板；**不要**把规则对照章与需求清洗稿混成一段。

## 边界（强制）

| 做 | 不做 |
|---|---|
| 提炼标题与书面描述；自动识别类型/优先级/标签/提交部门/提交人 | 改云效状态 / 建任务 / **直接**打云效标签 |
| 多行/多条 → 多份转译结果 | 写成完整 AutoPRD / 臆造业务结论 |
| 有待确认 → 强制 Plan 逐条确认 | 停在初稿等口令；把猜测写入定稿 |
| 去除描述**结尾句号** | 加载已下架的旧云效 lifecycle Skill |

云效建单与打标由 **`$YunxiaoPM`（需求任务）** 负责；本 Skill 只出清洗稿、推荐元数据，以及【交付】用的**规则对照章**。

## 跨 Skill 逻辑交接（强制）

- 下游只传正式 Skill 名 **`YunxiaoPM`**、清洗后的标题/描述、结构化元数据，以及材料版本或内容哈希等必要证据标识。
- 禁止定位、读取或要求用户提供其他 Skill 的安装目录；不同客户端之间不得通过物理文件路径交接。
- 下游需要调用时只输出正式选择器 **`/skill YunxiaoPM`**，不得输出旧名称或安装路径。

## 何时使用

- 口令含 `AutoRDO` / `清洗聊天` / `录音整理` / `原始诉求`
- 粘贴反馈台账（含部门/优先级/模块列）或口述碎片
- YunxiaoPM「记录需求」前必须先跑本 Skill（材料为碎片/台账时）
- **YunxiaoPM 生成/回填【交付】描述**：必须调用本 Skill，产出 [delivery-rules-chapter.md](references/delivery-rules-chapter.md) 规则对照章（修改前 + 修改后）

## 输入

- 聊天、会议速记、口述、录音转写
- **多行/台账**：含反馈人、所属部门、业务模块、优先级、PC或移动端等列时优先采信列值
- 确认阶段补充文字

## 处理规则

**强制前置**：ONE-OS 材料先 Read [references/oneos-domain.md](references/oneos-domain.md)，元数据规则见 [references/meta-fields.md](references/meta-fields.md)，再按 [references/rules.md](references/rules.md) 执行。

1. **多条拆解** → 每条独立成稿  
2. **OneOS 对齐** → 模块/部门标准名  
3. **元数据识别** → 类型、优先级、标签、提交部门、提交人（显式列 > 正文标记 > 语义推断；不确定 → 待确认）  
4. **标题 + 描述转译** → 去口语、去结尾句号  
5. **有待确认 → 强制 Plan** → 见 [references/confirm-pending.md](references/confirm-pending.md)  

## 输出

```markdown
## 原始诉求（AutoRDO）

**标题**：<清晰标题>
**类型**：【新增】|【优化】
**优先级**：P1-高|P2-中|P3-低
**标签**：<标准模块>[, PC端|小程序]
**提交部门**：<标准部门名或空>
**提交人**：<姓名或空>

**描述**：
<转译正文；无结尾句号>
反馈：<有则附日期/禅道/状态/端>

待确认：
- …
```

多条时先写「共 N 条」，再 `### 1` … `### N`。  
交 YunxiaoPM 示例：`记录需求：标题=…；类型=…；优先级=…；标签=…；提交部门=…；提交人=…；描述=…`  
交【交付】描述：先跑本 Skill 产出规则对照章，再由 YunxiaoPM 写入交付任务。

## 口令

```text
AutoRDO：<粘贴聊天或台账行>
AutoRDO：录音转写如下 …
按下列补充消解待确认：
<补充说明>
```
