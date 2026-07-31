# 云效实写 API（YunxiaoPM 已验证）

`verified_at`: 2026-07-25 · **项目须门禁 PJ 点选**（见 [project-selection.md](project-selection.md)）；历史验证样本项目为 `01_ONEOS` / 原「统一运营管理平台」（`last_selected.spaceIdentifier` 见 `assets/runtime-ids.json`，禁止未点选即使用）。

本文件只记**已跑通**的写法；禁止再盲试 `updateStatus` / 错误 `updateFieldValue` POST。

## 认证

- Cookie：Chrome 域 `.aliyun.com` / `devops.aliyun.com`（`browser_cookie3` 或 Playwright storage）
- Header：`x-xsrf-token` = cookie `XSRF-TOKEN`（URL 解码后）
- `Origin` / `Referer`：`https://devops.aliyun.com`

## 建单

`POST|PUT /projex/api/workitem/workitem?_input_charset=utf-8`

创建响应 `result.identifier` / `serialNumber` 即编号真相；**禁止按标题查重**。

## 改负责人（已通）

```http
PATCH /projex/api/workitem/workitem/{id}?_input_charset=utf-8
{"propertyKey":"assignedTo","propertyValue":"<userId>","operateType":"COVER"}
```

交棒：【交付】`propertyValue` = 何斐 ID。

## 打标签（已通）

```http
PATCH /projex/api/workitem/workitem/{id}?_input_charset=utf-8
{"workitemIdentifier":"{id}","propertyKey":"tag","propertyValue":"<tagId>[,<tagId>]","operateType":"COVER"}
```

## 改状态（已通 · 唯一推荐）

```http
POST /projex/api/workitem/workitem/{id}/status/transit?_input_charset=utf-8
{"fromStatus":"<当前status.identifier>","toStatus":"<目标status.identifier>"}
```

成功：`code=200` 且 `result=true`。失败时 `errorMsg` 含「不能流转」。

### 需求状态 ID（本项目）

| 显示名 | identifier |
|---|---|
| 待处理 | `100005` |
| 已确认 | `32` |
| 分析中 | `154395` |
| 设计中 | `156603` |
| 设计完成 | `307012` |
| 待开发 | `1582fc929d429111b925309493` |

### 任务状态 ID

| 显示名 | identifier |
|---|---|
| 待处理 | `100005` |
| 已完成 | `100014` |

### 极速交棒跳转（工作流允许）

从「待处理」菜单可见直达「设计完成」；推荐最少跳：

```text
待处理 → 设计完成 → 待开发
```

标准路径若需看板留痕，可走完整链：已确认→分析中→设计中→设计完成→待开发（仍用本 API，勿开 UI）。

### 禁止（已证伪）

| 写法 | 结果 |
|---|---|
| `PATCH …/updateStatus` + `statusIdentifier` | `400 不能为空` |
| `PATCH …/{id}` + `propertyKey=status` | `property not found` |
| Playwright 点左侧/列表上的状态色块（`x<1100`） | 假成功、状态不落库 |

仅当 `status/transit` 不可用时，才用 UI：右侧详情状态钮（`getBoundingClientRect().x > 1100`）+ `.next-menu-item`。

## 计划开始/完成 · 提交部门/人 · 预计工时（2026-07-27 修订）

**通用字段写入（已通）：**

```http
POST /projex/api/workitem/workitem/field/value/{workitemId}?_input_charset=utf-8
Content-Type: application/x-www-form-urlencoded

fieldValueList=[{"fieldIdentifier":"79","value":"2026-07-27 12:00:00"},{"fieldIdentifier":"3132597a9718d1c282b7ba5a0c","value":"业务管理部"},{"fieldIdentifier":"9e01269e96f91fbb97d36bf5b3","value":"何苗苗"}]
```

| 字段 | fieldIdentifier | value |
|---|---|---|
| 计划开始 | `79` | `YYYY-MM-DD HH:mm:ss`（推荐正午）或 epoch ms 字符串 |
| 计划完成 | `80` | 同上 |
| 提交部门 | `3132597a9718d1c282b7ba5a0c` | 纯文本 |
| 提交人 | `9e01269e96f91fbb97d36bf5b3` | 纯文本 |

**预计工时 `101586`：禁止直接改字段**（报「不可直接修改」）。须登记：

```http
POST /projex/api/workitem/workitem/time/estimate?_input_charset=utf-8
{"workitemIdentifier":"<id>","spentTime":8,"type":"develop","description":"阶段日历工时","recordUserIdentifier":"<userId>","forCreate":false,"containsRestDay":false}
```

删除多余预估：`DELETE /projex/api/workitem/workitem/time/estimate/{workitemId}/{estimateId}`  
列表：`GET …/time/estimate/list?workitemIdentifier=`

旧写法 `PATCH …/updateWorkitemFieldValue` 对上述自定义字段常 `400 不能为空`，勿再优先使用。

## 父子 / 子项 / 关联项（已通 · 2026-07-23 修订 · 子项优先）

### 关联项（【交付】强制 · ASSOCIATED）

任务详情「关联项」只认 `ASSOCIATED`。**仅【交付】**建单时 `createWorkitemRelationInfo` 必须指向**需求**：

```json
{
  "createWorkitemRelationInfo": {
    "relatedWorkitemIdentifier": "<需求id>",
    "relatedToRelationIdentifier": "ASSOCIATED"
  }
}
```

校验：

```http
GET /projex/api/workitem/v2/workitem/{交付id}/relation/workitem/list/by-relation-category?category=ASSOCIATED&isForward=true
```

`result` 含该需求即通过。

### 禁止（关联项）

