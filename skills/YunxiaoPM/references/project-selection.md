# 门禁 PJ · 云效项目选择（强制点选）

凡 **新建需求 / 新建任务树 / 创建迭代 / 其它写入依赖 `spaceIdentifier`** 的操作，项目必须由用户从云效实时列表**点选**。禁止静默使用 `runtime-ids.json` 里的默认 `project.spaceIdentifier`。

## 何时触发

| 场景 | 是否必须选项目 |
|---|---|
| 记录需求 / 无单快轨新建 | **必须** |
| 创建迭代（新挂项目空间） | **必须**（与需求同项目时沿用已锁定项，仍须在 Plan 写出项目名+ID） |
| 仅推进已有编号（受理确认、开始分析…） | **不必重选**；以该编号所在项目为准，Plan 写出项目名 |
| 只读查询 | 不强制 |

## 执行顺序（建单前）

1. **实时拉取**云效项目列表，只用官方 CLI：

```text
aliyun devops projex-search-projects --page 1 --per-page 100 --order-by gmtCreate --sort desc
```

分页直到返回不足一页；认证只读取本机 PAT/组织环境变量。禁止 Cookie、XSRF、浏览器或网页内部接口。

2. 将结果整理为单选列表：`{name}（{customCode}）`；选项 id 用 `identifier`（spaceId）。
3. **AskQuestion / Plan 单选**「PJ. 云效项目」；未点选 → **禁止 create**。
4. 「批准 Plan」≠ 已选项目；Plan 里仍是空选项或写「默认 01_ONEOS」而未点选 → 停。
5. 用户点选后：本轮 apply 全程使用该 `spaceIdentifier`；回报写清项目名 + customCode + spaceId。
6. 拉取成功后可回写 `assets/runtime-ids.json` → `projects_catalog`（缓存）；**缓存不得当作已选项**。

## 无法对应 → 自动重拉一次

「无法对应」任一成立即触发：

| # | 情形 |
|---|---|
| 1 | 口令/预填的项目名、customCode、别名在**当前列表**中 0 命中 |
| 2 | 口令给出的 spaceId / identifier 不在当前列表 |
| 3 | 用户点选的选项 id 在 apply 前校验时已不在列表（列表过期） |
| 4 | 仅命中 `projects_catalog` 缓存、与本次实时列表不一致 |
| 5 | 首次拉取失败后改用了缓存，用户按缓存点选后 create 报项目/空间无效 |

**动作（固定一次）：**

1. **立即再调一次**同一 `projex-search-projects` CLI 查询（强制网络，不用缓存）。
2. 用新列表重新做匹配 / 刷新 Plan 单选选项；可回写 `projects_catalog`。
3. 回报注明：`已自动重拉项目列表（因无法对应）`。
4. **仍无法对应** → 停，展示最新列表请用户重选；**禁止**再自动拉第 3 次；**禁止**猜一个 spaceId 继续建单。

匹配规则（名/码）：忽略大小写；`name` 全等或包含；`customCode` 全等；`name_aliases` 全等。多命中视为无法唯一对应 → 重拉后仍多命中则请用户点选，不自动选定。

## 禁止

- 未询问就写入 `project.spaceIdentifier`（即便 catalog 标了 `suggested`）
- 按口令里的「统一运营管理平台」字符串静默映射而不展示列表点选（口令仅作**预填建议**，仍须用户确认点选）
- API 失败时擅自沿用上次默认；应展示 `projects_catalog` 缓存并标明「离线缓存，请确认」，仍须点选；用户确认后若仍无法对应 → 走上一节「自动重拉一次」
- 多项目并行建单却共用一个未确认的 spaceId
- 「无法对应」时循环重拉超过 1 次，或跳过点选直接建单

## 口令预填

```text
记录需求：…；项目=01_ONEOS；…
```

若口令已含项目名/编号前缀且在实时列表中**唯一命中**：Plan 可预勾该选项，但仍须用户确认；0 命中或多命中 → **先自动重拉一次**再匹配；仍 0/多 → 不预勾，只展示最新列表。

## 执行入口

项目点选查询直接使用官方 `projex-search-projects`；标准生命周期由 `skill-run yunxiao_cli_pm.py preflight-standard` 再次回读并冻结项目ID与名称。旧 `list_projects.py` 不再执行。
