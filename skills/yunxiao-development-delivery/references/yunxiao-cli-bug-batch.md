# 云效CLI批量Bug端到端适配器

## 1. 适用范围

批量命令中的云效平台动作必须全部通过官方`aliyun devops` CLI执行：

1. 通过PAT解析当前用户；
2. 按精确项目ID查询当前用户负责、需要开发处理的Bug；
3. 并发补读Bug详情、正式关联项和外部代码关系，生成冻结快照；
4. 将快照内明确指定的Bug改为项目真实`处理中`或`已修复`；
5. 每次状态写入后回读编号、状态、负责人和验证者。
6. 查询Codeup代码库、分支和MR；
7. 创建或复用精确分支，创建或复用MR，合并并回读`mergedRevision`；
8. 回读实际MR合并版本，并核验每个Bug的开发验证报告和提交版本；
9. 写入已修复及待部署、待交付测试记录；
10. 回读Bug状态、描述、负责人和验证者；不读取、触发或等待Flow。

代码编辑、编译测试、`git commit`和`git push`是本机Git动作，不属于云效OpenAPI；仍在隔离工作区执行。分支/MR/合并和Flow查询执行属于云效动作，禁止再通过浏览器、DOM或Cookie执行。本文件只定义批量Bug命令；`分配任务`另按`yunxiao-cli-allocation.md`执行。

## 2. CLI和凭证门禁

要求：

- 阿里云CLI可执行；
- 已安装`aliyun-cli-devops`专用插件；
- `aliyun devops version`成功；
- PAT只通过`ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`提供；
- 中心版设置`ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`；
- Region版设置`ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`；
- 口令或已验证上下文提供一个或多个精确项目ID。

禁止把PAT写入命令参数、Skill、仓库、快照、日志或聊天。CLI、插件、认证或范围门禁失败时全批停止，不得静默回退浏览器、DOM或Cookie写入。

适配器只能输出仓库、分支、MR和流水线的必要摘要。不得回显流水线完整配置、Webhook、访问签名、下载签名、密码或密钥字段。

## 3. 预检

```text
skill-run yunxiao_cli_bug_batch.py doctor --require-auth
```

只回报CLI版本、插件版本、凭证变量是否存在以及当前用户ID/名称；不输出PAT。

## 4. 冻结快照

```text
skill-run yunxiao_cli_bug_batch.py snapshot --space-id <项目ID> [--space-id <项目ID>]
```

默认可处理状态：`待确认`、`待处理`、`处理中`、`再次打开`、`重新打开`。通过`--actionable-status`可显式覆盖，但不得加入`已修复`、`已关闭`、`已取消`或归档状态。

脚本把完整快照写到系统临时目录，并在标准输出返回快照路径、当前用户、Bug编号/状态/负责人/验证者和耗时。后续状态修改只接受该文件中的Bug；运行期间新分配Bug不得加入。

## 5. Codeup与Flow只读预检

代码写入前生成交付计划JSON：

先把正式开发关系和逐仓库分支解析结果写成`resolutions`文件，并执行：

```text
skill-run yunxiao_cli_bug_batch.py build-plan --snapshot <快照文件> --resolutions <解析结果JSON> --output <批次计划JSON>
```

解析结果JSON必须同时含`resolutions`和待CLI核验的`testPipeline`。脚本生成可直接交给`yunxiao_cli_bug_delivery.py preflight`的v2计划、稳定`bugBatchId`，按`仓库+源分支+目标分支`分组，并为每个Bug保留独立`retestIdentity`。`associationMode=development_task`必须带唯一开发任务；`associationMode=independent_bug`表示没有开发任务关系。测试任务、需求或交付关系不能把它改判为开发任务分支。

