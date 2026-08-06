# 记录需求 · 元字段（优先级 / 标签 / 提交部门 / 提交人）

建单前消费网页 / AutoRDO / 口令中的四类元信息。细则与 `assets/runtime-ids.json` 对齐；**禁止臆造未验证的 fieldIdentifier**。

## 口令形态

```text
记录需求：…；交付端=PC|小程序|共用服务；优先级=紧急|高|中|低；标签=…；提交部门=…；提交人=…；推进至=…
```

`交付端` 必选：`PC` / `小程序` / `共用服务`；未给则停下询问，禁止默认猜。  
含义（产品确认）：`PC`/`小程序` = 后续只建对应单端【交付】；`共用服务` = 开始分析或快轨时建 **双端【交付】**（PC+小程序 各一，挂同一需求）。  
其余四字段（优先级/标签/提交部门/提交人）均可选出现；网页或 AutoRDO 提示里已带的值与口令等价。

## Plan 是否追问

记录需求 **一律**走 [compact-select.md](compact-select.md) 字母表（类型/项目/优先级/标签），即使用户口令已写齐；给出建议压缩串，等用户回 `1a2b3a4d`（或改字母）并「执行」。

| 条件 | 行为 |
|---|---|
| 口令已含类型/项目/优先级/标签 | 对应选项标 ★ + 建议压缩串；**仍须**压缩确认或显式点选 |
| 标签名 0 命中 / 多命中 | **自动重拉一次**标签候选并重生 4.A/B/C…；仍失败则停 |
| 仅缺提交部门/提交人 | 压缩 1–4 确认后，缺则追问或写入描述页脚 |
| 仅缺「推进至」等 | 按既有口令规则；可作 5. 题字母表 |

## 写入策略

### 优先级（已验证）

- 映射：`runtime-ids.json` → `priority`（紧急 / 高 / 中 / 低）。
- create 时通过官方 `projex-create-workitem --custom-field-values` 写入 `priority`，并按 [live-api.md](live-api.md) 回读。
- 未给优先级时：Plan 追问；脚本默认「中」仅作既有兜底，口令/网页有值时以用户值为准。

### 标签（已验证）

- 映射：`runtime-ids.json` → `tags`（按显示名取 tagId）。
- 标签须 **PATCH** `propertyKey: "tag"`（create 带 tag 不落库）。
- 口令/网页给出的标签名若不在候选：按 [compact-select.md](compact-select.md) **自动重拉一次**标签列表并重生选项；仍无则停在 Plan，勿猜 ID。

### 提交部门 / 提交人（已验证 · 2026-07-27 · ONEOS-293）

| 字段 | fieldIdentifier |
|---|---|
| 提交部门 | `3132597a9718d1c282b7ba5a0c` |
| 提交人 | `9e01269e96f91fbb97d36bf5b3` |

| 规则 | 说明 |
|---|---|
| **写入** | `POST /projex/api/workitem/workitem/field/value/{workitemId}`，`Content-Type: application/x-www-form-urlencoded`，参数 `fieldValueList` = JSON 数组字符串 `[{"fieldIdentifier","value"}]` |
| **形态** | 均为普通文本 input（非人员选择器）；口令值原样写入 |
| **页脚** | 仍可在描述页脚重复一份，便于检索；**不能替代**字段写入 |
| **计划开始** | 字段 `79`，同一 `field/value` API；推荐 `YYYY-MM-DD 12:00:00`。快轨：【交付】/【设计】创建当日写入；【设计】另写计划完成 `80`=`当日 23:59:59` |
| **预计工时** | 字段 `101586` **禁止**直接 PATCH；用 `POST …/time/estimate`（`spentTime`）登记；删多余用 `DELETE …/time/estimate/{workitemId}/{estimateId}` |
| **实际工时** | `POST …/workitem/time`，body **`actualTime`**（非 spentTime）+ `gmtStart`/`gmtEnd`（epoch ms 字符串）；快轨待开发需求默认 **2** |
| **描述更新** | `PATCH …/workitem/{id}/document`，`{"content","formatType":"RICHTEXT"}` |
| **快轨标签** | 【交付】【设计】建单后 `PATCH propertyKey=tag`：`需求模块标签` + **端侧标签**（`PC` 或 `小程序`）；多标签逗号拼接。禁止只复制需求标签而漏打端标签 |

## 与描述双段的关系

页脚元信息写在「原始诉求」段末或整篇描述末尾均可，**不得覆盖** `## 产品说明（AutoPRD）` / `## 工作项编号（系统）` 区块（见 [description-split.md](description-split.md)）。
