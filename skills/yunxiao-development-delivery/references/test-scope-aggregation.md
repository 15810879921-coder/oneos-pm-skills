# 需求级测试计划与开发任务范围执行

## 口径

- 测试计划按**需求**建立，需要时配置正式 TestHub 计划。
- 每个非取消【开发】任务都必须唯一对应一个【测试】任务；二者同属源【交付】并关联同一需求。
- 是否存在正式计划只决定用例来源，不决定是否创建【测试】任务。无正式计划使用`mandatory-test-task`。
- 测试任务完成是发版红线；没有Bug不能替代测试任务完成。

## 可识别计划与范围

默认自动匹配只接受测试计划名称含精确需求编号，例如`ONEOS-536｜任务工单测试`。旧计划未写需求编号时，必须由测试人员提供唯一`testPlanId`，不得按标题相似猜测。

正式计划中的结果目录以以下前缀声明范围：

```text
[Web] 任务工单/台账展示
[小程序] 任务工单/移动端
[跨端] 任务工单/端间联调
```

`PC`归为`Web`。一个目录只能属于一个范围；没有端侧前缀的目录不自动纳入任一端。计划存在但当前端没有可识别目录时，记录`scope-unconfigured`，创建`mandatory-test-task`测试任务并报告计划配置缺口；不得猜测或更新整份计划的用例结果。

## 完成开发分流

1. 每个完成开发任务都调用`yunxiao_cli_test_scope.py resolve`，传入需求编号、开发任务编号和端侧。
2. 有精确正式计划及端侧目录时使用`formal-plan`；只执行当前端被选中的真实测试用例，真实执行后才更新 TestHub 结果。
3. 没有正式计划或端侧目录未配置时使用`mandatory-test-task`；仍创建测试任务，由QA按需求验收点执行并记录结果，不伪造计划或用例。
4. 创建或复用测试任务时以`项目ID+需求ID+交付ID+开发任务ID`唯一去重，并写入`oneos.test-scope/v1`。同一开发任务出现零个或多个有效测试任务都属于阻塞。
5. 测试任务创建及关系/负责人/描述回读、开发任务完成、需求进入待测试必须按该顺序分阶段落receipt，并由`yunxiao_cli_complete_development.py`统一编排。测试交接未通过时不得关闭开发任务；部分执行必须留下可恢复回执。

`oneos.test-scope/v1`至少包含`requirementId`、`deliveryId`、`developmentTaskId`、`deliveryEnd`、`scopeId`、`testMode`、`testPlanId`、`directoryIds`、`selectedCaseIds`、交付版本和幂等键。它不是给人看的任务正文，必须按以下格式隐藏写入，JSON使用紧凑单行，重试时只替换这一个区块：

```html
<!-- ONEOS_TEST_SCOPE_START -->
<!-- {"schemaVersion":"oneos.test-scope/v1","requirementId":"...","deliveryId":"...","developmentTaskId":"...","deliveryEnd":"Web","scopeId":"...","testMode":"formal-plan|mandatory-test-task","testPlanId":"...|null","directoryIds":["..."],"selectedCaseIds":["..."],"deliveryVersion":"...","idempotencyKey":"..."} -->
<!-- ONEOS_TEST_SCOPE_END -->
```

不得使用`<pre>`包装受管JSON，也不得把它与`## 开发交接`正文拼接为`<br/>`文本。旧`oneos.lightweight-verification/v1`只读保留，不能替代测试任务或满足发布门禁。

## 需求级聚合

需求进入`测试中`的条件是第一个测试任务开始执行，不等待兄弟开发任务。需求进入`测试完成`仅在所有非取消开发任务均有唯一测试任务且全部闭环时：

- `formal-plan`：测试任务已完成，所选用例无失败、阻塞、未执行；版本一致；该范围缺陷已关闭或有正式暂不修复批准。
- `mandatory-test-task`：测试任务已完成，验收结果与交付版本一致，且无未决阻断缺陷。
- `跨端`范围：所有前置端已闭环后，跨端用例也已闭环。

开发侧不得把需求直接写为`测试完成`。该状态只能由QA在全量读取非取消开发任务与对应测试任务后聚合推进。任何缺失、重复、未完成或仍使用旧轻量模式的测试映射都必须阻断发版。