```json
{
  "schema": "oneos.yunxiao-cli-bug-delivery-plan/v2",
  "snapshotPath": "<冻结快照>",
  "groups": [
    {
      "groupId": "frontend-develop",
      "repositoryId": "6316668",
      "sourceBranch": "fix/ONEOS-123",
      "targetBranch": "develop",
      "bugSerials": ["ONEOS-123"],
      "associationMode": "unassociated-fix",
      "deliveryUnitId": "DU-ONEOS-123",
      "branchInstanceId": "BR-6316668-ONEOS-123",
      "baseBranch": "develop",
      "baseCommit": "40位提交ID",
      "baseEvidence": {"verified": true, "evidenceId": "test-deployment-or-integration-readback"},
      "reuseExisting": false,
      "mrTitle": "fix(ONEOS-123): <摘要>",
      "mrDescription": "<修复和验证摘要>"
    }
  ],
  "testPipeline": {
    "environment": "test",
    "params": {}
  }
}
```

执行：

```text
skill-run yunxiao_cli_bug_delivery.py preflight --plan <计划JSON>
```

预检必须证明：

- 每个Bug来自同一冻结快照且只属于一个提交组；
- 每组必须声明`associationMode`：`associated-development-branch`表示Bug唯一关联【开发】并复用已验证开发分支，`unassociated-fix`表示没有开发任务关系的独立Bug。前者必须`reuseExisting=true`且源分支在预检时已存在；后者只能包含一个独立Bug，源分支必须为`fix/<BUG-ID>`。Bug关联【测试】、需求或交付不改变此判断；
- v2计划必须记录`deliveryUnitId/branchInstanceId/baseBranch/baseCommit/baseEvidence`。测试发现Bug优先使用真实被测提交作为基线；无法核验时不得伪造证据，转入临时修复并要求重新部署复测；
- Codeup数字仓库ID、读写权限、目标分支和提交基线可回读；
- 已有源分支仅在`reuseExisting=true`且提交一致时复用；
- 本节点不要求、创建、修改或运行流水线。旧计划中的`testPipeline`仅兼容读取，不构成门禁；

预检输出Codeup分支与基线的带哈希回执，不访问Flow。

## 6. 创建或复用Codeup分支

```text
skill-run yunxiao_cli_bug_delivery.py ensure-branches --preflight <预检回执>
```

适配器重新读取目标分支并核对预检提交。关联开发分支在预检后缺失、变化或不可复用时阻塞，绝不降级创建`fix`分支。无关联Bug才允许创建其计划内的`fix/<BUG-ID>`分支；创建后必须回读精确名称和提交；同名分支被其他提交占用时阻塞。

## 7. 进入处理中并循环修改

逐Bug开始修改前，在确有必要时执行：

```text
skill-run yunxiao_cli_bug_batch.py set-status --snapshot <快照文件> --target 处理中 --serial ONEOS-123
```

适配器重新读取Bug，确认编号、负责人和当前状态仍与冻结范围相容；从该Bug真实项目和工作项类型的工作流中解析唯一目标状态ID；只写`status`，然后回读编号、状态、负责人和验证者。已经是`处理中`时按幂等成功返回。

循环内只修改和验证代码，不提交、不push、不创建MR、不合并、不发布。最后一个Bug完成后，每个`仓库+源分支+目标分支`组在本地最多一次commit和一次`git push`。Git push后生成映射JSON：

```json
{
  "frontend-develop": "0123456789abcdef0123456789abcdef01234567"
}
```

## 8. 通过CLI创建并合并MR

```text
skill-run yunxiao_cli_bug_delivery.py ensure-mrs --branches <分支回执> --commit-map <提交映射JSON>
skill-run yunxiao_cli_bug_delivery.py merge-mrs --mrs <MR回执>
```

`ensure-mrs`先回读Codeup源分支，要求远端40位提交ID与本地映射一致；随后按精确仓库、源分支和目标分支复用唯一打开MR，或通过CLI创建MR并用快照内部工作项ID关联Bug。创建后回读`localId`、仓库、源/目标分支、冲突和WIP状态。

`merge-mrs`只在MR精确、非WIP、无冲突且平台允许时合并，不绕过平台保护。合并前再核对源分支40位提交与验证过的提交映射一致，合并后回读`state=MERGED`和`mergedRevision`。失败结果保留Bug归属，不能遗漏失败仓库后收口。

