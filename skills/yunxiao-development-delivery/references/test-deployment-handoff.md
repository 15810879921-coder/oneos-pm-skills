# Test部署、迭代与发布修复回流

## 端侧分流（产品确认）

先回读源`【交付】`端侧标签：

| 标签 | 开发自测 / 完成复验 | 交测 test 流水线 |
|---|---|---|
| `Web`（`PC`视为`Web`） | 必做 | 必做，写`oneos.test-deployment/v1` |
| `小程序` | **跳过** | **跳过**；写`deliveryEnd=小程序；testPipeline=skipped` |

混端或无端标签 → 阻塞。

## 正常需求提测门禁

当前开发范围取得可信交付版本并被`test-scope-aggregation.md`判为`formal-plan`后，即可创建或复用该范围正式【测试】任务；不得等待同需求的兄弟开发任务。普通模式使用已合并版本；隔离快速模式使用`oneos.rapid-delivery/v1`记录的远端源提交。迭代不是提交、推送、MR创建/合并、实际工时、开发任务完成或测试任务创建的前置条件；只在正式测试范围交接时，从源【交付】正式关系反查。随后：

1. 从源【交付】正式关系反查唯一非关闭迭代；不得读取或使用开发任务/MR的`sprint`字段，也不得用聊天文本、标题相似或默认迭代代替。无迭代、多个候选、跨项目或关系冲突时，保留已合并开发任务及已创建测试任务，需求保持`开发完成`；仅暂停测试部署与`待测试`，交回`$YunxiaoPM`关联该源【交付】到目标迭代。
2. **Web**：按每个适用Codeup仓库的精确代码源和目标分支反查已经创建好的Flow流水线；名称必须带`test/测试`且不带`prod/生产`。每条不同流水线最多启动或关联一次，禁止创建、复制、更新或重命名流水线。**小程序**：不发现、不启动test流水线。
3. **Web**：证明部署版本包含本需求所有必需Commit/MR；隔离快速模式必须精确包含开放MR的远端源提交。只收到流水线提交成功、运行中、未知或环境不符均阻塞。**小程序**：跳过本步。
4. 在【测试】描述中幂等写入并回读：

**Web：**

```html
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_START -->
<!-- {"schemaVersion":"oneos.test-deployment/v1","projectId":"...","iterationId":"...","iterationName":"...","requirementId":"REQ-1","testTaskId":"TEST-1","executionId":"EXEC-1","environment":"test","status":"success","deployedVersion":"commit-or-artifact","includedChanges":["MR-or-commit"],"evidenceUrl":"...","completedAt":"ISO-8601","idempotencyKey":"test-deploy-..."} -->
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_END -->
```

**小程序：**

```html
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_START -->
<!-- {"schemaVersion":"oneos.test-deployment/v1","projectId":"...","iterationId":"...","iterationName":"...","requirementId":"REQ-1","testTaskId":"TEST-1","deliveryEnd":"小程序","testPipeline":"skipped","status":"skipped","reason":"小程序交付按规则跳过test流水线与开发自测","completedAt":"ISO-8601","idempotencyKey":"test-deploy-skip-miniprogram-..."} -->
<!-- ONEOS_TEST_DEPLOYMENT_EVIDENCE_END -->
```

5. **Web**：成功部署区块必须与从源【交付】反查的正式项目、迭代、需求、测试任务和范围一致并回读成功。**小程序**：跳过区块与该正式迭代回读成功即可交接。向YunxiaoQA交接时必须携带迭代ID、端侧范围和计划目录；首个正式范围由QA推进需求进入`测试中`，不得把它误写成“全需求待测试”。

## 发布/验收失败开发回流

```text
$yunxiao-development-delivery
处理发布回流：发版任务=TASK-900
```

1. 精确读取发版任务的生产事件或产品验收不通过证据、回滚状态、受影响需求和迭代。
2. 只接受YunxiaoQA已建立且带同一回流批次ID的Bug；若没有正式Bug，零代码写入并交回`接收发布回流`。
3. 冻结当前开发可处理Bug集合，按现有批量修复规则修改、验证并按仓库+分支统一提交；保留逐Bug代码归属。
4. 所有分组合并后：**Web**按涉及仓库执行各自已创建的test流水线；相同流水线去重后只执行一次，并以组合证据证明部署版本覆盖全部回流修复。**小程序**跳过test流水线，在回流交接中注明`testPipeline=skipped`。
5. 将每个成功包含的Bug改为`已修复`，保持验证者不变；不关闭Bug、不写复测通过。
6. 输出：

```text
$YunxiaoQA
验证发布回流：发版任务=TASK-900；缺陷=BUG-1,BUG-2；回归证据清单=<JSON文件>
```

开发侧不得直接调用`重新发布`，不得把原生产回滚成功当成修复成功，也不得修改需求、交付或产品验收状态。
