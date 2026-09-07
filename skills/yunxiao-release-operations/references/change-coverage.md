# 提交完整性与实际内容核对

准备发布与执行发布共用 `scripts/validate_release_change_coverage.py`。保留已有组件矩阵、计划修订、部分合并续跑和发布授权边界。本文不新增业务口令或发布权限。

## 准备发布：先查全，再决定范围

1. 通过正式关系从源交付找到开发任务及其分支、关联修复缺陷。交付是汇总节点，不创建也不拥有业务分支。只有无关联工作项的独立缺陷可以作为独立缺陷分支所有者；有测试、需求或交付关系时先追踪开发链，不能降级新开 fix。发布候选分支是执行产物，与业务分支所有者分开。
2. 从官方 Codeup/Flow 核验仓库、目标分支及其 HEAD，冻结完整源 SHA 与目标基线 SHA；分支已删除时可用有证据的 MR 源 SHA。每个源运行：

```text
skill-run validate_release_change_coverage.py collect --repository-id <仓库ID> --source-head <完整源SHA> --target-base <完整目标SHA> --output <history.json>
```

采集器通过本 Skill 官方 CLI 网关按 SHA 读取源和目标的提交历史，每页最多 100 条，读至空页，不使用日期、标题、路径过滤。它检查分页、父关系、HEAD 可达性；任何源记录遗漏都不能靠 `sourceHistoryComplete=true` 补齐。返回数据只含读取参数、提交 ID 和父关系，不保存凭据。网络/权限失败保留已有计划，恢复后重采集；不能改写“已完整”声明继续。

3. 将采集结果原样放入 source 的 `historySnapshot`。源新增 `branchOwner`：

```json
{"type":"development_task","workItemId":"开发任务内部ID或精确编号","relationEvidenceId":"正式关系读回定位"}
```

独立缺陷用 `type=independent_bug`，且 `relatedWorkItemIds=[]`；必须来自独立分支形成时或追加本次发版汇总关系前的官方关系证据，不能据标题或分支名填写。发布自身追加的汇总关系不反向否定已有独立分支；后来认领到开发任务的分支沿已核验认领关系记录 owner，不新开或改名。现有 `sourceWorkItemIds` 仍表示发布来源汇总，不重解释为 owner。

4. 对源可达、目标不可达的每个提交填 `sourceCommitHistory`。每条保留 `commitId`、`include`、`evidenceId` 及归属；纳入项与 `exactCommitIds` 一致。排除项写 `reason=out-of-scope` 并提供具体变更/正式关系证据。历史序列仍按父先子后排列，末项对应 sourceHead；pure 源不能隐藏排除项。原 `sourceHistoryComplete`、`sourceHistoryEvidenceId` 字段保留兼容，但不替代 `historySnapshot` 的实质验证。
5. 检查实现引用、变更内容、正式范围和测试证据，识别必要前置实现，用 `requiresCommitIds` 记录。脚本检查这些依赖是否纳入或目标已有；它不能从父关系、标题或编译成功推断完整业务依赖。不确定时系统先补查具体引用和变更，仍无法证明才报告受影响仓库的明确缺口，不让开发例行筛候选。跨来源的同仓库依赖也必须在本仓库选集内。
6. 经内容证据确认的 squash/cherry-pick 等价改动仍是本次必要变更，写 `include=true, reason=target-equivalent`；执行时检查目标实际内容，不能因 SHA 不同重复重放，也不能因为曾合入而忽略撤销。它按干净候选路径核验。已有 SHA 祖先路径用 contained，但仍需要目标内容核对。
7. 多父合并提交需要明确 `replayParent`，必须是官方父节点之一，并记录选择该父节点的范围理由。MR 补丁集各版本是快照线索；只按冻结源版本的可达图纳入，不能把 rebase 前废弃版本全量并入。
8. 运行原计划生成器。新计划 `coverageVersion=1` 保存原始历史证据、owner、逐项处置及 `replayOrder`。SHA 排序只用于集合表示；干净候选必须按 `replayOrder` 重放，不能按 `exactCommitIds` 排序。跨源重叠提交去重，必要依赖和父节点先行。

