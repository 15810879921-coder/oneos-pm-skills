# 法眼如炬（fayanruju）changelog

原名 wangmian-brain；自 v1.2.0 起正式更名。

## v1.3.21 — 2026-08-16

### 用途名主入口 · 业务口径

- 团队主入口：`oneos-biz-rules`；本目录为花名运行时
- 版图：`oneos-wave-router`；配对产品交付 / 开发落地 / 测试验收
- ≠ 改发版权；≠ 写云效

## v1.3.20 — 2026-08-16

### 轨 B 现网冲突升档指针（配对明镜 v1.0.10）

- `references/dual-track-p0.md` 增「轨 B · 现网冲突升档」
- 明镜 `deviationCode: conflict_kb` → 升法眼 → 言出法随改包 → 再交明镜
- ≠ 扩 KB 正文；≠ 写云效

## v1.3.19 — 2026-08-16

### 第七轮 KB↔AutoPRD 对表（evo-fy-kb-round7）

- 报告 [`references/kb-drift-2026-08-16-round7.md`](references/kb-drift-2026-08-16-round7.md)：备车 · 停车场 · 证照
- KB：三卡 legacy→building；备车钉 `ops-backup-vehicle`+装备标签；停车场有车禁删；开 `DEF-OPS-CERT-01`
- ≠ 写云效 / 合 Master

## v1.3.18 — 2026-08-16

### 第六轮 KB↔AutoPRD 对表（evo-fy-kb-round6）

- 报告 [`references/kb-drift-2026-08-16-round6.md`](references/kb-drift-2026-08-16-round6.md)：调拨 · 异动 · 年审
- KB：三卡从 legacy 升 building；钉待办 102/104/105；**重开 DEF-OPS-03**（异动加氢汇算假绿）
- ≠ 写云效 / 合 Master

## v1.3.17 — 2026-08-15

### 第五轮 KB↔AutoPRD 对表（evo-fy-kb-round5）

- 报告 [`references/kb-drift-2026-08-15-round5.md`](references/kb-drift-2026-08-15-round5.md)：交车 · 还车 · 替换车 · 保险采购
- KB：交还车/替换从 legacy 薄卡升 building；保险纠偏「业财规划 ≠ AutoPRD 主路径」；开 DEF-OPS-DELIV-03 / DEF-OPS-RETURN-03
- ≠ 写云效 / 合 Master

## v1.3.16 — 2026-08-15

### 第四轮 KB↔AutoPRD 对表（evo-fy-kb-round4）

- 报告 [`references/kb-drift-2026-08-15-round4.md`](references/kb-drift-2026-08-15-round4.md)：救援任务 · 供应商管理 · 应收催款函
- KB：新建 `rescue-task` / `receivable-dunning`；补厚供应商（救援结算关系 + 二次态 Toast 禁令）；alias + manifest
- 作战室开 `DEF-ENERGY-SUP-01`（供应商查看/编辑 Toast）
- ≠ 写云效 / 合 Master

## v1.3.15 — 2026-08-15

### 第三轮 KB↔AutoPRD 对表（evo-fy-kb-round3）

- 报告 [`references/kb-drift-2026-08-15-round3.md`](references/kb-drift-2026-08-15-round3.md)：消息中心 · 故障处置 · 加氢订单 H5
- KB 回写：消息中心五端/业务键；故障 AI态分立+证明一期边界+P6 指针；加氢核对≠对账+手工台账门禁+禁真PLC假绿
- ≠ 写云效 / 合 Master

## v1.3.14 — 2026-08-15

### 第二轮 KB↔AutoPRD 对表（evo-fy-kb-round2）

- 报告 [`references/kb-drift-2026-08-15-round2.md`](references/kb-drift-2026-08-15-round2.md)：氢费账户/明细 · 任务工单 · 工作台待办
- KB 回写：氢费核对≠对账；工单 PRD 指针 **1.5.0**；工作台董事长 `116` + foundations 催办真相源；Autoprd 黄条
- 下一关：第三轮（消息中心·故障处置·加氢订单 H5）；≠ 写云效 / 合 Master

