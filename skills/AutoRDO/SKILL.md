---
name: AutoRDO
description: >-
  AutoRDO (Requirement Description Optimization): cleans fragmented chat logs,
  voice transcripts, and oral notes into written title and description while keeping original
  meaning—extracts title (xxxx模块xxxx功能), translates raw text into written description,
  removes filler/self-corrections/trailing periods; light formatting only.
  Use when user says AutoRDO, 清洗聊天, 录音整理, 原始诉求, or before YunxiaoPMapp
  记录需求. Does not change Yunxiao status or create tasks. Pair with YunxiaoPMapp
  for cloud write; never load yunxiao-requirement-lifecycle.
---

# AutoRDO

**Requirement Description Optimization**（需求描述优化）。  
将碎片化、通俗化文字（多为聊天记录）与录音转写，在**保留原意**前提下自动拆解并提炼为**标题**与**描述**（书面表达），供入库写入云效需求。

## 边界（强制）

| 做 | 不做 |
|---|---|
| 自动提炼标题（格式：`xxxx模块xxxx功能`） | 改云效状态 / 建任务 / 打标签 |
| 清洗措辞、将原文转译为规范书面描述 | 写成完整 AutoPRD 六大块 / 十章 PRD |
| 不确定处标「待确认」 | 臆造未出现的业务结论 |
| 去除描述句子的**结尾句号** | 加载或对齐 `yunxiao-requirement-lifecycle` |

云效建单与推进由 **`$YunxiaoPMapp`** 负责；本 Skill 只出标题与描述清洗稿。

## 何时使用

- 口令含 `AutoRDO` / `清洗聊天` / `录音整理` / `原始诉求`
- YunxiaoPMapp「记录需求」前，材料为聊天/录音/口述碎片时**必须先**跑本 Skill

## 输入

- 粘贴的聊天记录、会议速记、口述碎片
- 录音**转写文本**（优先）
- 仅有音频文件、无转写时：说明需先转写后再清洗（**不**内嵌 ASR、不索要密钥）

## 处理规则

详见 [references/rules.md](references/rules.md)。摘要：

1. **标题拆解**：从原文内容中自动提炼模块与功能，固定格式为 `xxxx模块xxxx功能`
2. **描述转译**：原文的转译结果，保留原意与业务事实，转换为规范书面表达；不升格、不脑补方案细节  
3. **去除口语**：去掉嗯/啊/那个/然后呢等口头禅，合并自我修正  
4. **格式规范**：轻度分段或条目，**去除结尾句号**（问号/叹号按语义保留）  
5. **标注待确认**：缺信息写「待确认：…」，不假装已确认  

## 输出

回报一份拆解与清洗后的整理稿，结构如下：

```markdown
## 原始诉求（AutoRDO）

**标题**：<xxxx模块xxxx功能>

**描述**：
<原文的转译/清洗结果；无结尾句号>

待确认：
- …
```

用户确认后，再交 YunxiaoPMapp：`记录需求：标题=…；描述=…`

## 口令

```text
AutoRDO：<粘贴聊天或转写>
AutoRDO：录音转写如下 …
```

无写云效 → **不必**进 Plan 模式；直接出稿。
