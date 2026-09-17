# 提交后的开发完成判断

用户明确说“提交代码到远端”“推送代码”或等价提交意图时，先完成受控提交和远端版本官方回读，再判断是否继续开发关单。提交成功本身不证明开发完成。

## 判断输入

把当前正式开发任务冻结为`oneos.development-completion-assessment/v1`：

```json
{
  "schemaVersion": "oneos.development-completion-assessment/v1",
  "developmentTask": "ONEOS-983",
  "taskResolution": "unique",
  "scopeMatch": "confirmed",
  "implementation": "complete",
  "validation": "passed",
  "remoteDelivery": "verified",
  "remoteVersion": "commit:abc123",
  "remainingTaskChanges": false,
  "recoveryNeeded": [],
  "candidateCodeRefs": [],
  "knownBlockers": []
}
```

- `taskResolution`来自云效任务与当前分支/提交的唯一关系回读。
- `scopeMatch`来自需求快照、技术方案、验收点和真实代码差异逐项对照；范围冲突必须为`conflict`。
- `implementation`只有验收点均有实现证据时才是`complete`；主体完成但仍有一个无法确认的验收点时为`likely`；存在明确缺口时为`incomplete`。
- `validation`只接受当前远端候选版本的实际开发验证；失败必须为`failed`，没有充分证据为`unknown`。
- `remoteDelivery=verified`必须有远端提交、MR或集成版本的官方读回。
- 对先开发、后补建任务的历史情况，如果官方Codeup已经找到精确候选，但尚不能证明哪些候选属于当前任务，使用`remoteDelivery=recoverable`，并同时填写`recoveryNeeded=["code_mapping"]`与非空`candidateCodeRefs`。候选必须包含仓库和MR或提交唯一标识；只有模块名、作者或时间相似不能直接升级为`verified`。
- `recoveryNeeded`还可包含`formal_handoff`和`managed_test_scope`。`formal_handoff`是硬阻塞，直接输出`incomplete / stop_after_submit`，不得降为警告或通过确认提示放行；产品交接补齐并重新校验后才能重新判断。其他历史缺口可受控补录；无法恢复或已确认冲突仍写入`knownBlockers`。
- `remainingTaskChanges`只统计属于当前任务的工作区变更；混入其他任务的变化按范围冲突处理。
- `knownBlockers`记录已确认的业务、代码、验证或平台阻塞，禁止为获得自动完成而省略。

## 四种结果

运行：

```text
skill-run classify_completion_readiness.py --input <判断输入.json> --output <判断回执.json>
```

- `confirmed / auto_complete`：全部事实已确认，直接调用当前任务的完成开发执行器，不再次询问。
- `likely / ask_once`：没有硬阻塞，但实现覆盖、验证或剩余改动仍有一个或多个不确定项。展示任务编号、远端版本和不确定项，只询问一次是否继续；同一任务内回复“是”后执行完成开发，执行器原有门禁仍全部保留。
- `recovery_required / recover_then_complete`：正式历史任务已通过产品交接硬门禁，但代码映射或既有测试任务的受管范围尚未补齐。展示精确候选集合；代码归属无法由任务编号、已有台账或正式关系自动证明时只确认一次。确认后按[历史代码交付恢复](historical-code-recovery.md)补录并重新分类，不能直接关单。
- `incomplete / stop_after_submit`：任务不唯一、范围冲突、实现明确未完成、验证失败、远端版本未回读、仍有任务改动或存在已知阻塞。保留提交结果，禁止询问或执行开发关单。

该判断不创建测试结果、不降低测试任务红线，也不把概率值写入云效。正式测试仍由`YunxiaoQA`执行。
