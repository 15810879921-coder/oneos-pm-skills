# 云效 CLI 实写与回读

YunxiaoPM 的云效操作只允许官方 `aliyun devops` CLI 和本 Skill 的适配器。禁止 Cookie、XSRF、浏览器、DOM、视觉点选和网页内部接口回退。

## 认证与诊断

认证只来自本机环境变量：

- `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`
- 中心版：`ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`
- Region 版：`ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`

统一诊断：

```text
skill-run yunxiao_cli_pm.py doctor
```

不得输出或写入 PAT、Cookie、认证头、AccessKey、密码或私钥。

## 标准生命周期事务

Plan 门禁通过后，先预检：

```text
skill-run yunxiao_cli_pm.py preflight-standard \
  --space-id <项目ID> --project-name <项目名> \
  --subject <需求标题> --description-file <需求说明MD> \
  --delivery-file <交付规则MD> --priority <紧急|高|中|低> \
  --label <标签> --delivery-owner <交付负责人> --stage-owner <阶段负责人> \
  --sprint-name <迭代名> --start-date YYYY-MM-DD --end-date YYYY-MM-DD \
  --idempotency-key <稳定业务键> --output <预检JSON>
```

预检冻结项目、当前PAT用户、人员、工作项类型、优先级、标签、状态ID、同一幂等键下已有对象、迭代和文档哈希。任何对象不唯一或字段无法解析时零写入。

确认预检后执行：

```text
skill-run yunxiao_cli_pm.py apply-standard --preflight <预检JSON> --receipt <回执JSON>
```

apply 必须重新读取全部守卫并比对哈希。通过后按顺序创建或复用：

1. 产品类需求；
2. `【交付】`任务并建立 `ASSOCIATED→需求`；
3. `【分析】`、`【设计】`并分别建立 `PARENT→交付`；
4. 逐状态推进需求，完成分析/设计，回填交付说明，最终停在`待开发`；
5. 创建或复用迭代，只把`【交付】`挂入迭代；
6. 按内部ID回读状态、负责人、关系、迭代和幂等回执。

相同幂等键只能对应一套对象；多条匹配时阻塞，不按标题或最新时间自动选择。部分失败后必须重新预检，由幂等键复用已创建对象并只补未完成动作。

## 官方 CLI 操作映射

| 能力 | CLI 操作 |
|---|---|
| 项目实时列表/详情 | `projex-search-projects` / `projex-get-project` |
| 标签 | `projex-list-labels` |
| 成员 | `base-search-members` / `projex-list-project-members` |
| 工作项类型/字段/流程 | `projex-list-workitem-types` / `projex-get-workitem-type-field-config` / `projex-get-workitem-workflow` |
| 创建/更新/回读工作项 | `projex-create-workitem` / `projex-update-workitem` / `projex-get-workitem` |
| 正式关系 | `projex-create-workitem-relation-record` / `projex-list-workitem-relation-records` |
| 迭代 | `projex-create-sprint` / `projex-list-sprints` / `projex-get-sprint` / `projex-update-sprint` |

参数必须以本机插件的 `aliyun devops <operation> --help` 为准。不得直接拼网页 URL 或调用未公开的 Cookie API。

## 状态与证据

- 状态ID必须实时读取工作流，禁止把缓存ID当成当前事实。
- 创建响应中的内部ID是后续回读锚点；编号只用于交接展示。
- 需求状态、任务状态、正式关系和迭代必须分别回读，不能互相替代。
- 预检与执行回执保存在系统临时目录或显式路径；不得包含敏感认证值。
- 写入失败时返回真实部分状态，禁止用计划值补齐结果。

## 禁止

- 执行 `live_create_fast.py` 等硬编码压测脚本处理真实业务；
- 因 CLI 受限而切换浏览器补点；
- 用标题查重或选择“最新一条”；
- 在一个未经 Plan 确认的事务中扩大项目、需求或迭代范围；
- 未回读即声称创建、流转、关联或挂迭代成功。
