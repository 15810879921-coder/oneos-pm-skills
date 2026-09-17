# 云效生命周期 Skill 索引

> 本文件由 `scripts/build-yunxiao-skill-index.py` 从 `docs/yunxiao-lifecycle-skill-index.json` 生成，请勿手工修改。

- 套件版本：`10.2.5`
- 范围：OneOS 云效需求、开发、测试与发布生命周期
- 权威入口：各 Skill 的 `SKILL.md`；本索引只负责定位，不替代运行时规则。

## 生命周期目录

| 顺序 | Skill | 阶段 | 职责 | 口令/规则入口 | 写入边界 |
|---:|---|---|---|---|---|
| 1 | [YunxiaoPM](../skills/YunxiaoPM/SKILL.md)<br>需求任务 | 需求受理、分析设计、正式交棒、产品验收 | 把需求推进到待开发并形成正式产品交棒；发布后完成产品验收。 | [口令](../skills/YunxiaoPM/references/commands.md) | 可写需求、交付、分析、设计及产品验收；不创建开发或测试任务。 |
| 2 | [yunxiao-development-delivery](../skills/yunxiao-development-delivery/SKILL.md)<br>云效开发交付 | 接收交棒、分配、开发、提交、完成开发、缺陷修复 | 从正式产品交棒创建和推进开发任务，形成代码与验证证据，并创建或交接测试任务。 | [口令](../skills/yunxiao-development-delivery/references/commands.md) | 可写开发任务、代码交付记录和测试交接；止于待测试，不执行正式测试或生产发布。 |
| 3 | [development-brain](../skills/development-brain/SKILL.md)<br>知行合一（开发大脑） | 开发前预检、执行中约束、完成后复盘 | 为真实开发动作提供证据化约束和知识路由，由开发意图隐式触发。 | 隐式触发，无独立口令页 | 不执行业务仓、云效或生产写入；只管理通过准入的开发知识。 |
| 4 | [YunxiaoQA](../skills/YunxiaoQA/SKILL.md)<br>测试人员云效 | 接收测试、执行验证、缺陷闭环、完成测试 | 接收测试任务，记录可核验证据，发起和复测缺陷，满足门禁后交接发布。 | [口令](../skills/YunxiaoQA/references/commands.md) | 可写测试任务、测试证据和缺陷状态；不执行生产发布。 |
| 5 | [yunxiao-release-operations](../skills/yunxiao-release-operations/SKILL.md)<br>云效发布运维 | 准备发布、流水线、发布、回滚、重新发布、查询 | 冻结发布范围，校验代码与测试门禁，执行受控生产发布和回滚，并交接产品验收。 | [口令](../skills/yunxiao-release-operations/references/commands.md) | 只在发布门禁通过后写发版任务、生产尝试与发布状态；产品验收由 YunxiaoPM 完成。 |

## 自然语言路由

| 意图 | 负责 Skill | 示例 |
|---|---|---|
| 记录需求、分析设计、交棒开发、产品验收 | `YunxiaoPM` | `记录需求`、`交棒开发`、`刷新产品快照`、`验收通过` |
| 分配、开始、实现、提交、完成开发或修复 Bug | `yunxiao-development-delivery` | `分配任务`、`开始开发`、`提交代码`、`完成开发`、`修复bug` |
| 真实开发动作的预检、约束与复盘 | `development-brain` | `实现功能`、`修改代码`、`调试`、`重构` |
| 开始测试、记录证据、提缺陷、复测或完成测试 | `YunxiaoQA` | `拉取测试任务`、`开始测试`、`发起缺陷`、`完成测试` |
| 准备发布、执行流水线、发布、回滚、重发或查询 | `yunxiao-release-operations` | `准备发布`、`执行发布`、`执行回滚`、`重新发布`、`查询发布` |

## 交接关系

- `YunxiaoPM`：上游 `yunxiao-release-operations`；下游 `yunxiao-development-delivery`。
- `yunxiao-development-delivery`：上游 `YunxiaoPM`、`YunxiaoQA`；下游 `YunxiaoQA`。
- `development-brain`：上游 无固定上游；下游 无固定下游。
- `YunxiaoQA`：上游 `yunxiao-development-delivery`；下游 `yunxiao-development-delivery`、`yunxiao-release-operations`。
- `yunxiao-release-operations`：上游 `YunxiaoQA`；下游 `YunxiaoPM`、`YunxiaoQA`。

## 关键文件

- `YunxiaoPM`：规则 [handoff-gate.md](../skills/YunxiaoPM/references/handoff-gate.md)、[product-handoff-snapshot.md](../skills/YunxiaoPM/references/product-handoff-snapshot.md)、[release-acceptance.md](../skills/YunxiaoPM/references/release-acceptance.md)；执行/校验 [yunxiao_cli_pm.py](../skills/YunxiaoPM/scripts/yunxiao_cli_pm.py)、[handoff_gate.py](../skills/YunxiaoPM/scripts/handoff_gate.py)。
- `yunxiao-development-delivery`：规则 [semantic-routing.md](../skills/yunxiao-development-delivery/references/semantic-routing.md)、[complete-development-executor.md](../skills/yunxiao-development-delivery/references/complete-development-executor.md)、[historical-code-recovery.md](../skills/yunxiao-development-delivery/references/historical-code-recovery.md)、[handoff-gate.md](../skills/yunxiao-development-delivery/references/handoff-gate.md)；执行/校验 [route_lifecycle_intent.py](../skills/yunxiao-development-delivery/scripts/route_lifecycle_intent.py)、[yunxiao_cli_complete_development.py](../skills/yunxiao-development-delivery/scripts/yunxiao_cli_complete_development.py)、[yunxiao_cli_gateway.py](../skills/yunxiao-development-delivery/scripts/yunxiao_cli_gateway.py)。
- `development-brain`：规则 [semantic-evolution.md](../skills/development-brain/references/semantic-evolution.md)、[knowledge-governance.md](../skills/development-brain/references/knowledge-governance.md)、[knowledge-index.md](../skills/development-brain/knowledge/knowledge-index.md)；执行/校验 [select-knowledge.mjs](../skills/development-brain/scripts/select-knowledge.mjs)。
- `YunxiaoQA`：规则 [semantic-routing.md](../skills/YunxiaoQA/references/semantic-routing.md)、[test-execution.md](../skills/YunxiaoQA/references/test-execution.md)、[handoff-gate.md](../skills/YunxiaoQA/references/handoff-gate.md)；执行/校验 [yunxiao_cli_test_lifecycle.py](../skills/YunxiaoQA/scripts/yunxiao_cli_test_lifecycle.py)、[yunxiao_cli_testhub.py](../skills/YunxiaoQA/scripts/yunxiao_cli_testhub.py)。
- `yunxiao-release-operations`：规则 [release-batch.md](../skills/yunxiao-release-operations/references/release-batch.md)、[change-coverage.md](../skills/yunxiao-release-operations/references/change-coverage.md)、[handoff-gate.md](../skills/yunxiao-release-operations/references/handoff-gate.md)；执行/校验 [build_release_merge_plan.py](../skills/yunxiao-release-operations/scripts/build_release_merge_plan.py)、[execute_release_merge_plan.py](../skills/yunxiao-release-operations/scripts/execute_release_merge_plan.py)、[yunxiao_cli_gateway.py](../skills/yunxiao-release-operations/scripts/yunxiao_cli_gateway.py)。
