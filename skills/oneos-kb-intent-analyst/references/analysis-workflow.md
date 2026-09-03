# 群聊 Excel → 意图 KB · 分析工作流

> 本文件为 `oneos-kb-intent-analyst` 深读参考。默认从 SKILL.md 摘要启动，全量分析时 Read 本文件。

## 0. 目标产物

结构化意图条目，每条可支撑：

- 故障 Bot **意图分类**（fault vs 静默）
- **sceneId** / **faultType** / **candidateFaultDefs** 提示
- 向量检索 **aliases** 与 **negativeExamples**

---

## 1. Excel 入站（体微绘画存档）

### 1.1 常见列（按导出版本猜测，先探表头）

| 可能列名 | 用途 |
|---|---|
| 时间 / 发送时间 | 线程合并窗口（同发送人 ±5–15 分钟） |
| 发送者 / 昵称 | 拆车牌·姓名·手机；判内部/客户 |
| 内容 / 消息 | 主分析字段 |
| 类型 | 文本/图片/语音；图片记 `hasImage=true` |
| 群名称 | 过滤非客户服务群 |

**无表头或乱码**：先读前 5 行推断；仍不明 → 问本尊要列说明，禁止瞎映射。

### 1.2 读取方式

- 小文件（<5000 行）：Agent 可直接 Read xlsx（若环境支持）或用 `xlsx` skill / Python `openpyxl` 转 CSV 再分析  
- 大文件：按日期或群名分 sheet 批处理；每批出 `intent-taxonomy-{batch}-part{n}.md`

### 1.3 预处理

```text
1. 去重：msgid 或 时间+发送者+内容 hash
2. 合并线程：同发送者相邻消息（图→文→@）合成一条 composite utterance
3. 标记角色：外部联系人=客户；@运维 记 signal=want_human
4. 提取媒体：图片消息保留「[图片]」占位 + 若有 OCR 侧车表则合并
```

---

## 2. 噪声过滤（第一遍）

对每条 composite utterance 跑规则 + 轻量语义：

### 2.1 硬丢弃 regex / 关键词（示例）

```text
加氢站.*(营业|休息|停加|价格|地址)
发票|开票|对账|账单|里程.*(目标|达成)
早安|晚安|收到|好的$|^\[表情\]
违章|保养预约|合同|续租
```

### 2.2 硬保留

```text
抛锚|趴窝|无法开|开不了|故障灯|离子水|冷却液|漏气|不给加
什么故障|影响行驶|混动|氢系统.*故障|空调|尾板|漏油|大灯
```

### 2.3 灰区

- 仅 `[图片]` 无文：保留，标 `sceneCandidate=S05`，`needsFollowUp=true`
- 运维长回复：默认丢弃；若含客户引述则只抽客户原话
- 中英混杂故障码：保留原文 + 归一码

输出：`filtered.csv` 元数据列 `{keep|drop|review, dropReason}`

---

## 3. 术语归一（第二遍）

对齐 `fcev-customer-report-lexicon.md` §2：

| 原文模式 | 归一 |
|---|---|
| 清/氢 混写 | 氢 |
| 离只水/离子水 | 去离子水（客户语境） |
| 兆怕/2mp | 2MPa |
| 粤A·GP9331 | 粤AGP9331 |
| 车趴窝/又抛锚 | immobilized + recurrent |

归一写 `normalizedText`；**aliases 保留客户原话**。

---

## 4. 分类（第三遍）

### 4.1 决策树

```text
utterance
 ├─ 安全词（漏气/站拒加/冒烟/高速抛锚）→ vehiclePart=供氢加氢; severity≥P0
 ├─ 失能（抛锚/无法开）→ 燃电/动力 or 电控仪表; scene S01/S09
 ├─ 冷却+自救（加了.*还）→ 冷却系统; scene S03/S04
 ├─ 问句+图 → 电控仪表; scene S02/S06/S11
 ├─ 具名子系统（空调风机）→ 空调上装; scene S08
 ├─ 站拒加 → scene S07
 └─ 其他 → faultType=其他; FD-UNMAPPED
```

### 4.2 映射 FD-*

1. Grep `fault-definition-catalog.md` / JSON 定义名  
2. 读 `utterance-to-fault-exec.md` 已有映射表，避免冲突  
3. 置信度：`exact | strong | weak | none`（见 exec 文档 §1）  
4. **禁止**把 Excel 解决方案文本当匹配依据

### 4.3 聚类合并

- 同一 `vehiclePart + faultType + sceneId` 下 utterance 归一条 intent  
- 变体 ≥3 条才单独建 intent；否则并入最近邻  
- 统计 `frequency` 供 kb-ops 排优先级

---

## 5. 枚举变体（第四遍）

每条 intent 产出：

| 字段 | 说明 |
|---|---|
| `aliases` | 客户原话 verbatim；含错别字 |
| `normalizedAliases` | 归一后（检索用） |
| `negativeExamples` | 易混淆但非本意图 |
| `slotHints` | 车牌/地点/能否行驶/已自救 |
| `dashboardSignals` | 红灯/黄灯/OCR 字 |
| `solutionInternal` | 仅内参；来自 Excel 解决方案列 |

### 5.1 negativeExamples 来源

- 同批 discarded 噪声中与该 intent 词面相近的  
- 已知误触：如「加氢站今天休息」≠ 漏气拒加  
- 办结语句：「好了谢谢」

---

## 6. 输出 MD

按 [`intent-taxonomy-template.md`](intent-taxonomy-template.md) 渲染。

文件命名：`corpus/intent-taxonomy-{YYYYMMDD}-{source-slug}.md`

---

## 7. 可选 JSON 增量

供 kb-ops 合并进 `utterance-to-fault-rules.json`：

```json
{
  "id": "rule-cf-batch-20260826-001",
  "intentKey": "coolant_di_water_selfhelp_fail",
  "vehiclePart": "冷却系统",
  "faultType": "燃料电池系统故障",
  "sceneId": "S03",
  "match": {
    "any": ["离子水加了", "冷却液加了", "灯还在", "电.*往下掉"],
    "all": []
  },
  "candidateFaultDefs": [{ "id": "FD-032", "confidence": "weak" }],
  "negative": ["加氢站", "发票"],
  "updatedAt": "2026-08-26",
  "sourceBatch": "wecom-export-xxx.xlsx"
}
```

---

## 8. 自检清单

```text
- [ ] 丢弃率合理（通常 40–70% 视群质量）
- [ ] 每条 intent 有 sceneId 或显式 OTHER + 理由
- [ ] faultType ∈ FAULT_TYPES
- [ ] 无 solutionInternal 泄漏到 aliases
- [ ] 新 scene 未私自发明（或已标注待产品确认）
- [ ] 交付包已写（SKILL §6.3）
- [ ] 口径疑义已列待法眼项
```

---

## 9. 体微绘画存档备注

- 导出可能含多群；按群名过滤「客户」「服务」「氢能」等白名单  
- 时间戳时区确认（常见 UTC+8）  
- 图片内容本 workflow **不** OCR；有 OCR 侧车表则 merge，否则标 `imageOnly=true`
