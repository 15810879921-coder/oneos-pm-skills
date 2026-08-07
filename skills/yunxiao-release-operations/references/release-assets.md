# 发布组件矩阵

`执行发布`不是“重启前端”的同义词。只部署本次正式范围内实际有代码变更的组件；前端、后端、Cloud、网关和独立服务均按自己的仓库、目标分支、制品和生产流水线处理。没有代码变更的组件写`无需部署`，不得为凑齐流程无意义重启。

准备发布、执行发布、执行回滚、重新发布和查询发布只读取生产流水线。测试流水线、测试部署和名称含`test/测试`的定义完全不参与发布组件矩阵；它们仅由显式`执行测试流水线`命令读取。

## 合并来源

常规迭代发布只允许下列链路：`已测试通过的 feature/* 或 fix/* → release/<迭代名称> → master → 生产流水线`。

- `release/<迭代名称>`必须从当时最新`master`创建；例如本期为`release/ONEOS_V1.4.1`。
- 只纳入冻结范围中已测试通过需求/缺陷的MR或精确提交；逐条保存源分支、MR、提交和测试证据。
- `develop`是开发集成分支，绝不能合并到`master`作为正式发版来源，也不能作为生产流水线源。
- 没有现成`release/*`时，先报告“待创建发布候选分支”；除非用户明确授权，不创建分支、不合并、不推送。
- 紧急热修复可用`hotfix/* → master`，但必须由用户明确说明是热修复；不得借此混入常规迭代内容。

## 准备发布时冻结

从每个正式`【交付】`及关联的开发/测试任务、需求完整描述、Codeup MR/提交或可读取制品记录提取代码资产。每一行必须包含：

```json
{"component":"web|gateway|cloud-service|自定义服务名","repository":"仓库","releaseBranch":"release/ONEOS_V1.4.1","targetBranch":"master","changeEvidence":"release分支→master的MR/commit/制品ID","pipelineId":"生产流水线ID","pipelineName":"名称","deployTarget":"目标","logicalReleaseEnvironment":"prod","dependencyOrder":1,"deployRequired":true}
```

- `deployRequired=true`：该仓库或服务有本次变更；必须先确认对应的`release/<迭代名称>`只含已测范围、且已合并至`master`，再唯一映射到源分支同为`master`的活动生产流水线。`develop`、特性分支或仅“准备合并”的MR均不通过。
- `deployRequired=false`：明确没有本次代码变更；保留原因，不启动、不重启。
- 一个流水线可覆盖多个组件时按`pipelineId`合并为一条执行，但账本仍列出它覆盖的组件。
- 代码资产、合并证据或流水线映射无法唯一确认时，`执行发布`停止在该组件，不猜测“只发前端”或把其他服务视为无需部署。

## 执行与完成

1. 先回读每个`deployRequired=true`组件的`release/<迭代名称>`来源、已测试提交、`master`已含本次合并，以及流水线仓库、源分支=`master`、部署目标和运行参数。任何一个组件不满足即不启动该发布尝试，也不得把它改算成“仅前端发布”。
2. 按`dependencyOrder`执行；默认后端/Cloud/网关在前、前端在后，但仅在正式依赖或流水线定义可读时采用，无法判断则请求最少必要顺序。
3. 在同一个`releaseAttemptId`中为每条实际生产执行写入`productionExecutions`，每条至少含`component`、`pipelineId`、`pipelineName`、`executionId`、`status`和`logicalReleaseEnvironment`。旧账本的`productionExecutionId`仅兼容读取，不能证明多组件发布完整。
4. 任一必发组件失败、阻塞或未启动，都不得写`发布完成`；只对已实际部署且具备保存回滚信息的组件执行对应回滚，不猜测跨服务回滚。
5. 只有所有必发组件终态成功且环境/范围回读一致，才形成技术`发布完成`。