## 执行发布：核对候选，再核对目标

每个仓库需要一份包含冻结源、目标基线对象的本地 Git 对象库。候选/新目标提交无需先拉到本地：命令默认通过官方 `codeup-list-files --ref <精确SHA>` 读取根目录，各子目录的 Git tree 标识递归约束其全部内容，直接计算实际根树标识。远端事实仍只用官方 Codeup CLI；本地 Git 只计算已有源补丁与预期树，不允许借本脚本 fetch/clone 云效远端，也不改当前索引、工作区或分支。源/基线对象缺失时先定位已有完整本地仓或用官方证据补齐；无法补齐时保留续跑点，不将内容核对写成通过。

```text
skill-run validate_release_change_coverage.py verify-tree --plan <merge-plan.json> --repository-key <仓库ID|组件|目标分支|部署目标> --repository <本地Git目录> --revision <官方已回读候选SHA> --output <candidate-coverage.json>
```

含竖线的 repository-key 在 shell 中须整体加引号。核验器验证计划哈希及官方父关系，在临时 Git 仓库/索引中从冻结基线重放精确补丁，将预期根树与官方实际根树比较；检查增加、修改、删除、重命名、二进制和文件模式。只有最终内容完全一致才生成核验结果，官方根目录记录保存在 `officialTreeRead` 内。离线测试可用 `--local-only` 从本地提交取实际树，此结果不替代正式执行的官方读回。不会调用 Git 网络、checkout、merge 或生产流水线。

`target-equivalent` 及已在目标祖先链中的选定提交，先用反向补丁检查当前基线中的内容仍存在。后续合法修改导致旧补丁无法独立证明时会报告需要补证/修订，不能把失败当作“代码必然缺失”，更不能盲目重放或重试；本实现不自动裁决复杂语义等价。无冲突重放失败时同样保留双方代码和旧证据，按已有授权/修订规范处理。

执行状态机的调用约束：

- `init` 重新验证完整计划与哈希。旧 READY 计划没有新历史证据时，先补查并生成下一版本，不能直接执行或原地覆盖旧计划。历史已终态发布不迁移、不重跑。
- `preflight` 的每仓库行继续带现有测试、依赖及可合并检查，并增加 `currentTargetCommit`。未合并仓库还需 `candidateRevision` 与完整 `candidateCoverage` 对象；已合并/contained 仓库需 `targetCoverage`。实际目标必须等于冻结基线或该仓库已记录的结果 SHA。
- 调用 preflight 前，经官方网关实时回读源/目标/MR，将这些读取加入实际合并事务的 guards；核验结果哈希只证明内容一致性，不是官方签名或实时状态证明。不能用缓存核验结果替代写前官方漂移检查。
- 合并成功后官方回读目标新 SHA，对该 SHA 再运行同一个 `verify-tree`，用 `record-merge --status success --target-commit <SHA> --coverage <target-coverage.json>` 记录。缺失核验结果不能记录合并成功。
- 若真实合并已经发生但内容核验失败，立即保存真实目标 SHA 和差异证据，以 failed 记录该仓库，保持部署未启动；后续重新读取目标、修订计划或按已授权的新 MR 处理，不能抹掉已发生的合并，也不能把旧基线不匹配简单重试成成功。
- 只有所有仓库目标内容核对通过才允许 `start-deployment` 状态动作。它本身不启动流水线；正式生产调用仍受原发布尝试和授权门禁约束。

核验结果绑定 planHash、repositoryKey、targetBaseCommit、revision、expectedTree、actualTree、proofHash。重放结果变更、计划修订或版本漂移都须重算，不能只更改通过标志。准备、执行使用同一套内容核验代码；小程序跳过规则保持原样。
