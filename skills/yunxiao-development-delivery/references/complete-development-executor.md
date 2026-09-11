# 完成开发专用执行器

`yunxiao_cli_complete_development.py`只负责代码交付完成后的云效生命周期收口。代码修改、Git提交、推送、MR创建/合并和开发验证仍在前序步骤完成，并以可信交付版本和验证证据作为本执行器输入。

## 为什么需要专用执行器

通用网关能保证单个事务的预检、漂移检查、幂等和回读，但不能保证多个业务事务的固定先后关系。`完成开发`的红线是：测试任务已经可接收测试，开发任务才允许关单。因此必须由专用执行器把多个通用网关事务编排为一条可恢复链路。

执行顺序固定为：

1. `effort`：可选。工时证据完整时创建或更新实际工时并回读；失败或证据不足只记录跳过。
2. `testHandoff`：必选。创建或复用唯一测试任务，设置唯一测试主管，写入开发交接与`oneos.test-scope/v1`，建立并回读`TASK_SUB→源交付`和`ASSOCIATED→需求`。
3. `developmentComplete`：必选。只有上一步完整通过后，才把当前开发任务推进到`已完成`并回读。
4. `requirementDevelopmentComplete`：按实时状态可选。需要遵循工作流中间态时，先把需求推进到`开发完成`并回读。
5. `requirementHandoff`：按实时状态可选。把需求推进到`待测试`；已经是`待测试`或`测试中`时省略，禁止写`测试完成`或由开发侧推进`测试中`。
6. `finalReadbacks`：必选。再次回读开发任务、需求、交付任务、测试任务、负责人、描述和两条关系；只有全部一致才签发`verified=true`完成回执。

测试流水线、测试部署、迭代、正式QA结论和需求`测试完成`不属于本执行器。普通需求提测不因为没有测试流水线而被阻塞。

## 输入计划

计划使用`oneos.complete-development-plan/v1`，套件版本为`10.1.1`。生成计划前必须通过只读CLI冻结以下事实：

- 项目、开发任务、需求和源交付任务唯一；计划同时保存开发任务/需求的内部ID与编号，源交付仍为`处理中`。
- 全部适用仓库已有可信交付版本，Web最终版本验证通过；小程序有规则化跳过证据。
- `yunxiao_cli_test_scope.py resolve`已生成`oneos.test-scope-resolution/v2`回执；其中项目、需求编号、开发任务编号和端侧必须与主计划一致。测试模式为`formal-plan`或`mandatory-test-task`，不得使用`lightweight-verification`。正式计划还必须有唯一计划ID和非空端侧目录。
- 同一`项目+需求+交付+开发任务`只有零个或一个测试任务。
- 当前项目`测试主管`恰好一人，并冻结其用户ID。
- 测试建议和临时需求变更点已能确定；存在影响验收但未确认的变化时不生成写计划。

`stages`中的每项都是`oneos.yunxiao-cli-transaction-plan/v1`通用网关事务。精确operation和参数必须来自当前安装插件的`aliyun devops <operation> --help`，不可照抄历史参数。新建测试任务时，主计划的`scope.testTaskRef`使用完整值`${stage.testHandoff.action.0.id}`；该阶段内的后续动作和回读使用网关自己的完整值`${action.0.id}`。

每个阶段的写白名单是固定的：

| 阶段 | 允许写操作 |
| --- | --- |
| `effort` | `projex-create-effort-record`、`projex-update-effort-record` |
| `testHandoff` | 创建/更新工作项、创建工作项关系或扩展关系 |
| `developmentComplete` | 一个`projex-update-workitem`，目标只能是当前开发任务的`已完成` |
| `requirementDevelopmentComplete` | 一个`projex-update-workitem`，目标只能是当前需求的`开发完成` |
| `requirementHandoff` | 一个`projex-update-workitem`，目标只能是当前需求的`待测试` |

`testHandoff.verifications`必须在阶段内校验测试任务的真实状态、唯一测试主管负责人、完整描述、父交付关系和关联需求关系。把这些校验只放在最终回读会被计划校验器拒绝，因为那样可能先关开发任务、后发现测试任务不可用。

## 运行

```text
skill-run verify_lifecycle_suite.py --skill <名称=SKILL.md绝对路径，五次> --output <套件回读JSON>
skill-run yunxiao_cli_complete_development.py preflight --plan <完成开发计划JSON> --suite-state <套件回读JSON> --output <完成开发预检JSON>
skill-run yunxiao_cli_complete_development.py apply --preflight <完成开发预检JSON> --output <完成开发回执JSON>
```

`preflight`先实时读取`suite-state`中的五个安装路径，要求版本全部为`10.1.1`，再验证总计划并为各阶段生成通用网关计划和预检回执。`apply`会再次实时回读安装路径。任何关键阶段预检失败时零写入；只有可选工时阶段可以标记跳过。

`apply`严格串行执行。每个阶段结束后立即落盘主回执；关键阶段失败时结果为`partial`并记录`failedStage`，后续阶段不执行。再次使用相同预检和输出路径时，已成功阶段不会重复执行，只从尚未完成的阶段继续。若某个通用网关阶段在内部发生部分写入，其网关回执会拒绝盲目重放，需要根据官方当前状态生成新的审核计划。

只有主回执`result=complete`、`verified=true`且最终回读齐全，才能报告“完成开发并已交测试”。代码或MR成功、单个测试任务创建回执、阶段预检或`partial`回执均不代表完成。
