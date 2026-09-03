# 意图 Taxonomy 输出模板（intent-taxonomy）

> 分析员产出 MD 时按本模板填写。示例成品见  
> `src/resources/customer-fault-knowledge-base/corpus/wecom-group-fault-intent-by-part-2026-08-25.md`

---

## 文首元数据

| 项 | 内容 |
|---|---|
| 文档版本 | vX.Y.Z |
| 语料来源 | 体微绘画存档 · N 个 Excel（导出日期） |
| 原始消息总量 | N 条 |
| 客户故障相关 utterance | N 条（去重后 M 条） |
| 用途 | 企微故障机器人意图精准判断 · 向量入库 `customer-fault` |
| 对齐 | `dict.ts` · `fcev-customer-report-lexicon.md` · `utterance-to-fault-exec.md` |

---

## 每个意图条目（INT-XXX）

```markdown
### INT-001 · {子类型名称}

| 字段 | 值 |
|---|---|
| intentId | `INT-001` |
| part | `{部位}` |
| faultType | `{现网 FAULT_TYPES 枚举}` |
| sceneId | `S0X`（可选，对齐语料卡） |
| fdCandidates | `FD-0XX`（可选，weak/strong） |
| realCorpusCount | N |
| defaultSeverity | `P0|P1|P2|P3` |
| slotsHint | 车牌, 现象描述, 位置, … |

**真实语料（群聊原文）**
- 「…」

**模拟变体（用户口语扩展 · 供召回）**
- 「…」

**规则关键词（regex 片段）**
- 主触发：`…`
- 辅触发：`…`

**negativeExamples（勿误判）**
- 「…」
```

---

## 必含章节

1. **使用说明** — 匹配顺序、多部位、排除项  
2. **部位总览表** — part / faultType / 子类型数 / 语料条数  
3. **分部位详述** — 每子类型一条 INT  
4. **负例** — 勿判为车辆故障建单  
5. **待人工复核** — 未自动归类 utterance  
6. **关联文件**

---

## 质量闸

- 每条意图 ≥2 条真实或模拟 utterance  
- `faultType` 必须来自 `dict.ts` `FAULT_TYPES`  
- Excel「解决方案」只进 `solutionInternal`，**禁止**写入 aliases  
- 加氢站停业/发票/GPS 等噪声进 negativeExamples，不进真实语料