| 写法 | 结果 |
|---|---|
| `relatedToRelationIdentifier=PARENT` 把交付挂需求 | 详情可能有 parent，**关联项仍为空** |
| 分析/设计只用 `ASSOCIATED→需求` + `parentIdentifier` | 关联项可能有，**交付子项仍为空**（ONEOS-246/247） |
| 建后再 `POST …/relation/record` 补关系 | Cookie 路径下常报「不能关联相同的工作项」 |
| `createWorkitemRelationList` | 不落 ASSOCIATED |

### 子项（【分析】/【设计】强制 · TASK_SUB）

「子项」页读 `PARENT_SUB` / `TASK_SUB`，分析/设计**必须**：

```json
{
  "parent": "<交付id>",
  "parentIdentifier": "<交付id>",
  "createWorkitemRelationInfo": {
    "relatedWorkitemIdentifier": "<交付id>",
    "relatedToRelationIdentifier": "TASK_SUB"
  }
}
```

同一 create 只能带一条 `createWorkitemRelationInfo`。  
`ASSOCIATED→需求` 与 `TASK_SUB→交付` **不能同时写**。

**产品优先级：交付「子项」tab > 阶段任务「关联项」。**  
交付本身仍必须 `ASSOCIATED→需求`。标准路径下分析/设计的「关联项」允许为空。

**无单快轨例外（设计双挂）：** create 用 `TASK_SUB→交付` 后，须再补 **ASSOCIATED→原始需求**，使设计详情「关联项」可见需求。

```http
POST /projex/api/workitem/workitem/{设计id}/relation/record?_input_charset=utf-8
{"relationIdentifier":"ASSOCIATED","toWorkitemIdentifier":"<需求id>"}
```

**已证伪（Cookie · 2026-07-27）：** 凡工作项**已创建**后再 `relation/record` 补挂（含 ASSOCIATED / TASK_SUB），常报「不能关联相同的工作项」；与是否已有父项无关。`createWorkitemRelationList` 亦不落 ASSOCIATED。  
**可行路径：**

| 目标 | 做法 |
|---|---|
| 交付「子项」可见设计（优先） | create 带 `TASK_SUB→交付` |
| 设计「关联项」可见需求 | create 带 `ASSOCIATED→需求`（与上互斥，同 create 只能一条） |
| 双挂 | 需个人 `x-yunxiao-token` OpenAPI；Cookie 路径**不得**声称成功 |

产品默认：**子项优先**；关联项失败须在回报中标红并列出缺项。

校验子项：

```http
GET /projex/api/workitem/v2/workitem/{交付id}/relation/workitem/list/by-relation-category?category=PARENT_SUB&isForward=true
```

结果须含对应分析/设计 identifier。

校验设计关联项：

```http
GET /projex/api/workitem/v2/workitem/{设计id}/relation/workitem/list/by-relation-category?category=ASSOCIATED&isForward=true
```

`result` 须含原始需求 identifier。

### 无单快轨字段默认（2026-07-27）

| 对象 | 规则 |
|---|---|
| 【设计】描述 | 复制需求 document HTML |
| 【设计】`79`/`80` | 当日 `12:00:00` / `23:59:59`，create 后 `field/value`（勿 create 同时带 79+80） |
| 【交付】描述 | 手工同步需求正文，或原型→AutoPRD；禁止无故占位 |
| 【交付】`79` | 创建当日；不写 `80` |
| 【交付】/【设计】标签 | 与需求相同，`PATCH propertyKey=tag` |
| 需求预计工时 | `time/estimate` **spentTime=2**（先删多余预估） |
| 需求实际工时 | `POST …/workitem/time`，body 用 **`actualTime`**（非 spentTime）+ `gmtStart`/`gmtEnd` epoch ms 字符串；见 `runtime-ids.json` `fields.actual_hours` |
| 描述更新 | `PATCH …/workitem/{id}/document`，`{"content":"<html>","formatType":"RICHTEXT"}` |

## 迭代挂接（已通 · 2026-07-27 · 只挂交付）

创建迭代：`POST /projex/api/workspace/sprint`（必填 `staffIds`；可写 `capacityHours`）。

挂【交付】到迭代：

```http
PATCH /projex/api/workitem/workitem/{交付id}?_input_charset=utf-8
{"workitemIdentifier":"{交付id}","propertyKey":"sprint","propertyValue":"{sprintId}","operateType":"COVER"}
```

清空误挂（如需求）：`propertyValue:""` + `operateType:"COVER"`。

**校验**必须读 `/extra`（详情主接口常不含 sprint 字段，禁止据此判失败）：

```http
GET /projex/api/workitem/workitem/{id}/extra?_input_charset=utf-8
→ result.sprint[].identifier / name
```

产品规则：**只挂【交付】**；需求 / 分析 / 设计默认不挂（除非口令显式）。

### 极速建单注意

1. Cookie 只刷一次；全程纯 HTTP，默认**不开浏览器**。
2. 交付建完后，【分析】与【设计】**并行**创建（均 TASK_SUB→交付）；标准/快轨两树可并行。
3. 状态用 `transit` + **本地追踪 fromStatus**（禁止每次 GET）；负责人在交棒场景下**创建时即何斐**。
4. 建单 `fieldValueList` 可带计划开始 `79`；**不要**在 create 同时写 `79+80`（同日会 400）。
5. 标签必须 PATCH（create 带 tag 不落库）；可与建子任务重叠；快轨交付/设计须与需求同标签。
6. `requests.Session` keep-alive；**禁止**对共享 opener 加全局锁。
7. 脚本入口：`scripts/live_create_fast.py`（v5：快轨描述/计划/标签/工时 2+2/设计 ASSOCIATED 补挂）。
