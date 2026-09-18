# 云效 CLI 统一执行运行时

本 Skill 中云效 Projex、Codeup、Flow 和 AppStack 的读取、写入、日志查询与结果回读使用官方 `aliyun devops` CLI。唯一的传输例外是`完成开发`读取TestHub测试计划：默认直接使用`yunxiao_testhub_read_api.py`调用官方公开ListTestPlan接口，固定`Content-Type: application/json`；禁止先探测已知错误的计划列表CLI或为该查询升级重试插件。真实JSON服务/连接失败时只跳过正式计划/用例验证并输出真实错误和traceId，后续仍走CLI创建必需测试任务。鉴权、权限、参数、归属冲突仍阻断，该例外不适用于任何写操作。其他CLI失败默认停止并报告缺失能力；禁止浏览器、视觉点选、截图/OCR、DOM、Cookie、连接器或网页内部接口替代执行。

## 环境

CLI 只从 `PATH`、`ALIYUN_CLI_PATH` 或官方默认安装位置发现。认证只读取以下本机环境变量，不在参数、计划、回执、日志、Skill 或聊天中记录其值：

- `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`
- 中心版：`ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`
- Region 版：`ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`

先执行：

```text
skill-run yunxiao_cli_gateway.py doctor
```

## 适配器选择

1. `分配任务`使用 `yunxiao_cli_allocate_task.py`。
2. 批量 Bug 的 Projex 快照和状态写回使用 `yunxiao_cli_bug_batch.py`，Codeup/Flow 使用 `yunxiao_cli_bug_delivery.py`。
3. `完成开发`的多阶段收口使用`yunxiao_cli_complete_development.py`，其每个阶段再调用`yunxiao_cli_gateway.py`。
4. 其他接收交棒、开始开发、单 Bug、测试任务、发布回流和分支清理的云效动作使用 `yunxiao_cli_gateway.py`。
5. 本地代码读取、编辑、测试、`git commit` 和 `git push`不经过网关；Codeup 远端分支、MR、合并和删除必须经过 CLI 适配器。

## 只读调用

把单个白名单只读请求保存为临时 JSON：

```json
{
  "operation": "projex-get-workitem",
  "args": ["--id", "工作项内部ID"]
}
```

然后执行：

```text
skill-run yunxiao_cli_gateway.py read --request <请求JSON>
```

只读白名单覆盖 `base-get-*` 以及 Projex、Codeup、Flow、AppStack 的 `get/list/search/find` 操作。精确 CLI 参数必须来自当前插件的 `aliyun devops <operation> --help`，不得猜测。

## 写事务

所有未由专用适配器封装的写入都使用 `oneos.yunxiao-cli-transaction-plan/v1`：

```json
{
  "schema": "oneos.yunxiao-cli-transaction-plan/v1",
  "label": "精确业务动作",
  "authority": "apply",
  "idempotencyKey": "稳定业务键",
  "guards": [
    {
      "operation": "projex-get-workitem",
      "args": ["--id", "工作项内部ID"],
      "expect": {"status.displayName": "待处理"}
    }
  ],
  "actions": [
    {
      "operation": "projex-update-workitem",
      "args": ["--id", "工作项内部ID", "--biz-body", "{\"status\":\"目标状态ID\"}"]
    }
  ],
  "verifications": [
    {
      "operation": "projex-get-workitem",
      "args": ["--id", "工作项内部ID"],
      "expect": {"status.displayName": "处理中"}
    }
  ]
}
```

执行顺序固定为：

```text
skill-run yunxiao_cli_gateway.py preflight --plan <计划JSON> --output <预检回执JSON>
skill-run yunxiao_cli_gateway.py apply --preflight <预检回执JSON> --receipt <执行回执JSON>
```

`apply`重新读取守卫并比较业务快照；工作项详情仅忽略响应包装与顶层`modifiedAt/updatedAt/gmtModified/updateTime`更新时间，其余字段（包括状态、描述、负责人、归属、关系及未知字段）仍参与漂移检查。其他接口保留完整响应比较；旧预检也保留原有完整哈希检查。`expect`始终校验，不能通过省略业务期望绕过快照冲突。发生未解释漂移时当前阶段零写入。

动作只执行一遍，随后运行定向回读。相同计划指纹已有成功账本时返回原回执并补写请求的回执文件，不重复写入。动作可在完整参数值中使用 `${action.0.id}` 形式引用前序动作输出；不得在普通字符串中拼接模板。

部分失败使用原计划、原预检、原幂等键执行`apply --resume`：全部动作都有成功回执时，只重新执行全部定向回读；已证明从未尝试的后续动作，只有守卫与生命周期复核通过后才执行。每次发出写请求前持久化`inFlightAction`；请求失败或进程中断留下结果不明标记时，禁止自动重放，必须先通过官方状态核对。旧部分回执只有在全部动作成功证据齐全时才能补回读，不能猜测剩余动作未执行。不得删除账本或更换幂等键规避此保护。

同一幂等键用排他执行锁防止首次执行与恢复并发写入。锁冲突时等待原执行结果；进程异常终止的遗留锁，只能在核实原进程已结束、保留并核对账本后人工处理，不自动抢锁。清理锁不代表写入结果已确定，`inFlightAction`保护仍然有效。

分支删除还必须使用 `authority=cleanup` 且设置 `destructiveConfirmation=true`。网关拒绝凭据字段和值，不保存敏感流水线参数；敏感参数只能引用 Flow 已配置的受保护变量。

## 性能

- 每条业务命令只运行一次 `doctor`，不要对同一未变化事务执行第二次 `apply`。
- 预检只读取写入门禁所需对象；成功后只回读被写字段、关系、执行或日志。
- 独立的只读发现可并行；任何存在依赖或写入的步骤保持顺序。
- 同一阶段内对同一对象、相同参数且中间无写入的重复读取，复用当次结果；不得跨写入阶段缓存守卫或替代最终回读。
- 等待云效最终一致性时使用短间隔定向回读，不重新扫描整个项目。
- 长流水线按不超过 60 秒的节奏轮询并向用户汇报，不使用一次超长阻塞等待。