## v1.3.13 — 2026-08-15

### 双轨 P0/L0 裁决卡（evo-fy-dual-track-p0）

- 新增 [`references/dual-track-p0.md`](references/dual-track-p0.md)：P0 证据包；登录/组织属 P2；Vue 禁拷 React
- alias `dual-track-p0`；L0 升档表挂载；配对言出法随 v1.4.77 · 明镜 v1.0.4

## v1.3.12 — 2026-08-14

### 产线 MySQL 只读外部事实 cold-up

- 硬规矩：现网表/库归属先跑本机只读探针，报告见 `~/oneos-prod/docs/external-facts/`
- 禁写产线库；禁把连接口令写进本仓/答复正文；配对言出法随 v1.4.75 · `evo-prod-mysql-ro-coldup`

## v1.3.11 — 2026-08-14

### 四条进化任务落地（观测优化项）

- **evo-fy-eval-routine**：`eval-mini` §0 双周例行 + 首轮 15/15 Pass
- **evo-fy-kb-fresh**：三模块对表（租赁 / 组织通讯录 / 审核中心）；报告 `references/kb-drift-2026-08-14.md`；KB 已回写漂移点
- **evo-fy-alias-boost**：L0 + 模块别名加厚（AI审核/同人跳过 · Master合入 · 组织默认 · 字段副作用）；alias v1.1.2
- **evo-fy-code-level**：跨条线 §11 + 硬规矩 + eval-mini #13；无字典禁字段级假裁

## v1.3.10 — 2026-08-14

### 给分身边界 × 言出法随收口三行对齐

- 答复包「给分身边界」改为交棒码短格式：`W/S/C/B` + 做/不做（D/N）
- 分身收口第③行必须消费「是」项（habits §2.1 · `handoff-closeout.md`）
- 进化任务 `evo-cross-handoff` → done；减少漏回写作战室 / 评分 / Bad Case

## v1.3.9 — 2026-08-14

### 双 Skill 能力进化评分 · 给分身边界提醒

- 答复包「给分身边界」：触及 Skill 进化 / 能力短板 / 进化任务进展时，提醒分身更新 `skillCapabilities.ts` + publish:war-room
- 配对言出法随 habits §2.3 · v1.4.67；作战室首评法眼综合 **7.6 / 10**

---

## v1.3.8 — 2026-08-14

### AI-AGENT PM 一号位评分 · 给分身边界提醒

- 答复包「给分身边界」：触及一号位 / 组织默认 / 可观测 / AI 产品主线进展变化时，提醒分身更新 `aiAgentPmScorecard.ts` + publish:war-room
- 配对言出法随 habits §2.2 · v1.4.66

---

## v1.3.7 — 2026-08-13

### 生产环境参考 · 现网能力默不可砍

- 触发：组织通讯录对照生产时分身先抄钉钉习惯、漏复原现网编辑/设置
- 硬规矩：本尊甩 OneOS/YOS 生产作参考 → 无书面豁免不得裁掉现网编辑/设置/权限/状态机
- 配对言出法随 habits §3.0.6 · eval 26 · Rule `oneos-prod-logic-restore` · v1.4.59
- **KB 入库（同日）**：`00-cross-cutting-rules` §10；模块卡 `oneos-org-contacts`；alias L0「现网能力默不可砍」；eval-mini #11；重建 fayan 语料

---

## v1.3.6 — 2026-08-06

### 全局常驻协议（配对言出法随 v1.4.43）

- User Rule `yanchufasui-fayanruju-always`：业务/规则题默认走本 Skill 协议
- 个人 Skills 软链：`~/.cursor/skills/fayanruju` → 仓内单源（跨非 oneos 工作区也能发现）
- 废止「仅口令才加载」；纯闲聊仍可跳过

---

## v1.3.5 — 2026-08-04

