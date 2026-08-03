# 云效 CLI 发布运行时

## 环境与入口

只使用官方 `aliyun devops` CLI。认证来自本机环境变量 `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` 与中心版 `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`，Region 版可用 `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`。不得输出变量值。

```text
skill-run yunxiao_cli_gateway.py doctor
```

## 只读请求

把操作和参数保存为临时 JSON，然后调用：

```text
skill-run yunxiao_cli_gateway.py read --request <请求JSON>
```

请求示例：

```json
{"operation":"flow-get-pipeline","args":["--pipeline-id","精确ID"]}
```

允许 Projex、Flow、Codeup 和 AppStack 的 `get/list/search/find` 读取。参数必须以当前插件的 `aliyun devops <operation> --help` 为准。

## 守卫事务

写入计划 schema 为 `oneos.yunxiao-cli-transaction-plan/v1`，必须包含：

- `authority`：`apply`、`execute`或`cleanup`。
- `idempotencyKey`：发版任务、尝试号、动作和目标组合出的稳定键。
- `guards`：写前只读调用和必要期望值。
- `actions`：本口令授权且在网关白名单内的精确 CLI 写操作。
- `verifications`：动作后的定向只读调用和必要期望值。

```text
skill-run yunxiao_cli_gateway.py preflight --plan <计划JSON> --output <预检回执JSON>
skill-run yunxiao_cli_gateway.py apply --preflight <预检回执JSON> --receipt <执行回执JSON>
```

网关会哈希守卫输出，`apply`前重新读取并拒绝漂移；动作只运行一次，随后做定向回读。相同计划指纹的成功账本直接幂等返回。`${action.0.id}`可作为完整参数值引用前序动作结果。

计划、回执和参数不得包含 Token、Cookie、AccessKey、密码、私钥、认证头或敏感流水线值；敏感参数只能使用 Flow 已配置的受保护变量。

## 性能规则

- 一条业务口令只做一次环境诊断和一次写入事务，不用第二次 `apply`做验证。
- 独立只读发现可并行，写动作及其依赖保持顺序。
- 等待最终一致性时只轮询受影响任务或执行 ID，不重扫项目、迭代或全部流水线。
- 每次轮询最多等待 60 秒并向用户更新；结束后只抓取失败步骤需要的日志区间。
