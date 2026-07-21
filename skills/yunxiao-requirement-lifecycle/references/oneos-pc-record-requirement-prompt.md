# 统一运营管理平台 · 记录需求到云效（完整提示词）

复制下方「用户口令」整段发给 Agent；Agent 须先弹出 Plan / 单选卡让你点选 **A 优先级 + B 推进至 + C 标签**，**未点选前不得建单**。

---

## 用户口令（复制整段）

```text
使用 $yunxiao-requirement-lifecycle + $oneos-autoprd
记录需求到云效 · 统一运营管理平台

【需求名】
（填写 1 条或多条，例：车辆资产功能优化）

【描述来源】
$oneos-autoprd，原型/模块：（填写，例：oneos-h5-vehicle-assets）

【已锁定】
- 项目：统一运营管理平台
- 计划开始：今日
- 负责人：分析中 / 设计中 / 设计完成 → 创建人；开发中 → 何斐

【请你先 Plan 点选，未选完禁止写云效】

A. 优先级（单选）
○ 紧急
○ 高
○ 中
○ 低

B. 推进至（单选）
○ 分析中（建同名「分析」任务，负责人=创建人）
○ 设计中（建同名「设计」任务，负责人=创建人）
○ 设计完成（只改状态，负责人=创建人；不强制建阶段任务）
○ 开发中（建同名开发/交付任务，负责人=何斐；状态连跳：待处理→设计完成→待开发→开发中）

C. 标签（可多选；只能从下列 30 个云效标签中选，禁止自造、禁止按业务条线/lines.ts 自动推断）
○ 运维管理条线
○ 报表中心
○ 能源管理
○ 维修站管理
○ 充电站管理
○ 还车应结款
○ 交车应收款
○ 加氢站管理
○ 保险管理
○ 合同管理
○ 租赁账单
○ 供应商管理
○ 客户管理
○ 还车任务
○ 安全培训
○ 备件管理
○ 停车场管理
○ 备车管理
○ 异动管理
○ 调拨管理
○ 上牌管理
○ 替换车管理
○ 还车管理
○ 交车管理
○ 车辆管理
○ 审批中心
○ 故障管理
○ 车辆年审
○ 维修管理
○ 工作台

【我确认 A+B+C 后你再执行】
批准 / Implement 计划时，我会写明所选值，例如：
优先级：高；推进至：设计完成；标签：运维管理条线

【执行要求（Agent）】
1. 读快路径：references/oneos-pc-fast-path.md + assets/oneos-pc-runtime-ids.json
2. 先 $oneos-autoprd 生成描述（【原型】【目标】【非目标】【更新内容】；无增量则「首版定稿」）
3. API 建产品类需求（POST /workitem/workitem，创建时写入 document）
4. 计划开始=今日；按 B 推进状态；按规则建/复用同名阶段任务
5. 标签：用 tags.by_name 查 identifier，PATCH propertyKey=tag operateType=COVER；API 失败 1 次再 UI 兜底
6. 一次校验回报：编号、链接、状态、优先级、负责人、计划开始、标签、描述、阶段任务
7. 禁止默认「中+分析中」；禁止未选标签时自作主张打标；标签失败不得报「已成功」
```

---

## 单条需求示例（填好即用）

```text
使用 $yunxiao-requirement-lifecycle + $oneos-autoprd
记录需求到云效 · 统一运营管理平台

【需求名】
测试需求3

【描述来源】
$oneos-autoprd，原型/模块：oneos-h5-vehicle-assets

【已锁定】
- 项目：统一运营管理平台
- 计划开始：今日
- 负责人：分析中/设计中/设计完成=创建人；开发中=何斐

请先 Plan 让我点选 A 优先级、B 推进至、C 标签（30 项 catalog，禁止 lines.ts 推断）。
我确认后再执行快路径建单。
```

确认回复示例：

```text
优先级：高；推进至：设计完成；标签：运维管理条线
```

---

## Agent 执行清单（内部，勿省略）

| 步 | 动作 |
|---|---|
| 0 | 门禁：A+B+C 已明确；Implement ≠ 已选 |
| 1 | `$oneos-autoprd` → HTML 描述 |
| 2 | `POST …/workitem/workitem` 建需求 + document |
| 3 | 字段：priority、assignedTo、79=今日 |
| 4 | 若 B∈{分析中,设计中,开发中} → 同名阶段任务（查重复用） |
| 5 | 状态推进至 B（开发中三跳） |
| 6 | `PATCH …/workitem/{id}` 打标签 COVER |
| 7 | 回报 ONEOS-xxx + 链接 + 核对表 |

标签 API 形态：

```json
{
  "workitemIdentifier": "{id}",
  "propertyKey": "tag",
  "propertyValue": "{identifier1},{identifier2}",
  "operateType": "COVER"
}
```

参考：`assets/oneos-pc-tag-catalog.md`、`assets/oneos-pc-runtime-ids.json` → `tags.by_name`