### 仓库单源 · 跟 pull 更新（禁发文件夹）

- Skill 迁入 oneos-v2：`.cursor/skills/fayanruju/`
- 知识库单源：`src/resources/oneos-knowledge-base/`；Skill 内 `kb/` 为软链（不维护第二份拷贝）
- 跨机更新 = 拉仓 + 新开对话；**淘汰**整包拷贝 / rsync 发文件夹
- 同步当日 KB 口径后入库；`INSTALL.md` 改写为仓库通道

---

## v1.3.4 — 2026-08-04

### KB 全量并入 Skill（过渡；已被 v1.3.5 仓库单源取代）

- 曾将 KB 拷入 Skill `kb/` 解决跨机无仓问题
- v1.3.5 起改为仓内软链 + pull，不再以发 Skill 包为更新手段

---

## v1.3.3 — 2026-08-03

### 给分身边界 · 缺口入库提醒

- 答复包「给分身边界」：若缺口/待拍板/优化非空，须提醒言出法随写入作战室 `defects[]` 并 publish  
- 与言出法随 v1.4.18「沟通发现缺口入库」配对

---

## v1.3.2 — 2026-08-03

### 判定明白吗 + 迷你评测（Observe/Eval 轻量补齐）

- 答复包增加 **判定明白**；不明白 → `待拍板`/`缺上下文`，禁止猜裁  
- 新增 [`references/eval-mini.md`](references/eval-mini.md)（升档才读；约 10 条）  
- 本尊纠错口径时提醒分身写入 `eval-cases.md` 最近失败  
- 触发：本尊对照「生产级 Agent PM」文，要求两 Skill 补 Eval，不大跃进

---

## v1.3.1 — 2026-08-02

- 提速说明：禁止默认读 retrieval/voice；研发规则题可直调本 Skill（配合言出法随瘦启动）
- 补齐 **当前能力总览** 表；答复包「给分身边界」含作战室驾驶舱联动提醒（`warRoomData.ts`，落地仍归言出法随）
- 作战室 Skill 页展示副本：`oneos-project-war-room/data/skillCapabilities.ts`

---

## v1.3.0 — 2026-08-02

### 闭环五件套 + 租赁 v2.5.8f

- 答复包强制：**闭环 / 可行性 / 缺口 / 优化·更好办法**
- 新增 [`references/lease-v2.5.8f.md`](references/lease-v2.5.8f.md)（L0 定版摘要：G1–G10、主链阶段、缺口 N1/N2…）
- 冲突裁决：租赁以 v2.5.8f 为准；计费起算=业务确认，废止运维定计费/一车一账单
- 与言出法随 habits §2「闭环五件套」对齐

---

## v1.2.1 — 2026-08-02

- 开场签名对齐言出法随：**「王冕驱动 · 法眼如炬」**
- 下架战神金刚报幕 / 无敌帅类自夸（与分身 v1.4.3 同步）

---

## v1.2.0 — 2026-08-02

### 合体重装 · 正式更名「法眼如炬」

- 花名与言出法随配套；Skill ID / slash：**`fayanruju`**
- 主唤名：`法眼如炬` / `$法眼如炬` / `/法眼如炬` / `$fayanruju` / `/fayanruju`
- 旧 `wangmian-brain` / 「分身大脑」保留兼容重定向，勿再当主唤名
- 目录：`~/.codex/skills/fayanruju`；`~/.cursor/skills/fayanruju` → 同路径 symlink
- 答复包标题：`## 法眼答复`（旧「大脑答复」同等认）

---

## v1.1.0 — 2026-07-30

- 协议内联 `SKILL.md`：激活不再强制 Read `retrieval.md` / `voice.md`
- 分级读 L0→L3；定位改 Grep `kb-alias-index.tsv`，禁止默认整读 manifest
- KB 新增 `machine/kb-alias-index.{tsv,json}`；Skill `assets/` 同步瘦索引副本
- 新增 `scripts/smoke-system-qa.py`（系统使用问答 ×10）