## 9. 测试部署另行执行

修复完成不启动或等待测试流水线。旧`start-test-pipeline`入口立即拒绝且不写Flow，避免老会话继续自动部署；`check-test-pipeline`只保留历史运行查询。具体交测由独立的`执行测试流水线`命令承担，本版不修改该命令。QA复测/关闭仍须核验实际被测版本包含修复，不能把`已修复`或本地验证当作已部署。

## 10. 合并与开发验证通过后标已修复

保存真实运行的开发验证报告，再计算文件SHA256。每个Bug及其每个仓库分组都必须有唯一验证结果，不能把计划执行或静态扫描冒充业务验证通过：

```json
{
  "schemaVersion": "oneos.bug-development-validation/v1",
  "snapshotHash": "<冻结快照哈希>",
  "results": [{
    "bugSerialNumber": "ONEOS-123",
    "groupId": "frontend-develop",
    "status": "passed",
    "revision": "<实际验证的40位提交SHA>",
    "repairSummary": "<修复内容与验证范围>",
    "reportPath": "validation.log",
    "reportSha256": "<报告文件SHA256>"
  }]
}
```

相对报告路径以清单文件所在目录为基准。验证版本必须是`mergedRevision`，或带`sourceVerifiedAtMerge=true`的合并执行器回执中的`expectedSourceCommit`。历史已合并MR没有源提交核验标记时，验证实际合并版本，不能补造已验证标记。报告原文和本地路径不上传Bug。

```text
skill-run yunxiao_cli_bug_batch.py set-status --snapshot <快照文件> --target 已修复 --merge-evidence <CLI合并回执JSON> --validation-evidence <开发验证清单JSON> --serial ONEOS-123
```

适配器验证回执哈希、快照/用户、Bug及所有分组、报告哈希和版本，并实时回读MR。写入前逐Bug再次核验MR、负责人和验证者；用同一次工作项更新写状态和描述中的`oneos.bug-fix-evidence/v1`受管记录，回读核对。人可读记录含修复内容、验证结果、仓库、目标分支、MR、合并版本，以及`待部署、待交付测试`。原描述保留，不写复测通过、不关闭Bug。`--deployment-evidence`不再被修复完成入口接受。

测试特殊修复请求由`处理测试修复请求：缺陷=<ID>`先消费`oneos.test-bug-repair-request/v1`评论，再进入同一修复链路。若选择不修复，使用`set-status --target 暂不修复 --defer-evidence <证据清单>`；清单必须包含原因、批准人、批准证据和后续动作，适配器追加`oneos.bug-deferred-fix/v1`并回读。QA不得代开发写任一收口状态。

缺少实际合并或有效开发验证时零状态写入；没有流水线运行证据不阻塞。某Bug写入失败只阻塞该Bug，不重复提交或合并。单Bug命令也必须遵循相同证据与记录要求，但不改变单Bug原有“可修复指定负责人Bug”的权限边界；批量适配器仍只操作当前账号快照。

## 11. 输出与续跑

脚本把状态收口回执写到系统临时目录，记录：

- 快照ID和快照哈希；
- Bug编号和内部ID；
- 变更前后状态；
- 负责人和验证者一致性；
- CLI更新及回读结果；
- Codeup分支、远端提交、MR和`mergedRevision`回读；
- 每个Bug的开发验证版本、报告哈希及修复说明；
- 待部署、待交付测试及`qaReady=false`；
- 耗时与错误。

同一合并/验证证据重复执行且状态和描述记录一致时幂等返回，不追加记录或重复合并。已修复单上的不同记录不能覆盖历史交测记录；重新打开后的新修复保留历史区块并追加本轮记录。快照/回执哈希、Bug范围、负责人、验证者、MR身份、分支或版本不一致时停止对应阶段。回读失败先核实现状，不能盲目重试Git或写入。
