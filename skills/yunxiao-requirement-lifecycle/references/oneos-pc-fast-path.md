# 统一运营管理平台 · 记录需求快路径

真相源运行时 ID：[assets/oneos-pc-runtime-ids.json](../assets/oneos-pc-runtime-ids.json)  
验证样例：ONEOS-84「测试需求」（2026-07-21）。

**用户可复制完整口令（A/B/C 门禁 + 30 标签）：** [oneos-pc-record-requirement-prompt.md](oneos-pc-record-requirement-prompt.md)

本文件只服务**日常 `记录需求` apply**。全量审计/规则配置仍读 `live-operations.md` 等模块。

## 0. 执行门禁（强制）

用户口令要求 Plan / 单选「优先级」「推进至」「标签」时：

1. **必须**先拿到明确的 A（紧急/高/中/低）、B（分析中/设计中/设计完成/开发中）、**C（标签，可多选）**。
2. 标签 **C** 只能从 [assets/oneos-pc-tag-catalog.md](../assets/oneos-pc-tag-catalog.md) / `tags.catalog` 点选；**禁止**按 `lines.ts` 或业务条线说明自动推断。
3. 来源优先：`AskQuestion` 点选 → Plan 批准时写明的 A+B+C → 用户一句话点明。
4. **禁止**：未选时默认「中 + 分析中」并继续建单；**禁止**未选标签时自作主张打标。
5. 「批准/Implement 计划」≠ 已选 A+B+C；计划正文若仍是空 ○，必须先问清再执行。

多条需求名称时：每条或整批共用的优先级/推进至/标签仍须用户点选后再写云效。

## 1. 加载配方（禁止重探）

对项目别名含「统一运营管理平台」时：

1. 读取 `assets/oneos-pc-runtime-ids.json`。
2. **禁止**再探测 create URL（不要用 `/workitem/create`）。
3. **禁止**对优先级 ID 做猜测重试超过配方表。

## 2. 标准执行顺序（目标 1～3 分钟）

```text
AutoPRD → API 建需求(含描述) → API 建阶段任务 → API 打标签(COVER) → 状态连跳 → 一次校验回报
```

### 2.1 AutoPRD

- 先跑 `$oneos-autoprd`（模块/原型来自口令或对话页）。
- 描述 HTML 最小块：`【原型】` + `【目标】` + `【非目标】` + `【更新内容】`（无变更记录则「首版定稿」）。

### 2.2 API 建产品类需求

`POST`（失败再试一次 `PUT`）  
`https://devops.aliyun.com/projex/api/workitem/workitem?_input_charset=utf-8`

要点：

- `workitemTypeIdentifier` **与** `workitemType` 都设为产品类需求 ID。
- `document: { content: html, formatType: 'RICHTEXT' }` 创建时写入。
- `fieldValueList` 带 `priority`、`assignedTo`、可选 `79`（计划开始，中国时区中午 epoch 字符串）。
- 开发中：需求负责人用何斐 ID；分析中/设计中/设计完成：创建人 ID。

### 2.3 API 建同名阶段任务

同一 create 接口，`category=Task`，`parentIdentifier=需求ID`，标题与需求**完全同名**。

| 推进至 | 任务标签目标 | 负责人 |
|---|---|---|
| 分析中 | 分析 | 创建人 |
| 设计中 | 设计 | 创建人 |
| 开发中 / 待开发 | 开发或交付 | 何斐 |

查重：同需求 + 同阶段标签 + 未取消 → 复用，不建第二条。详见 [auto-stage-task.md](auto-stage-task.md)。

### 2.4 状态连跳（开发中）

从「待处理」到「开发中」UI 固定路径：

```text
待处理 → 设计完成 → 待开发 → 开发中
```

每跳点开状态按钮选目标；不要在「待处理」下拉里找「开发中」（没有）。

其它推进至：

- 分析中 / 设计中 / 设计完成：待处理下拉通常可直达。

### 2.5 标签（选择器点选 + API）

1. 用户已从 `tags.catalog` 点选标签名（见门禁 C）；用 `tags.by_name` 得到 identifier。
2. **优先 API**（已验证）：

```http
PATCH https://devops.aliyun.com/projex/api/workitem/workitem/{identifier}?_input_charset=utf-8
Content-Type: application/json

{
  "workitemIdentifier": "{identifier}",
  "propertyKey": "tag",
  "propertyValue": "{id1,id2}",
  "operateType": "COVER"
}
```

3. API 失败 1 次 → UI 标签选择器勾选 → **确定**；仍失败 → **停止并请用户回复标签名**，禁止报「已打上」。
4. **禁止**对照 `lines.ts` / 业务条线说明自动映射；刷新全量标签：`GET` `api.list_tags`（`spaceType=Space`）。

### 2.6 校验与回报（只做一次）

核对：编号、链接、状态、优先级、负责人、计划开始、描述含原型、任务父项、标签。  
截图最多：建单后、终态后各一次。

## 3. 性能红线

| 允许 | 禁止 |
|---|---|
| 配方内 ID / URL | 每步 3+ 端点盲探 |
| create 带描述 | 默认先开富文本再粘贴 |
| 状态固定三跳 | React fiber 乱调 onChange（易白屏） |
| 标签失败问用户 | 标签失败仍声称成功 |
| API 失败 1 次改 UI | 同失败 payload 循环重试 |

## 4. 浏览器会话

- 复用已登录 `devops.aliyun.com`；不记录 Cookie/Token。
- 优先已打开的「统一运营管理平台」项目页；锁 tab 后执行，结束解锁。
