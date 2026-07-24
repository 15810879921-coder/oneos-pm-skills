# 云效实写 API（YunxiaoPMapp 已验证）

`verified_at`: 2026-07-23 · 项目 `统一运营管理平台`（`spaceIdentifier` 见 `assets/runtime-ids.json`）。

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

## 计划开始/完成

`PATCH …/updateWorkitemFieldValue` · `fieldIdentifier` `79`/`80` · value = 当日 `+08:00` 正午 epoch ms 字符串。

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
交付本身仍必须 `ASSOCIATED→需求`。分析/设计的「关联项」允许为空。若必须双挂，需个人 `x-yunxiao-token` 调 OpenAPI 后补 ASSOCIATED。

校验子项：

```http
GET /projex/api/workitem/v2/workitem/{交付id}/relation/workitem/list/by-relation-category?category=PARENT_SUB&isForward=true
```

结果须含对应分析/设计 identifier。

### 极速建单注意

1. Cookie 只刷一次；全程纯 HTTP，默认**不开浏览器**。
2. 交付建完后，【分析】与【设计】**并行**创建（均 TASK_SUB→交付）；标准/快轨两树可并行。
3. 状态用 `transit` + **本地追踪 fromStatus**（禁止每次 GET）；负责人在交棒场景下**创建时即何斐**。
4. 建单 `fieldValueList` 可带计划开始 `79`；**不要**在 create 同时写 `79+80`（同日会 400）。
5. 标签必须 PATCH（create 带 tag 不落库）；可与建子任务重叠。
6. `requests.Session` keep-alive；**禁止**对共享 opener 加全局锁。
7. 脚本入口：`scripts/live_create_fast.py`（v4：交付 ASSOCIATED + 阶段 TASK_SUB 强制验收）。
