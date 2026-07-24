---
name: AutoRDO
description: >-
  AutoRDO (Requirement Description Optimization): cleans fragmented chat logs,
  voice transcripts, and oral notes into written title and description while keeping original
  meaning—extracts a clear, concise title based on understanding, maps to OneOS modules/departments
  via oneos-domain.md, translates raw text into written description; when pasted multi-line or
  multi-item data, splits into multiple requirement results; after draft, confirms 待确认
  items one-by-one in Cursor Plan mode with choice questions aided by oneos-domain and optional
  free-text requirement supplements,
  removes filler/self-corrections/trailing periods; light formatting only.
  Use when user says AutoRDO, 清洗聊天, 录音整理, 原始诉求, 确认待确认, AutoRDO确认, or before YunxiaoPMapp
  记录需求. Does not change Yunxiao status or create tasks. Pair with YunxiaoPMapp
  for cloud write; never load yunxiao-requirement-lifecycle.
---

# AutoRDO

**Requirement Description Optimization**（需求描述优化）。  
将碎片化、通俗化文字（多为聊天记录）与录音转写，在**保留原意**前提下自动拆解并提炼为清晰的**标题**与**描述**（书面表达），供入库写入云效需求。  
若一次粘贴**多行 / 多条**彼此独立的诉求，**自动拆成多份**转译结果（一份需求一份稿），不合并成一条。  
清洗稿中的「待确认」可进入 **Plan 模式逐条人工确认**：优先选择题（选项参照 OneOS 词典），也支持用补充需求描述消解。

## 边界（强制）

| 做 | 不做 |
|---|---|
| 根据内容理解自动提炼清晰、简洁的标题 | 改云效状态 / 建任务 / 打标签 |
| 清洗措辞、将原文转译为规范书面描述 | 写成完整 AutoPRD 六大块 / 十章 PRD |
| 多行/多条独立诉求 → 拆成多份转译结果 | 臆造未出现的业务结论 |
| 不确定处标「待确认」 | 把多条无关需求硬揉成一条 |
| 待确认 → Plan 逐条确认（优先选择 + 可文字补充） | 跳过确认把猜测写入定稿 |
| 去除描述句子的**结尾句号** | 加载或对齐 `yunxiao-requirement-lifecycle` |

云效建单与推进由 **`$YunxiaoPMapp`** 负责；本 Skill 只出标题与描述清洗稿 / 已确认定稿。

## 何时使用

- 口令含 `AutoRDO` / `清洗聊天` / `录音整理` / `原始诉求`
- YunxiaoPMapp「记录需求」前，材料为聊天/录音/口述碎片时**必须先**跑本 Skill
- 一次粘贴多条待入库诉求（清单、表格行、编号列表等）时，自动批量拆解
- 口令含 `确认待确认` / `AutoRDO 确认` / `逐条确认` / `消解待确认` → 进入待确认 Plan 确认

## 输入

- 粘贴的聊天记录、会议速记、口述碎片
- **多行数据**：每行一条、编号列表、表格列、空行分隔的多条诉求等
- 录音**转写文本**（优先）
- **确认阶段补充**：选择题选项、或一段需求描述/功能规则用于消解待确认
- 仅有音频文件、无转写时：说明需先转写后再清洗（**不**内嵌 ASR、不索要密钥）

## 处理规则

**强制前置**：清洗 ONE-OS / 羚牛相关材料前，**必须先 Read** [references/oneos-domain.md](references/oneos-domain.md)（部门标准名、五条线模块、闭环与故事点摘要），再按 [references/rules.md](references/rules.md) 执行。摘要：

1. **多条拆解（优先判断）**：若输入明显为多条独立诉求（多行、编号/项目符号列表、表格多行、空行分段等），先按条拆分，再对**每一条**分别做标题与描述转译；输出多份 `## 原始诉求（AutoRDO）`（可用 `### 1/2/3…` 编号）。同一条需求内部的多行说明**不要**拆开  
2. **OneOS 对齐**：模块名、部门名、条线归属与业财关键词以 `oneos-domain.md` 为准；口语映射到标准名；不脑补材料未出现的故事点细节；**勿**把词典全文写入输出稿  
3. **标题提炼**：根据材料理解，提炼简炼、清晰的需求标题（准确覆盖业务模块与核心诉求/动作，表达自然干炼；剔除口语废话与长句直抄，不强求死板的特定后缀拼接）  
4. **描述转译**：原文的转译结果，保留原意与业务事实，转换为规范书面表达；不升格、不脑补方案细节  
5. **去除口语**：去掉嗯/啊/那个/然后呢等口头禅，合并自我修正  
6. **格式规范**：轻度分段或条目，**去除结尾句号**（问号/叹号按语义保留）  
7. **标注待确认**：缺信息写「待确认：…」，不假装已确认  
8. **待确认逐条确认（可选第二阶段）**：详见 [references/confirm-pending.md](references/confirm-pending.md)。有待确认且用户要确认时：`SwitchMode` → **plan** → 按需求条号逐点确认；**优先出选择题**（选项用词典辅助）；也支持用户粘贴补充描述一次消解多点 → 回填定稿  

## 两阶段流程

```text
阶段 A（清洗，默认可不进 Plan）
  输入碎片/多行 → 拆条 → 标题+描述+待确认

阶段 B（确认，强制 Plan）
  确认待确认 → 逐条选择题 / 文字补充 → 回填已确认定稿
  →（用户另嘱时）再交 YunxiaoPMapp 记录需求
```

## 输出

### 单条（阶段 A）

```markdown
## 原始诉求（AutoRDO）

**标题**：<清晰简洁的需求标题>

**描述**：
<原文的转译/清洗结果；无结尾句号>

待确认：
- …
```

### 多条（阶段 A · 自动拆解）

先给一行总览（条数），再按序输出多份；每份结构与单条相同。

### 已确认（阶段 B）

```markdown
### n（已确认）

## 原始诉求（AutoRDO）

**标题**：…

**描述**：
<初稿 + 已确认信息；无结尾句号>

待确认：
无
```

用户确认定稿后，再交 YunxiaoPMapp：可按条分别 `记录需求：标题=…；描述=…`（本 Skill 仍不建云效单）。

## 口令

```text
AutoRDO：<粘贴聊天或转写>
AutoRDO：录音转写如下 …
AutoRDO：<多行粘贴，每行一条诉求>
确认待确认
AutoRDO 确认：从第 1 条开始
按下列补充消解待确认：
<粘贴补充说明>
```

- **仅清洗出稿** → 不必进 Plan  
- **消解待确认 / 回填定稿** → **必须**进 Plan  
