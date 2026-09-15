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

需确认的标准生命周期事务在 Plan 门禁通过后先预检；同一已授权幂等批次的续跑可直接重做预检，不重复要求确认：

```text
skill-run yunxiao_cli_pm.py preflight-standard \
  --space-id <项目ID> --project-name <官方回读项目名> \
  --subject <需求标题> --description-file <需求说明MD> \
  --delivery-file <交付规则MD> --priority <紧急|高|中|低> \
  --label <标签> --delivery-owner <交付负责人> --stage-owner <阶段负责人> \
  --sprint-name <迭代名> --start-date YYYY-MM-DD --end-date YYYY-MM-DD \
  --idempotency-key <稳定业务键> --output <预检JSON>
```

项目 ID 若由命令明确给出，先用官方`projex-get-project`唯一回读名称与状态，不再人工点选。预检冻结项目、当前PAT用户、人员、工作项类型、优先级、标签、状态ID、同一幂等键下已有对象、迭代和需求/交付文档哈希。交付负责人参数来自命令或项目配置，可为姓名或userId，但必须官方唯一解析；任何对象不唯一或字段无法解析时零写入。

首次或扩范围事务确认预检后执行；同一幂等键、同一范围的续跑在守卫无漂移时直接执行：

```text
skill-run yunxiao_cli_pm.py apply-standard --preflight <预检JSON> --receipt <回执JSON>
```

apply 必须重新读取全部守卫并比对哈希。通过后按顺序创建或复用：

1. 产品类需求；
2. `【交付】`任务并建立 `ASSOCIATED→需求`；
3. `【分析】`、`【设计】`并分别建立 `PARENT→交付`；
4. 逐状态推进需求，完成分析/设计，回填交付说明，最终停在`设计完成`，回执 `formal:false`；
5. 创建或复用迭代，只把`【交付】`挂入迭代；
6. 按内部ID回读状态、负责人、关系、迭代和幂等回执。

相同幂等键只能对应一套对象；多条匹配时阻塞，不按标题或最新时间自动选择。部分失败后必须重新预检，由幂等键复用已创建对象并只补未完成动作；该续跑和补官方回读不重复确认。项目、对象、关系、负责人或动作范围变化时不属于续跑，必须重新Plan。

已有冻结 manifest/产品快照，或需求已进入待开发及后续阶段时，初始化入口零写入阻断，不能覆盖历史或其他 scope。10.1.x standard 预检须重新生成；不再承诺初始化一步直接正式交开发。

## 产品修改后刷新快照

PRD/原型修改并确认后，生成符合[product-handoff-snapshot.md](product-handoff-snapshot.md)的快照和 [handoff-gate.md](handoff-gate.md) 清单，再独立执行：

```text
skill-run yunxiao_cli_pm.py preflight-product-snapshot \
  --space-id <项目ID> --project-name <项目名> \
  --requirement-id ONEOS-xx --delivery-id ONEOS-a \
  --snapshot-file <产品快照MD> --handoff-file <该scope冻结清单JSON> --output <预检JSON>

skill-run yunxiao_cli_pm.py apply-product-snapshot \
  --preflight <预检JSON> --receipt <回执JSON>
```

预检按编号唯一解析需求和【交付】，验证`ASSOCIATED→需求`，冻结两者状态、负责人、描述哈希和快照哈希。明确编号的刷新属于幂等写入：同一已授权范围内不重复确认；apply只替换`## 产品交棒快照`受管区块，随后回读两边快照编号/哈希，并证明状态、负责人和正式关系未变化。已完成或已取消对象不得刷新。

## 正式交棒到待开发

全部当前端侧交付分别冻结和回读清单后执行（此处用官方内部 ID，不是 ONEOS 显示编号）：

```text
skill-run yunxiao_cli_pm.py preflight-handoff \
  --space-id <项目内部ID> --requirement-id <需求内部ID> \
  --handoff-file <Web清单.json> --handoff-file <小程序清单.json> --output <预检JSON>
skill-run yunxiao_cli_pm.py apply-handoff --preflight <预检JSON> --receipt <回执JSON>
```

单端只传一份，多 scope 重复参数。脚本实时检查全部关联端侧交付、负责人、正式关系、两边同版 manifest 和必读资料字节；仅允许设计完成→待开发，同版已待开发可幂等重验。预检需按既有 Plan 授权确认；已确认计划明确覆盖这些对象、清单及正式交棒时无需重复确认，只有初始化授权则不自动继续。apply 只写需求状态，不改正文、负责人或创建下游任务；前置漂移零写入。写后回读失败须报告可能部分成功，重新预检后续跑，不把 PATCH 返回当完成。

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
- 借幂等续跑扩大项目、需求、负责人或迭代范围；
- 未回读即声称创建、流转、关联或挂迭代成功。
