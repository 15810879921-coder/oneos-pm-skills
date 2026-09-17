# 需求级测试计划与开发任务范围执行

## 口径

- 测试计划按**需求**建立，需要时配置正式 TestHub 计划。
- 每个非取消【开发】任务都必须唯一对应一个【测试】任务；二者同属源【交付】并关联同一需求。
- 是否存在正式计划只决定用例来源，不决定是否创建【测试】任务。无正式计划使用`mandatory-test-task`。
- 测试任务完成是发版红线；没有Bug不能替代测试任务完成。
- “成功读取后确认无关联计划”和“测试计划读取失败”是两个独立结论。不得把读取失败写成没有计划。

## 可识别计划与范围

默认自动匹配只接受测试计划名称含精确需求编号，例如`ONEOS-536｜任务工单测试`。旧计划未写需求编号时，必须由测试人员提供唯一`testPlanId`，不得按标题相似猜测。

正式计划中的结果目录以以下前缀声明范围：

```text
[Web] 任务工单/台账展示
[小程序] 任务工单/移动端
[跨端] 任务工单/端间联调
```

`PC`归为`Web`。一个目录只能属于一个范围；没有端侧前缀的目录不自动纳入任一端。计划存在但当前端没有可识别目录时，记录`scope-unconfigured`；目录存在但没有正式用例时记录`scope-empty`。两种情况都创建`mandatory-test-task`测试任务并报告计划配置缺口；不得猜测或更新整份计划的用例结果。

## 完成开发分流

1. 每个完成开发任务都调用`yunxiao_cli_test_scope.py resolve`，传入需求编号、开发任务编号和端侧。
2. 首次读取测试计划失败且属于服务端5xx、超时、连接失败、命令/能力缺失或已知Content-Type兼容问题时，只更新`aliyun-cli-devops`插件并自动重试一次。鉴权、权限、参数、项目或数据冲突不得升级后跳过，仍直接阻断。
3. 插件升级后读取成功时，保存升级前后版本和首次错误；继续按真实计划数据判定，不把首次失败当成无计划。
4. 插件升级命令失败时也要继续执行一次读取重试；升级命令失败或升级后重试仍失败时，记录`plan-read-skipped`、升级结果、升级前后版本、升级错误、两次读取错误和traceId，跳过本次正式TestHub计划/用例验证，并在最终输出明确披露。该分支仍创建独立`mandatory-test-task`并保留测试任务完成发版红线，不得写成“确认无计划”或“测试通过”。
5. 成功读取后没有与需求精确关联的正式计划时，记录`no-associated-test-plan`并跳过正式TestHub计划/用例验证；仍创建`mandatory-test-task`，由QA按需求验收点执行并记录结果。
6. 有精确正式计划、端侧目录和非空具体用例时使用`formal-plan`；开发完成只读取、去重并冻结`directoryIds`与`selectedCaseIds`，不更新 TestHub 结果。
7. 计划读取成功但端侧目录未配置或目录内没有正式用例时使用`mandatory-test-task`并记录对应配置缺口；仍创建测试任务，不伪造计划或用例。
8. 创建或复用测试任务时以`项目ID+需求ID+交付ID+开发任务ID`唯一去重，并写入`oneos.test-scope/v1`。创建前零个则创建、一个则复用、多个则阻塞消歧；创建或复用后的正式回读必须恰好一个有效测试任务，零个或多个才阻塞交接。不得因尚未创建测试任务而拒绝进入创建步骤。
9. 测试任务创建及关系/负责人/描述回读、开发任务完成、需求进入待测试必须按该顺序分阶段落receipt，并由`yunxiao_cli_complete_development.py`统一编排。测试交接未通过时不得关闭开发任务；部分执行必须留下可恢复回执。

`formal-plan`冻结出的具体用例由`YunxiaoQA`通过正式TestHub适配器执行和写回；开发侧验证只证明代码可交测，不得代替测试人员把用例标为通过。

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
