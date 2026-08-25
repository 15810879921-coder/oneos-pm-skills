# 已确认开发约束

知识版本：`3`
最后审计：`2026-08-25`
来源：TODOS-26 的联动契约与 2026-08-25 通用性瘦身审计。

本文件仅保留不依赖单次项目快照的 confirmed 约束。项目规则、构建配置和工作区状态以目标仓实时资料为准。

## 调用边界基线

```text
ID：DB-C-001
状态：confirmed
适用范围：调用 $yunxiao-development-delivery 的全部动作；仅约束开发大脑联动
规则或复盘：在任何代码或外部系统写入前完成开发大脑预检；只有范围匹配、未冲突的 confirmed 记录可作为强制约束。
证据来源：TODOS-26 已确认目标；yunxiao-development-delivery/SKILL.md 联动契约（2026-08-24）
验证：由调用方输出开发大脑预检回执并在最终回执记录规则 ID 或无匹配理由。
记录日期：2026-08-24
复核触发：调用协议、知识模型或目标 Skill 入口变更
冲突/过期处理：协议变更时标记 superseded，不静默删改。
```

```text
ID：DB-C-002
状态：confirmed
适用范围：开发大脑的知识记录与全部联动动作
规则或复盘：未确认经验只可作为 candidate 或 pending；不得作为代码、Git、云效、流水线或生产写入的强制依据。
证据来源：TODOS-26 已确认安全边界；development-brain/references/knowledge-governance.md
验证：预检仅列出 confirmed 记录；结束复盘在证据不足时输出无可沉淀候选。
记录日期：2026-08-24
复核触发：何斐调整确认口径或证据标准
冲突/过期处理：发生冲突时标记 conflicted 并等待裁决。
```
