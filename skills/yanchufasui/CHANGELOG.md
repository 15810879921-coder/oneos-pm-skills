# 言出法随（yanchufasui）changelog

原名 wangmian-twin；自 v1.4.0 起正式更名。

## v1.5.2 — 2026-08-16

### 用途名版图 · 产品交付主入口（一期不上线）

- 团队主入口：`oneos-pm-product`（产品交付）；本目录保留为花名运行时
- 卫星：`oneos-qa-verify` / `oneos-ux-guide` / `oneos-release-gate`（休眠）/ `oneos-wave-router`
- 配对：`oneos-biz-rules` · `oneos-dev-delivery`；版图 `oneos-wave-router/SKILL-MAP.md`
- 本尊边界：发版上线自留；Skill 止于交开发→待测

## v1.5.1 — 2026-08-16

### 禁页头模块标题 + 标题下描述（DESIGN §2.4.0 升格）

- 本尊拍板：业务页顶栏模块标题与标题下描述**全部去除不保留**
- `DESIGN.md` §2.4.0 / `V2LedgerChrome` / `MigrateLedgerHub` / `oneos-ds-page-chrome.css` 同步
- Rules：`oneos-v2-copy-no-overexplain` · `oneos-v2-prototype-visual-align`；habits §3.0 条 7 / §3.0.4；eval **20**
- 详情/表单仍守 §4.8 业务页名（禁页名下描述）；口令门 / 汇报叙事 / Showcase 豁免口径写进 §2.4.0
- **标准包收口**：`references/no-page-title-chrome.md`（L0）· `evo-yc-no-page-title-chrome` done · 作战室能力卡 v1.5.1 / 综合 **8.8**（+0.1）

## v1.5.0 — 2026-08-16

### 三方联动可组装 · 交棒认 mj-receipt（配对明镜 v1.0.10）

- `handoff-to-dev`：模板增「视觉锚点」选填；§3 认偏差回写模板 + `mj-receipt`
- boot：口令速查指针 → 明镜 `twin-linkage` §0b
- 工程阻塞代挂触发词对齐 Vite 红屏 / `:5666`（仍禁无包改真码）

## v1.4.99 — 2026-08-15

### 产线握手恢复 · live DESC 通关（evo-yc-field-sidefx-desc）

- `prod-ro-probe.sh ping` 绿（MySQL 8.0.27）；出口当时 `45.196.236.77`
- 落盘：`ry-workflow` 62 表 + 全表 DESC；租赁/工单主表 live DESC
- `fed-modules-index` / README / habits 同步；任务 blocked→**done**
- 本机种子卡仅对照，不以之冒充产线

## v1.4.98 — 2026-08-15

### AI-PM 八维 · 双→三 Skill 协同指挥

- 展示名「双 Skill 协同指挥」→「**三 Skill 协同指挥**」（言出产品刀 · 法眼定口径 · 明镜真仓）
- ideal 同步；`id` 仍 `twin_orchestration`（历史快照兼容）
- habits §2.2 八维文案同步

## v1.4.97 — 2026-08-15

### 原型→现网像素对表门禁（evo-yc-proto-prod-visual-parity）

- 根因：工作台接入只做 IA 骨架，快捷折叠/自定义/预警行样式未复原；误把「禁拷 React」当成「禁拷视觉」
- habits **§3.0.8** + Rule `oneos-prototype-prod-visual-parity.mdc`
- 交棒禁止笼统「对等不像素抄」；须逐控件对表清单

## v1.4.96 — 2026-08-15

### 跨入口 B1 存量对齐（evo-yc-secondary-b1-align）

- 销 `DEF-PLT-SECONDARY-B1-ALIGN`：公共 `src/common/b1-cross-nav.ts`（`openB1Prototype` / `B1_TARGET`）
- 车辆档案履约/保险：Toast「即将跳转」→ 独立原型真链
- H5 工作台：待办按审核/交车/年审链对应独立 H5；去掉 Toast 装跳
- legacy：`oneos-web-business` 客户/供应商/ETC；旧 `LeaseContractManagement.jsx` 交还车/应收结
- Web 工作台 `oneos-web-workbench-new` 本已 href，保持 B1

## v1.4.95 — 2026-08-15

### 二次态必做满（evo-yc-secondary-panel · 本尊拍板）

- habits **§3.0.7**：模块内 list/detail/edit 强制 PRD 二次页清单 + 状态机 + 标注状态节点 + 必点清单；禁 Toast 冒充内页
- Rule `one-prototype-one-sidebar` 硬澄清：**同页 ≠ 可不做内页**
- eval **38**；交棒 `handoff-to-dev` 增「同页二次态」节
- **轨道 B**：明镜 **v1.0.9** 拍默认 **B1**（独立原型目录链跳）；存量整改已由 **v1.4.96** 销账

## v1.4.94 — 2026-08-15

### 法眼第二轮 KB↔AutoPRD 对表（evo-fy-kb-round2）

- 报告 `fayanruju/references/kb-drift-2026-08-15-round2.md`；KB 回写氢费核对≠对账 / 工单 1.5.0 / 工作台 foundations 总闸
- 作战室销账 + `nextAutoSyncGoal` → 第三轮（消息中心·故障处置·加氢 H5）；≠ 写云效 / 合 Master

## v1.4.93 — 2026-08-15

### 本机灌 ln_asset_management 结构旁证（evo-mj-asset-schema-fill）

- `~/oneos-prod/scripts/seed-local-asset-schema.py`：实体粗 DDL + 仓内 SQL → 本机 **157 表**；主链优先 8/8
- 双轨 `localAssetSchema=ready`；`module-asset-local-schema.md`；≠ 产线 live DESC
- 下一关：法眼 KB 第二轮对表；≠ 写库 / 合 Master

## v1.4.92 — 2026-08-15

### 作战室 · 资产 DESC 产线只读握手旁证（evo-dual-track-asset-desc-handshake）

- `refresh-dual-track-auto` → `assetDescHandshake`；双轨页专卡
- 再核：TCP 通 · greeting 超时 · ERROR 2013；dump/模块卡表级旁证；禁装 live 假绿
- 下一关：本机灌 ln_asset_management 结构旁证；≠ 写库 / 合 Master

## v1.4.91 — 2026-08-15

### 作战室 · 缺口↔云效只读对表（evo-warroom-defect-yx-align）

- `warRoomDefectYunxiaoAlign` 纯计算旁证 + 大盘 AlignStrip（命中/未命中/样本差）
- 禁自动改 defects；样本非全量诚实；下一关：资产 DESC 产线只读握手；≠ 写云效

## v1.4.90 — 2026-08-15

### 作战室 · 自进化链收口盘点（evo-warroom-auto-sync-closeout）

- `warRoomAutoSyncChain` 五环清单 + 大盘 `WarRoomAutoSyncCloseoutStrip`（可复制）
- 4 通关 / 双轨半通诚实；下一关：缺口 ↔ 云效打开项只读对表；≠ 写云效 / 合 Master

## v1.4.89 — 2026-08-15

### 作战室 · 双轨/AI 评分页角标跳转解释（evo-warroom-dual-ai-scope-jump）

- 共享 `ScopeExplainChip`；双轨 / AI-PM / AI 开发评分页均可点「解释 ›」→ 本页溯源条展开+焦点
- 下一关：自进化链收口盘点；≠ 写云效

## v1.4.88 — 2026-08-15

### 作战室 · Skill 页角标跳转解释（evo-warroom-skill-scope-jump）

- SkillFixRecordPage 角标「解释 ›」→ 本页溯源条展开 + skill_fix_log 焦点
- 下一关：双轨/评分页角标同跳；≠ 写云效

## v1.4.87 — 2026-08-15

### 作战室 · KPI 角标跳转口径解释（evo-warroom-kpi-scope-jump）

- HeroKpi ScopeTag「解释 ›」→ 溯源条展开 + 焦点高亮；补完成度/覆盖率 Q&A
- 下一关：Skill 页角标同跳；≠ 写云效

## v1.4.86 — 2026-08-15

### 作战室 · 三口径一键解释（evo-warroom-triad-explain）

- `WAR_ROOM_TRIAD_EXPLAIN` + 溯源条展开误读/正解/Q&A + 复制全文
- 下一关：KPI 角标点开跳转解释；≠ 写云效

## v1.4.85 — 2026-08-15

### 作战室 · 新鲜度黄/红督促动作（evo-warroom-freshness-urge）

- `WarRoomFreshnessUrgeBar`：人工 + 事实条 + 双轨三路最差档；复制刷新口令；策略常显
- 下一关：驾驶舱三口径冲突一键解释；≠ 写云效 / 合 Master

## v1.4.84 — 2026-08-15

### 明镜技术顾问旁路代挂（配对明镜 v1.0.5）

- 本尊：产品经理；工程题须自动有「明镜建议」，无需再喊 `/明镜止水`
- boot：工程阻塞同轮挂建议段；升档表加明镜 §0c / twin-linkage §2b
- 硬闸：顾问旁路 ≠ 无交棒改真码

## v1.4.84 — 2026-08-15

### 作战室 · 资产表结构有限字典探针（evo-dual-track-asset-schema-probe）

- `asset-api`：Controller + 模块 dirs + fed 字典卡/表清单；产线 DESC BLOCKED 诚实；mock≠表
- 下一关：外部事实条新鲜度告警动作；≠ 合 Master

## v1.4.83 — 2026-08-15

### 作战室 · 组织/权限对照探针（evo-dual-track-org-role-probe）

- `org`：钉钉审计 JSON + 原型通讯录 vs ruoyi-system User/Role/Dept + Web 页；人事主同步诚实 MISS
- 下一关：资产 API 表结构有限字典探针；≠ 合 Master

## v1.4.82 — 2026-08-15

### 作战室 · 工作台待办规则对照探针（evo-dual-track-workbench-todo-probe）

- `workbench-todo`：董事长 116 闸 + §0.4 催办白名单 vs 现网 todoRemind / admin 催办 GAP
- 下一关：组织/权限角色对照探针；≠ 合 Master

## v1.4.81 — 2026-08-15

### 作战室 · 台账密度 + 审核链探针加深（evo-dual-track-probe-deepen）

- 契约新增 `ledger-density`；`approval` 验 Gate / V2ApprovalProgress / WarmFlow API / popover
- P1/P3 波次证据同步；下一关：工作台待办规则对照探针；≠ 合 Master

## v1.4.80 — 2026-08-15

### 作战室 · 交棒回执刷波次半自动（evo-dual-track-handoff-waves）

- `refresh-dual-track-auto` 扫 `handoff-mj-*`；回执通过→波次建议 done；禁 Skill 模板误匹配
- 双轨页展示交棒证据；`nextAutoSyncGoal` → 加深 FS/现网探针；≠ 合 Master

## v1.4.79 — 2026-08-15

### 扩喂租赁/工单/氢能模块字典（evo-yc-field-sidefx-expand）

- `~/oneos-prod/docs/external-facts/`：`fed-modules-index.md` + `module-lease-contract.md` + `module-work-order-ops.md` + `module-hydrogen-energy.md`
- 从既有 asset dump 拆出可答主链表（含 `task_work_order`）；产线 TCP 通但握手 2013 → **未**装 live DESC 假绿
- `ry-workflow` 仍标未喂；下一关 `evo-yc-field-sidefx-desc`
- 能力评分 8.6→8.7；habits 已喂清单同步

### 字段 DESC 关 · 产线握手 blocked（同日）

- 再核：TCP 通、MySQL 问候包超时 → `ERROR 2013`；任务 **blocked**（不装通关）
- 旁路：本机 `ry-workflow` 13 表 DESC → `module-workflow-local-schema.md`（标明 ≠ 产线 live）
- 请本尊解白名单 / VPN / 跳板后喊「握手好了」再补产线 live DESC

## v1.4.78 — 2026-08-15

### 字段/表结构副作用：planned → 有限模块可答（evo-yc-field-sidefx）

- 证据：`~/oneos-prod/docs/external-facts/` 已喂 `ln_asset_management` / `ln_energy_v2` / `ry-cloud` 表清单 + 匹配报告（配对 v1.4.75 MySQL RO）
- 能力表：`planned` → **ready（有限模块可答）**；进化任务 done；新增扩喂任务 `evo-yc-field-sidefx-expand`
- 硬闸不变：未喂模块仍禁字段级假裁；**禁止**冒充全库 ready
- habits §2 升档注记；eval **33** 升档自检；作战室评分 8.5→8.6

## v1.4.77 — 2026-08-15

### 交棒波次边界 + P0 证据包（evo-yc-handoff-wave-id）

- `handoff-to-dev`：§1b 波次禁并刀；§2b P0 证据包；模板强制波次 ID + 通关证据清单
- 本尊「都要」：P0 勾齐 + E1–E3；配对法眼 dual-track-p0 · 明镜 VPN 闸

## v1.4.76 — 2026-08-15

### 外部事实条 · 测试计划 + 流水线部署旁证

- `war-room:refresh-facts` 接 test-hub 计划进度 + flow 最近部署（web/asset/energy/system/gateway × test/prod）
- `DEF-PLT-WARROOM-03` resolved；进化任务 `evo-warroom-test-deploy-facts` done
- 旁证 ≠ 正式 `oneos.qa-evidence` 清单哈希；仍禁写云效

### 双轨契约 / 仓栈只读自动回写

- `refresh-dual-track-auto` → `dualTrackAutoFacts.ts`；串进 `war-room:refresh-facts`
- 契约状态 + 仓栈 HEAD 本机探针；`DEF-PLT-DUAL-01` / `evo-dual-track-contract-auto` done
- 波次仍人工；≠ 无人值守合 Master

### 双轨波次半自动建议

- 同脚本增 P0–P7 证据启发（齐/半/缺 + done/doing/todo/locked）
- 双轨页对照「半自动 vs 人工态」；`evo-dual-track-wave-auto` done
- ≠ 合 Master；交棒回执刷波次仍可下一关

### 外部事实条 · 产线 Codeup 合入摘要

- 本尊拍板 A+B：`war-room:refresh-facts` 接 `~/oneos-prod` 浅克隆只读（`ln-cloud` + `ln-asset-management` + `ln-energy-v2`）
- 事实条 UI 展示合入；进化任务 `evo-warroom-codeup-facts` done
- habits §2.4 同步；仍禁写云效

## v1.4.75 — 2026-08-14

### 产线 MySQL 只读外部事实 cold-up

- 本尊提供远程库后：本机探针 `~/oneos-prod/scripts/prod-ro-probe.sh` + 协议/匹配报告 `docs/external-facts/`
- 密钥仅 `~/oneos-prod/.secrets/`（不进 oneos-v2）；硬闸禁写产线
- boot §4/§5 升档；作战室能力表 + 进化任务 `evo-prod-mysql-ro-coldup` done；配对法眼 v1.3.12

## v1.4.74 — 2026-08-14

### 交棒明镜止水（AI 开发分身）

- 新建 [`handoff-to-dev.md`](handoff-to-dev.md)：C 轨双轨交棒包模板；与 `.cursor/skills/mingjingzhishui/` 配对
- 分家：正式原型+真码归明镜；言出法随窄例外纯文案/样式；未唤明镜仍可按旧习惯改原型
- boot §4/§5 升档；habits **§5.0**；能力表挂交棒一行；eval **37**

## v1.4.73 — 2026-08-14

### 云效拉取 · 甘特计划起止强制对表

- 根因：ONEOS-537 等云效「计划开始/计划完成」已改，甘特仍旧日期 + 14 天硬裁切静默吃掉 08/27
- habits PM Mode + `pm.md` **§9.6**：拉云效必须核对 79/80；有更新同轮写 `ganttDeliveryTree`；空完成日不脑补；轴可拉伸；seed 甘特优先于 localStorage
- 原型：`pm-weekly-sync-board` 同步 537→08/10–08/27、545/546→08/11–08/18；存储键 v24；eval **36**

## v1.4.72 — 2026-08-14

### 法眼「给分身边界」× 收口三行对齐（evo-cross-handoff）

- 新建 [`handoff-closeout.md`](handoff-closeout.md)：交棒码 W/S/C/B + 收口③强制消费
- habits §2.1 收口三行改为对齐模板；法眼 v1.3.10 答复包短格式同步
- 减少漏回写作战室 / AI-PM 评分 / 双 Skill 能力 / Bad Case；eval **35**

## v1.4.71 — 2026-08-14

### 按双 Skill 优化建议强化（本尊拍板）

- **研发 onboarding（evo-yc-rd-onboarding · C+边界）**：新建 [`rd-onboarding.md`](rd-onboarding.md)；`audience-role` / `boot` §5–§6 默认挂分诊+一任务一支；闲聊不挂、只要结论一句指针、用法/合支/首次确认挂 §0–§2；eval **32**
- **字段副作用协议（evo-yc-field-sidefx · 2A）**：habits 升「有限可答」闸——模块级可答、无字典禁字段级假裁决、喂字典后升档；能力仍 ⏳；eval **33**
- **周五 5 黄金例套 A（evo-yc-eval-auto）**：`eval-cases` §0.1 固定 **1·19·31·30·23** + 复现清单；habits §2.1 周五强制；eval **34**
- **Master 桥（evo-yc-dev-master-bridge）**：本尊豁免本轮（交开发 Skill 侧整理）

## v1.4.70 — 2026-08-14

- **决策层汇报 · 禁部门内部管理要求**：`进度看得见、延期说得清`、**`任务按周拆解、过程留痕`**（及同义）、**整节「协同机制」**（跟踪粒度/信息同步/零散待办）属部门内部结论/要求，只留对内；向董事长汇报不得提及；对外只写业务结论与事项；habits §2 · Rule `pdf-report-plain-language` §F · eval **30**；作战室能力表已挂。

## v1.4.69 — 2026-08-14

- **作战室外部事实条**：`war-room:refresh-facts` 只读云效 + 本仓 Git → `warRoomExternalFacts` + 大盘条；Codeup 产线另开 DEF-PLT-WARROOM-03；habits §2.4。

## v1.4.68 — 2026-08-14

- **作战室数据溯源 / 三口径 / 新鲜度**：`warRoomDataProvenance.ts` + 页顶条；主链闭环 ≠ 产品缺口 ≠ Skill 修复记录；habits §2.4；进化任务 `evo-warroom-live-facts`。

## v1.4.67 — 2026-08-14

### 双 Skill 能力进化评分（作战室）

- 触发：本尊要求给言出法随/法眼如炬做能力值评估、优化建议与进化任务督促
- habits **§2.3**：数据 `skillCapabilities.ts`（八维 + optimizeSuggestions + SKILL_EVOLUTION_TASKS + buildSkillWhipState）
- 展示：Skill 修复记录 → 督促条 + 评分卡；能力清单默认折叠
- 口令：更新双 Skill 评分 / 跑 Skill 进化复评；禁拍马屁涨分；同轮 publish:war-room
- 首评：言出法随综合 **8.1** / 法眼如炬综合 **7.6**

---

## v1.4.66 — 2026-08-14

### AI-AGENT 产品经理 · 一号位多维评分（作战室）

- 触发：本尊要求挂作战室监测 AI-AGENT PM 各维进度，分身持续客观更新
- habits **§2.2**：数据 `aiAgentPmScorecard.ts`；顶栏「AI-PM 评分」；触发复评 + publish:war-room；禁拍马屁涨分
- 法眼答复包「给分身边界」提醒跟进；首评综合 **7.2 / 10**

---

## v1.4.65 — 2026-08-13

### 公网链 · 先 publish 再贴 + 禁尾斜杠（根因门禁）

- 触发：方案页交付写 `http://prototype…/v2/{id}/` → OSS 目录无 index 自动跳转 → XML `NoSuchKey`；且未同轮 publish
- habits **§2** · Rule `oneos-external-link-smoke` · eval **19**
- 强制：聊天/邮件/产物贴公网链前 `publish:oss`；URL 必须 `…/index.html`；对粘贴原文冒烟 200

---

## v1.4.64 — 2026-08-13

### 总监向对外汇报范式（硬门禁）

- 触发：总监对齐「自上而下、结论先行、改点→改完」；禁新旧整页并排抢视线
- habits **§2** · Rule `pdf-report-plain-language` **§E** · eval **29**
- 开篇三卡；分节骨架；对内/对外分离；完成标准 + 职责到部门

---

## v1.4.63 — 2026-08-13

### 汇报页禁布局自解说（硬门禁）

- 触发：汇报对照页写「左边是眼下…右边是改完…不用来回切」——给汇报对象看无意义，属布局自解说
- habits **§3.0 条 7** / **§3.0.4 条 10**：差异用视觉标（虚线红框 / 浅底 / 「拟去掉」）；禁教版式常驻文案
- Rule `oneos-v2-copy-no-overexplain` · eval **20c** · 作战室能力表同步

---

## v1.4.62 — 2026-08-13

### 台账首列字号 / 入口结构（硬门禁）

- 触发：组织通讯录把「姓名」染成主色下划线 +「查看 ›」，工号灰字副行；与车辆/合同台账对不上
- habits **§3.0 条 9**：有主键 → 上行 13/600 ink 只读 + 下行 `DetailEntryLink` mono；无主键 → 名称单行入口；td 吃 `--ln-table-*`；禁 `ui-monospace`
- visual-align **6 / 6b** · eval **28** · 作战室能力表同步

---

## v1.4.61 — 2026-08-13

### 仓库单源 · 跟 pull 更新（禁发文件夹）

- Skill 迁入 oneos-v2：`.cursor/skills/yanchufasui/`（与法眼 v1.3.5 同通道）
- 本尊机 `~/.cursor/skills/yanchufasui` / `~/.codex/skills/yanchufasui` → **软链到仓内**；禁止再维护第二份实体拷贝
- 新增 [`INSTALL.md`](INSTALL.md)；跨机更新 = `git pull` + 新开对话
- 作战室能力表源指针改为仓内双 Skill

---

## v1.4.60 — 2026-08-13

### 横滚必右粘操作列（硬门禁）

- 触发：组织通讯录成员表横滚时「查看/编辑」滚出视口
- habits **§3.3**：台账会出现横向滚动时操作列 `th`+`td` 必须 `sticky-right`（或 Ant `fixed`+`scroll.x`）；窄表无横滚禁乱 fixed
- visual-align **6c** · eval **27** · 作战室能力表同步
- 组织通讯录：`is-scroll-wide` + sticky-right 落地

---

## v1.4.59 — 2026-08-13

### 生产环境参考 · 强制完整复原 OneOS 业务逻辑

- 触发：组织通讯录对照 `lnoneos.com` 时先按钉钉习惯改 IA，漏复原现网编辑/设置/账号角色等
- habits **§3.0.6**：甩生产 URL/「按现网」→ 先摸底 + 现网能力对照表进 PRD，再改交互；禁默删未豁免能力
- boot 摘要 + SKILL 硬规矩 + eval **26** + 仓内 Rule `oneos-prod-logic-restore` + 法眼配对裁决
- 作战室能力表同步 + 审计 LOG + publish

---

## v1.4.58 — 2026-08-13

### PC/看板主区禁贴边

- 触发：加氢站日报主壳 `padding: 0 0 32px` → 左上/右侧贴边
- habits §3.0 条 8 + Rule `oneos-v2-design-system` 3b + visual-align 表项 0；eval **25**
- 修复：站日报对齐 B1 / 能源 BI `.ehb-body`（PC 20×24 / H5 16）
- **补丁（同日 · 本尊点头）**：详情 `width:100%` + `content-box` 白卡右侧溢出假绿；条 8 / Rule / eval 25 补「壳内 border-box + 验主卡右缘 inset」；禁只 Grep padding 通关

---

## v1.4.57 — 2026-08-13

### 作战室虚拟形象定妆恢复

- 本尊：把定妆形象挂回全局项目作战室「双 Skill 能力总览」言出法随卡**最上方**
- 资产：`oneos-project-war-room/assets/yanchufasui-avatar.png`
- `boot.md` §0b：作战室展示定妆；聊天唤名默认仍不出图（省 token）
- 作战室 `skillCapabilities` / `SkillCapabilityCard` + 审计 LOG + `publish:war-room`

---

## v1.4.56 — 2026-08-13

### 批注连改 / 跨午夜禁止漏记审计 LOG

- 触发：氢能 BI 批注连改跨午夜，审计表空档；本尊红框旁观
- 根因：每刀当「小样式」跳过 v1.4.44；无「连改收口」闸门
- habits §2 补强：≥3 刀同模块 / 会记开干 /「继续本会话」/ 跨日 → 收口前合并 1～3 条 LOG + publish；交付报「审计LOG：已写 N 条」
- boot 摘要 + eval **22b** + 作战室能力表同步

---

## v1.4.55 — 2026-08-12

### 禁过度指引 · 彻底封死 + 现结台账补齐

- 本尊：过度提示这条路**彻底封死**；再犯 = 交付失败
- habits §3.0 条 7 / §3.0.4 · Rule `oneos-v2-copy-no-overexplain`：明确禁**政策色块 / 体系说明 banner**；eval **20** 升级
- 站日现结：删说明书墙；列名「登记日期」；变更日志 + 批量导入/导出；可改可导
- 作战室能力表同步本条

---

## v1.4.54 — 2026-08-12

### 虚拟形象整条下线

- 本尊：言出法随**不做虚拟形象**；定妆出图能力废止
- `boot.md` §0b 改为废止声明；§7 去掉出图步骤
- `SKILL.md` 能力表/自我介绍/明确不做同步；删除 `assets/` 下定妆图与 AVATAR_* 文稿
- 作战室 `skillCapabilities` 去掉「显式唤名强制出定妆」条目

---

## v1.4.53e — 2026-08-12（已废止 · 见 v1.4.54）

### 定妆锁定 + 唤名动图假绿修复（历史）

- 曾：崩铁卡通风定妆 + data URI 动图出图；**v1.4.54 起整条不做**

---

## v1.4.53d — 2026-08-12

### 定妆迭代 · 去痣 + 崩铁卡通风

- 本尊：脸上无痣；风格更卡通，对齐崩坏：星穹铁道人物立绘感
- 仍保留：大衣 + 黑丝衬衣、雪山、严肃、非黑框银钛细框眼镜
- 重出 idle/blink/talk + GIF 覆盖 assets

---

## v1.4.53c — 2026-08-11

### 定妆迭代 · 大衣黑丝衬衣 + 雪山 + 更严肃帅气

- 本尊点改：高端大衣 + 黑丝衬衣；背景雪山；表情更严肃；眼镜非黑框（银钛细框）；整体更帅
- 重出 idle/blink/talk + GIF，覆盖 `assets/yanchufasui-*`

---

## v1.4.53b — 2026-08-11

### 定妆换脸 · 本尊本人照基底

- 本尊提供本人自拍 → 按原定妆插画风重出 idle/blink/talk + `yanchufasui-avatar.gif`
- 旧女版静帧备份 `assets/yanchufasui-idle-legacy-female.png`
- 聊天出图仍走 §0b：**Read PNG idle**（Cursor 内嵌）

---

## v1.4.53a — 2026-08-11

### 定妆出图纠偏 · Cursor 必须 Read PNG

- 本尊截图打回：只 Read GIF → 界面显示「Explored …gif」、聊天框**无图**，却口头说「上面那张」= 假绿
- §0b 改为：**优先 Read `assets/yanchufasui-idle.png`** 才能内嵌；GIF 保留作本机动态附件路径
- 禁止「Explored GIF + 口头有图」交差

---

## v1.4.53 — 2026-08-11

### 显式唤名 · 聊天框强制出定妆图

- 本尊：调用言出法随 → 聊天框自动出图（不要口头有图）
- `boot.md` 增 **§0b**；§7 首条顺序插入先 Read 定妆资产
- 触发：口令/唤名/Skills 挂载/自我介绍；**不**在全局常驻静默续聊每轮刷图
- 定妆 Read 不受「同会话已读勿重读」限制；对外大屏/PDF 仍不挂
- **v1.4.53a**：Cursor 出图改 PNG（见上）

---

## v1.4.52 — 2026-08-08

### 项目经理数字人 · 周报同步（pm.md §9）

- 本尊授权：言出法随代位项目经理梳理；口令「周报同步 / 会议纪要入库 / 会后确认」
- 强制提问序：进展 → 缺口/断头/卡顿；会后 P0/P1/P2 + 分歧；默认同步靶=`pm-weekly-sync-board`（`divergences`）
- **禁**默认同步作战室销账、写云效；boot/habits/eval #24 已挂

---

## v1.4.51 — 2026-08-08

### 汇报大屏 · 对外禁内部对齐口吻

- 触发：本尊纠正服务群汇报舱——「叙事收口 / 故障机器人路径 / 跟进要点 / 验收排除」是内部对齐，不是给老板看的
- **定位**：驾驶舱 / 汇报大屏默认**向外汇报**
- 仓内 Rule `pdf-report-plain-language.mdc` 增 **§C**；habits §2 扩 v1.4.34 → 叠 v1.4.51；boot 瘦摘要同步
- Fail = 大屏可见内部对齐话术

---

## v1.4.50 — 2026-08-08

### H5 图表与看板 6 大展示硬门禁（habits §3.0.2 条 15）

- 触发：本尊连查 H5 看板 6 案（列表展开重叠、柱图太密、提示跨行、KPI 4列强挤、顶部黑框/返回按键截断、图表 Header 图例与单位折行打架）。
- 6 大展示硬门禁：
  1. 趋势柱图固定舒适宽 46px + 原生平滑横滚与滑动引导，顶底数值与日期 100% 独立居中；
  2. 提示文案短句分流（`ehb-show-h5` vs `ehb-hide-h5`）+ 单行截断，彻底告别跨行打架；
  3. KPI 指标卡片重构为 2×2 网格，宽增至 165px+，舒展对齐不溢出；
  4. 钻取 Modal 顶端 Safe-Area 锚定 + `align-items: flex-start` + `height: 100dvh`，100% 确保返回按钮与标题完整露显；
  5. 图表 Header 上下分行，标题独占，图例与单位两端对齐；
  6. 钻取树多行自适应与横滚，取消 fixed，第一列 min-width 250px 允许 2-3 行自动换行与紧凑缩进。
- eval **6k**；能力表与 SKILL.md 同步。

---

## v1.4.49 — 2026-08-07

### 时生亮表区独立滚 · 非 H5 全仓扫挂

- 触发：本尊「V2 仓所有 H5 外表格扫一遍；嵌入后约 10 条/屏；拖表不拖整页」
- 共用：`src/common/v2-migrate-ledger/ledger-viewport-fill.css`（`migrate-ledger` / `ledger-page` / 车辆资产 / bfcl / 故障 / 工单 等入口 `@import`）
- 根类：`.v2m-page`/`.bfcl-page` 默认；`.ldb-page`/`.lc-page--list-dense`/`.ct-list-shell`；其余列表加 **`is-ledger-fill`**；特例 `is-page-scroll`
- 外壳：`oneos-shell-content` 对上述根盖回 `height:100%; overflow:hidden`
- Habits §3.3 补「全仓挂法」；能力表同步

---

## v1.4.48 — 2026-08-07

### 未预览严禁通关 + 表区独立滚入规范（放权干漂亮）

- 触发：本尊「放权给你干活，要干漂亮不是光干」；合同模板漏挂表区独立滚仍假绿交差
- **§3.0.5**：改 UI 须真预览；交付必报「路径 + 必点清单已绿 + 风险」；禁 Grep/HTTP 假绿；改前必报对照母版
- **§3.3**：时生亮表区独立滚 / sticky 表头 / 白卡撑满 / 禁仅 overflow-x / 非 v2m 根必自挂
- `boot.md` 瘦摘要一句；eval **23**；能力表同步

---

## v1.4.46 — 2026-08-06

### H5 交互自检破假绿 · 列表加载 + 浮层限壳（§3.0.2 条 14）

- 触发：本尊「不是让你做完自检吗」——故障 H5 删分页后筛选仍 `fixed` 飞出手机壳；注释写 Bottom Sheet 当通关
- 根因：① 自检门禁过窄只验分页关键字 ② 注释/Grep ≠ 壳内几何 ③ 自写遮罩不进 `h5-shell.css` 自动降级
- 硬门禁：H5 长列表滑到底加载；浮层 absolute/Portal 限壳；375/390 真点筛选；Rule `oneos-h5-interaction-selfcheck`
- 修复同轮：故障 H5 筛选/确认/Toast → absolute + `.v2-h5-phone`/`.v2-h5-body`；eval **6j**

---

## v1.4.45 — 2026-08-06

### 详情 / 表单 KV 禁跨列（habits §3.5 扩写）

- 触发：本尊红框故障详情「运营公司」与「运营城市」之间空坟场
- 根因：`v2-fh-drawer-kv-item--wide` → `grid-column: span 2`，宽屏多占一轨像缺字段
- 硬门禁：筛选 **与** 详情/表单 KV **一律一格一项**；禁 `span` / `--wide` 给长文案腾地（用 ellipsis + title）
- 修复：故障详情去掉公司 `--wide`；CSS 废止 span；eval **10** 扩 KV

---

## v1.4.44 — 2026-08-06

### 销账同轮写审计 LOG（habits §2）

- 触发：本尊旁观「按时间回溯」只见白屏一条，实际昨晚已修多缺口；根因只改 `status: resolved` 未写 `WAR_ROOM_AUDIT_LOGS`
- 硬门禁：`resolved` 销账 / 可回溯体验闭环 → **同轮**追加审计 LOG（最新在上）+ `publish:war-room`
- Fail：只改 defects 状态、审计表漏登 = 未完成
- 同步：`boot.md` 作战室一句；仓内 Rule `war-room-s3-sync` 补销账写 LOG；eval **22**

---

## v1.4.43 — 2026-08-06

### 全局常驻 · 言出法随 + 法眼如炬（瘦启动）

- 触发：本尊要求聊天**自动带**这两套 Skill，无需口令
- 落盘：全局 User Rule `~/.cursor/rules/yanchufasui-fayanruju-always.mdc`（alwaysApply）  
  → 每聊强制 Read `boot.md`；法眼按题型升档；禁止六连读塞进 Rule
- 法眼进个人 Skills：`~/.cursor/skills/fayanruju` → 仓内 `.cursor/skills/fayanruju`（symlink）；`~/.codex/skills/fayanruju` 同链（修 boot 相对路径）
- 废止「未喊口令不启用」；口令改为显式加码
- 验收：新开 Chat 后无需 `/yanchufasui` 也应走分身瘦启动

---

## v1.4.42 — 2026-08-06

### 调试条出展示区 · 双写 Rule + habits（§3.0.2 条 13）

- 触发：本尊要求以后**所有页面**调试条移出原型展示区，防研发 AI 误判为功能；并评估约束落点
- **评估结论**：仅写分身不够（未喊口令的 Agent 不读 habits）→ **alwaysApply Rule** 拦全体 + **habits 同步**（本尊点选）
- 落盘：`.cursor/rules/oneos-prototype-debug-chrome.mdc` · habits 条 13 · eval **6i**
- Fail：调试条叠壳/页头/画布 = 未完成（不要求同轮全仓迁完旧页，**新建/改到的页强制合规**）

---

## v1.4.41 — 2026-08-06

### 禁上下同义双 Tab + 调试条出壳（habits §3.0.2 条 12）

- 触发：本尊指出故障 H5 顶部分段与底栏同功能重复；2×2 吸底不像 App；调试条叠展示区误导研发 AI
- 纠偏：同功能只留底栏；吸底优先「主+次+更多」；调试条置于产品展示区外并标 `PROTO DEBUG · 非产品 UI`
- Fail：上下双 Tab / 调试条叠手机壳页头 = 未完成

---

## v1.4.40 — 2026-08-06

### H5 吸底窄屏不裁钮 · 禁 Grep 假绿（habits §3.0 条 6 / §3.0.2 条 11）

- 触发：本尊截图怒斥「转交转到哪里去了？」——四钮单行挤爆 375，最右「转交」只剩半个字；分身此前只报 HTTP200+Grep 通关
- **未自检根因**：把「组件挂上」当「画面可用」；缺 375/390 真预览最右 CTA 入框检
- 纠偏：≥3～4 吸底钮须 **2×N 宫格**（或外侧≤2+更多）；交付必须窄屏真预览；eval **6h**；Rule `oneos-v2-no-diy-ui` 同步
- Fail：Grep 绿但窄屏裁钮 = 未完成

---

## v1.4.39 — 2026-08-06

### ActionBar 子钮硬 Grep + 名单选人禁手输（habits §3.0 条 6 / §3.0.2 条 9–10）

- 触发：本尊点故障 H5「转交」仍是手输姓名；处置台吸底自造紫钮 + `fixed`；要求检查规范缺口并写机制防再犯
- 纠偏：
  - `V2MobileActionBar` 内主次 CTA **必须** `V2Button` 子节点（禁 ActionBar 内 `<button style>`）
  - 转交/派工名单选人：禁 textarea 手输；PC `V2Select searchable`；H5 `V2Select`
  - 吸底与滚动区须 flex 兄弟，禁塞进 `overflowY:auto` 末尾凑合
- Rule：`oneos-v2-no-diy-ui.mdc` 同步补「ActionBar 子钮 + 名单禁手输」
- eval：**6f** 扩写 · 新增 **6g**
- Fail：ActionBar 内自制按钮皮 / 转交用手输姓名 / 末条被挡 = 未完成

---

## v1.4.38 — 2026-08-05

### 台账连体白卡硬检（habits §3.3）

- 触发：本尊指出客户服务群绑定列表「背景卡片丢失」——筛选有白卡、表体掉灰底
- 根因：空挂 `is-filters-open` 拆缝 + 表格只有 `table-wrap`、缺 `table-section.is-connected`
- 纠偏：habits §3.3 增「台账连体白卡」行 + 交付自检；仓内 Rule `oneos-v2-prototype-visual-align` #5 补强
- Fail：列表筛选项有白底而表体直接躺灰画布 = 未完成

---

## v1.4.37 — 2026-08-05

### 禁止危险全仓机械替换 + 捞档后导出冒烟（habits §3.2 条 3c）

- 触发：清 Toast「原型演示」误全仓替换清空 `()`；`git checkout -- src/prototypes` 冲未提交工作；Local History 捞档致 import/export 版本拧巴 → 大量 `does not provide an export named …`（例：车辆资产 `LIFECYCLE_HIGH_FREQUENCY_STAGES`）
- 裁决：**不是**「禁过度指引」文案规范导致，属救援操作失误
- 纠偏：habits §3.2 **条 3c**；禁碰 `()` 的全仓清理；禁未备份整树回滚；捞档后强制命名导出一致 + B/C 冒烟；eval **21**
- Fail：捞档后仍 export 断裂 / 用整树 checkout 冲未提交工作 = 未完成

---

## v1.4.36 — 2026-08-05

### 禁过度指引文案（habits §3.0 条 7 / §3.0.4）

- 触发：本尊指出功能标题下堆大量描述导致页面混乱
- 纠偏：保留台账 ≤3 段副文案 / 门禁一句 / 防错 hint；禁说明书墙与内部演示词进 UI
- 落地：habits §3.0.4 · DESIGN §2.4.0b · Rule `oneos-v2-copy-no-overexplain.mdc` · eval **20**
- 同轮：P0 清场（工单详情/新建、H5 工单、物流自营页脚、自营台账 hint、车辆资产 H5 副标、收款中枢、运维指派弹窗）

---

## v1.4.35 — 2026-08-05

### 附加外链 · 自动冒烟 + 报错自修（habits §2）

- 触发：本尊——汇报舱 H5 外链 `NoSuchKey`；纠正「不是没发 OSS，是人工发的链」；要求以后贴外链须分身自检页面是否正常，报错主动修，勿提醒本尊去验
- 根因：分身改链后未对目标 URL 冒烟；误判「没发布」甩检查；未把「人工发过 ≠ 该路径 200」写进门禁
- 纠偏：habits §2 新条 + 仓内 Rule `oneos-external-link-smoke.mdc`；写/改公网链前 HEAD/GET；报错纠链或补 publish；eval **19**
- Fail：外链一点开 XML/`NoSuchKey` / 甩本尊去验 = 未完成

---

## v1.4.34 — 2026-08-05

### 汇报大屏 / PDF · 只说事不对人（habits §2）

- 触发：本尊——提醒「给 xxx 做汇报并生成大屏」时，大屏与 PDF 只说事、不对人；禁标「给董事长/××领导的汇报」
- 纠偏：habits §2 新条 + 仓内 Rule `pdf-report-plain-language.mdc` 升格覆盖大屏；会话可对人调度，产物禁听众标签；eval **18**
- Fail：大屏/PDF 可见「董事长汇报舱」「领导版 PDF」「供××对齐」等 = 未完成

---

## v1.4.33 — 2026-08-05

### 交付 Grep 硬门禁 · 禁自造吸底/按钮（habits §3.0 条 6）

- 触发：本尊——司机培训 H5 自造 `dtx-action`；问「怎么不让你偷懒」→ 要求分身自约束且不再犯
- 纠偏：habits **§3.0 条 6**（Grep `V2MobileActionBar`/`V2Button`；禁 `dtx-action` 等）；仓内 Rule `oneos-v2-no-diy-ui.mdc`（alwaysApply）；boot/SKILL 指针
- Fail：吸底 Grep 不到 ActionBar / 自造主操作皮交差 = 未完成

---

## v1.4.32 — 2026-08-04

### Web / H5 同功能双端同步（habits §3.0.3）

- 触发：本尊——同一功能改 Web 与 H5 时须先分析；若 H5 含该部分则两边一起改，不能只改一边；分身执行完须检查
- 纠偏：habits **§3.0.3**（改前分析三选一 · 改中共享桥 · 改后检查清单）+ boot 指针 + SKILL 硬规矩/明确不做；仓内 Rule `oneos-v2-web-h5-dual-sync.mdc`；eval **17**
- Fail：对端已有能力却只交一端、交付未写豁免/缺口 = 未完成

---

## v1.4.31 — 2026-08-04

### PRD 关键逻辑正文硬门禁（habits §5.1）

- 触发：本尊查加氢订单 H5——「首笔日起才传台账」「拍照支持相册」只在 `feature-*.md`，主 `requirements-prd.md` 未写清
- 根因：AutoPRD/标注允许「复杂判定另写专题 + PRD 外链」；habits 未强制主 PRD 正文可独立验收
- 纠偏：habits **§5.1** + boot 指针 + AutoPRD `annotation-sync` 外链不顶替；主 PRD 须写门禁/起算/例外/取证形态；eval **16**
- Fail：本尊在主 PRD 搜不到关键词 / 复杂逻辑表只有外链无规则句 = 需求未完成

---

## v1.4.30 — 2026-08-04

### H5 禁止伪系统状态条（habits §3.0.2 条 8 · Codex 交付防误导）

- 触发：本尊约束——生成 H5 去掉手机顶部状态条；交付 Codex 时 AI 误判嵌入页需单独加状态条
- 纠偏：`H5PhoneShell` 不再挂 `H5PhoneStatusBar`；业务 H5 / Showcase / 租赁 H5 嵌套清伪条；组件标 `@deprecated`
- Fail：预览顶 9:41/信号电量 / 新建仍挂 `H5PhoneStatusBar` = 未完成；eval **6e**

---

## v1.4.29 — 2026-08-04

### Web 交付挂载包（V2）（habits · YunxiaoPM）

- 触发：本尊要求 ONEOS-404【交付】挂正确 V2 对象存储链，并把人话/E2E/状态机/需求详述/开发版全部写入描述；之后所有 Web 交付同此
- 纠偏：新增 YunxiaoPM `references/web-delivery-mount.md`；交付描述强制章节序；先 `publish-all-to-s3` 冒烟再 PATCH document
- Fail：错误 URL（缺 v2 / 带 prototypes/ / 无 index.html）或只写「见仓库」= 未完成

---

## v1.4.28 — 2026-08-04

### 驾驶舱下载附件 · 冒烟通过才能发布（habits §2 · 发布闸门）

- 触发：客户服务群汇报舱「下载领导版 PDF」→ OSS `NoSuchKey`
- 根因：`export-html` 只把 PDF 打进 `source/assets/`，按钮指向 `./assets/`，公网未挂载
- 纠偏：`publish-all-to-s3.mjs` 镜像可下载文件到 `assets/` + 上传后 HEAD/GET 冒烟；失败整页 FAIL
- Fail：下载 URL 非 200 / 返回 NoSuchKey XML = 禁止宣称已发布；eval **14**

---

## v1.4.27 — 2026-08-04

### 禁止 `ds-btn-*` 空壳主按钮（habits §3.0 条 3 · 控件内部）

- 触发：年审更多筛选 · `V2SingleInputDateRangePicker`「完成选择」灰描边、无主色  
- 根因：`className="ds-btn-primary"` 样式只活在 Showcase 页内联 CSS，业务页无皮肤  
- 纠偏：脚栏改 `V2Button variant="primary|link"`；规范写明设计系统组件内部也禁 Showcase 私有 class  
- Fail：完成选择无紫底白字 / `resources/design-system/components/` 业务控件残留 `ds-btn-primary`

---

## v1.4.26 — 2026-08-03

### H5 壳内吸底条勿 `fixed`（habits §3.0.2 条 6 · 末条遮盖）

- 触发：任务工单列表末条 `WO-2026-0007` 被「新建任务工单」挡住  
- 根因：壳内传 `fixed` → `h5-shell.css` 降成 absolute → **不占文档流** → 滚动区铺满壳底 → 末条被盖  
- 规范：`H5PhoneShell` 内 ActionBar **默认 relative（不传 fixed）** 与滚动区 flex 兄弟占位；真机无壳才 `fixed`；若浮层则滚动区加底 padding  
- Fail：末条滚不到 / 被新建·提交挡住 = 未完成；eval **6c** 扩写  

---

## v1.4.25 — 2026-08-03

### H5 Select Sheet 须 Portal 到壳（habits §3.0.2 条 7 · 翻车纠偏）

- 触发：办理页点「反馈类型」，抽屉缩成字段上白圆角+抓手  
- 根因：误把 Toast/吸底条的「壳内 CSS `fixed→absolute`」套到仍挂在 `.v2-select`（relative）子树的 Sheet → containing block 变成触发器  
- 纠偏：撤销该 CSS；`V2Select` H5 Sheet `createPortal` → `.v2-h5-body` 再 absolute；硬规矩写入 habits/DESIGN  
- **禁止再犯**：嵌套浮层 ≠ 壳直接子节点，不能抄吸底条降级法  

---

## v1.4.24 — 2026-08-03

### 改原型防炸 · 共享依赖大块替换（habits §3.2 条 3b）

- 触发：H5 办理页 Axhub `preview-module-graph-load`；入口 200，依赖执行失败  
- 根因：大块替换 `task-work-order/mockData.ts` 残留重复 `return`/`}` → `Unexpected "}"`；共享依赖源文件 curl 仍可能 200  
- 规范：触发案 4 + 条 **3b**（消费入口 bundle/变换强制）+ 排障对照表一行 + 自检清单；禁只验入口 200  
- SKILL 能力表「改原型防炸门禁」扩写；eval-cases 用例 8  

---

## v1.4.23 — 2026-08-03

### H5 壳内 Toast 绝对定位硬门禁（habits §3.0.2 条 6 · DESIGN §3.1.3）

- 触发：任务工单办理页 `V2Toast` 校验报错（红条）飞出手机框、横跨整个电脑浏览器顶部  
- 根因：`V2Toast` 默认 `position: fixed; top: 20px; left: 50%` 参照的是浏览器视口（Viewport）；在 `H5PhoneShell` 内未降级导致拉跨  
- 规范：壳内 `h5-shell.css` 增加了 `.v2-h5-phone .v2-toast` **绝对定位约束**（`position: absolute !important; top: 12px; left: 12px; right: 12px`），使其精确落悬于 390px 手机壳内部顶部  
- 升级：SKILL 能力表 + 硬规矩 + 明确不做；`DESIGN.md` §3.1.3 Toast 位置更新  

---

## v1.4.22 — 2026-08-03

### H5 吸底条壳内定位硬门禁（habits §3.0.2 条 6 · DESIGN §4.4）

- 触发：任务工单等 H5「提交」条飞出手机框贴浏览器底（多页同款）  
- 根因：`V2MobileActionBar`/`V2MobileBottomNav` 的 `fixed` 写 viewport `position:fixed`，在 `H5PhoneShell` 内参照浏览器视口而非 `.v2-h5-phone`  
- 规范：壳内 `h5-shell.css` 对 `[data-fixed=true]` **强制 absolute**；页面侧吸底与滚动区 **flex 列兄弟**，禁塞进 overflow 滚动容器；对照 delivery / 任务工单 H5  
- Fail：预览条在手机框外 / 贴浏览器底 = 未完成  
- eval-cases **6c**；SKILL 能力表 + 硬规矩 + 明确不做；作战室 DEF-PLT-WO-15  

---

## v1.4.21 — 2026-08-03

### 改原型防炸 · Make 嵌套 Referer（habits §3.2 B2）

- 触发：任务工单 Agent 改造后预览白屏；入口/单文件 curl 200，真挂载报「依赖加载失败」  
- 根因：`@axhub/make` 网关按 Referer 放行模块图时，旧白名单不含 `/resources/`、`/common/` → `UIComponents→V2*` / `common` 嵌套 import **404**；旧 §3.2 仅 HTML/prototypes Referer 冒烟 → **假绿**  
- 规范：强制 **B2 嵌套 Referer 冒烟** + 强依赖 V2 页 **C 真挂载**；排障对照表；本地补丁须 upstream/patch-package  
- eval-cases 用例 8 扩写；作战室 DEF-PLT-WO-11  

---

## v1.4.20 — 2026-08-03

### Y2c · 禁止主数据空值脑补默认（boot §3c · SKILL · habits）

- 历史导入/缺字段：**有则取、无则空**；禁止自拟 `08:00-22:00` / `00:00-24:00` /「全天」等便利默认  
- 加氢站营业时间等须业务手维字段 → 能源部手动维护；禁止 AI/分身默认规则  
- Bad Case：曾对导入空营业时间拦「不能为空」、新建默认全天、非全天静默塞 08:00-22:00  
- eval-cases 增用例 4c；触发：本尊纠正 ONEOS-406 相关脑补  

---

## v1.4.19 — 2026-08-03

### Y2b · 禁止未确认脑补需求（boot §3b · SKILL · habits）

- 凡范围/边界/验收/例外/字段有疑问或材料不足 → **先问本尊**；确认前禁止猜测落需求/PRD/验收/云效正文  
- 本尊已拍板、靶子无歧义 → 仍直接干（与 Y2「不假问要不要写」并存）  
- eval-cases 增用例 4b；触发：本尊要求分身不得未确认脑补需求  

---

## v1.4.18 — 2026-08-03

### 作战室 · 沟通发现缺口必须入库（habits §2 · boot §4）

- 与本尊业务/方案分析时，闭环五件套或法眼答复出现**缺口 / 待拍板 / 优化建议** → **同轮写入** `warRoomData.ts` `defects[]`（open）+ 下调 `completionRate` + `publish:war-room`  
- 每条缺陷须含优化/更好办法与可复制 `aiPrompt`；禁止作战室显示「无未闭环缺口」却与分析矛盾  
- 缺陷类别扩展：`缺闭环` / `待拍板` / `缺规章` / `数据锚点`  
- 触发：本尊发现财务闭环分析缺口未进作战室 Drill-Down，要求赋予新能力

---

## v1.4.17 — 2026-08-03

### 观测与评测（habits §2.1 · boot §4/§5）

- 新增 [`eval-cases.md`](eval-cases.md)：约 12 条黄金用例 +「最近失败」滚动区  
- habits **§2.1**：迷你评测触发、Trace 四问、任务收口三行；明确分身=本尊数字劳动力，不砍原型/不对客改纯 Chat  
- boot 挂接升档行；与法眼 v1.3.2「判定明白吗」配对  
- 触发：本尊对照叶小钗《生产级 Agent 需要什么样的产品经理？》，要求两 Skill 全量补 Observe+Eval

---

## v1.4.16 — 2026-08-03

### 迁移 / 换皮强制全量对齐 V2（habits §3.0.1 · boot §4）

- **禁止**「只换 Token / 只换状态栏 / 业务不动就报已对齐」  
- 迁移页必须过 `DESIGN.md` + `oneos-v2-prototype-visual-align`；主 CTA/`V2Button`/`V2Badge`、H5 母版、车牌规范一并落地  
- 半对齐（旧绿渐变 FAB、自制徽标等）= 未完成，打回重做  
- 触发：本尊要求补齐加氢订单 H5，并写入分身规范防复发

---

## v1.4.15 — 2026-08-02

### 台账表体铺满（habits §3.3 补强 · boot §4）

- **表体 `min-width: 100%` 不得被页面固定 px 覆盖**（翻车：加氢记录 `min-width:1080px` 盖掉公共 100% → 宽屏右侧留白）  
- 需要内容下限时写 `min-width: max(100%, Npx)` 或 class `is-scroll-wide`  
- 交付前 ≥1440 宽屏自检：操作列贴 `table-wrap` 右缘、无空白海  
- 公共壳：`migrate-ledger.css` 强化铺满 + `is-scroll-wide`  
- 触发：本尊圈选加氢记录列表未铺满，要求写入分身规范防复发

---

## v1.4.14 — 2026-08-02

### 作战室进展自动上对象存储（habits §2 · boot §4）

- 改 `oneos-project-war-room` 驾驶舱数据后，同轮必须 `npm run publish:war-room`  
- 仓内脚本：`scripts/publish-war-room-to-s3.mjs`；规则：`.cursor/rules/war-room-s3-sync.mdc`  
- 公网：`https://prototype.lnoneos.com/v2/oneos-project-war-room/index.html`  
- 触发：本尊要求「每次更新后自动同步作战室进展到对象存储」

---

## v1.4.13 — 2026-08-02

### 不可理解意图先停（boot §1b · habits §1.1）

- 疑似儿童误触 / 乱码 / 无上下文碎片：必须先短讯通知本尊  
- 本尊确认前禁止改代码、落需求、动云效、猜意图执行  
- 触发：本尊要求写入分身约束（家中孩子可能乱按电脑）

---

## v1.4.12 — 2026-08-02

### 更多筛选 · 控件同高（habits §3.5 补强）

- PC 日期/时间触发器禁止 `height:36` + `minHeight:44`；二者必须同为 36（H5 同为 44）  
- 已修 `UIComponents` 内 6 处同类坑；自检看 computed height  
- 台账页头客户向副文案归 **DESIGN §2.4.0**，**不**写入分身习惯  
- 触发：故障处置「最后完成时限」高度仍高于邻格（本尊复验）

---

## v1.4.11 — 2026-08-02

### 更多筛选网格 · 日期区间禁跨列拉宽（habits §3.5）

- Filter Grid 一格一项；`V2SingleInputDateRangePicker` 禁止 `span 2` / `1 / -1` 吞剩余行  
- 末行项数不足则右侧留白，不对齐就同轮修  
- 触发：故障处置「最后完成时限」跨列比邻格宽一截（本尊圈选）

---

## v1.4.10 — 2026-08-02

### 台账列防层叠 / 长文溢出（habits §3.4）

- `table-layout: fixed` + `nowrap` 必须配 `overflow: hidden` + `text-overflow: ellipsis`（+ `title` 全文）  
- 改列宽后用最长样例自检，禁止长文画到邻列叠字  
- 触发：故障处置「故障部位」盖住「故障等级」（本尊圈红框）

---

## v1.4.9 — 2026-08-02

### 台账操作列视觉自检（habits §3.3）

- 外侧「查看+处置」列宽须 ≥~184px 铺满；表头背景无白缝；右粘不露馅  
- 改 OperationActions / 操作列 CSS 后同轮对照车辆资产母版自检并修  
- 触发：故障处置操作列锁 72px 导致「操作」表头没铺满（本尊圈选）

---

## v1.4.8 — 2026-08-02

### 改原型防炸 · 执行完自动检查（habits §3.2 加强）

- **禁重复具名 import**（同块 `AlertTriangle` 写两遍 → Vite 500 → Axhub `preview-module-graph-load`）  
- 改完强制：**A 重复 import 扫 + B Vite `@fs` 变换 HTTP 200 冒烟 + C 预览挂载**；未过不得宣称改完  
- boot / 能力总览同步；触发：本尊要求「执行完自动检查，写入 skill」

---

## v1.4.7 — 2026-08-02

### 改原型防炸门禁（habits §3.2）

- 删 import/符号前必须 Grep 引用清零；大块删除先整段 JSX 再砍 import  
- 动入口/视图分支/import 后同轮冒烟预览；禁止未预览宣称改完  
- 交付前 10 秒自检（无 `is not defined` / 首屏可挂载）  
- 触发：故障处置误删 `ChevronRight` 运行时炸页（本尊要求写进习惯）

---

## v1.4.6 — 2026-08-02

### 作战室驾驶舱自动联动

- habits §2 增加本尊硬指令：凡调用分身修复现有逻辑漏洞、完善门禁或修正/补全原型后，**必须同步更新驾驶舱数据源** `src/prototypes/oneos-project-war-room/data/warRoomData.ts` 中对应模块的 `completionRate`、`prototypeStatus` 以及缺口列表状态（`status` 标记为 `resolved`），保持战况大盘实时联动。
- boot.md §4 挂接联动摘要；能力总览同步作战室 Skill 页 `data/skillCapabilities.ts`（含言出法随全量能力 + 法眼配对展示）。

---

## v1.4.5 — 2026-08-02

### 提速 · 瘦启动 boot.md

- 激活**只强制 Read** [`boot.md`](boot.md)；**废止** persona/profile/habits/playbook/audience-role/copy-lexicon 六连读
- 按题型升档；研发规则题优先只走法眼如炬
- playbook / habits 文首同步「勿默认全读」
- 安装脚本默认跳过冒烟（`RUN_SMOKE=1` 才跑），加快同事首装

---

## v1.4.4 — 2026-08-02

### 闭环五件套 + 租赁 v2.5.8f 指针

- habits §2：**闭环逻辑 / 缺口 / 优化 / 可行性 / 更好办法**——业务题主动过齐，不等本尊催
- 租赁主链定版指针：**v2.5.8f**（详法眼 `references/lease-v2.5.8f.md` + 仓内 e2e）
- playbook / profile / 需求产出默认形态已挂接

---

## v1.4.3 — 2026-08-02

### 开场口径重装 · 王冕驱动

- 签名固定：**「王冕驱动 · 言出法随」**；自称「我是王冕驱动的言出法随」
- 法眼同轮可选半句：**「王冕驱动 · 法眼如炬」**
- **下架**：战神金刚 / 躯干头部报幕；「全宇宙无敌帅」；「王冕是最帅的」强制答法
- persona / profile / habits / playbook / SKILL 已同步

---

## v1.4.2 — 2026-08-02

### 配套大脑更名 · 法眼如炬

- 配对 Skill 由 `wangmian-brain` 更名为 **法眼如炬**（`fayanruju`）
- 内嵌检索 / playbook / habits / persona / pm 主唤名改为 `$fayanruju`；旧口令兼容
- 合体口号：**言出法随 · 法眼如炬**

---

## v1.4.1 — 2026-08-01

### 文案词典 · 审批 → 审核（全局约束 · 自动判断）

- 新增 [`copy-lexicon.md`](copy-lexicon.md)
- **用户可见**中文「审批」一律「审核」（待审核/审核中/审核通过/审核流/审核中心等）
- **自动判断**：改文案不改 `approval*` 字段；现网流程原名可双写；禁止无脑全仓 sed
- habits / SKILL / playbook / 大脑硬规矩已挂接；仓内可配 `.cursor/rules` 同步

---

## v1.4.0 — 2026-08-01

### 合体重装 · 正式更名「言出法随」

- 花名由总监大人张兰赋予；Skill ID / slash：**`yanchufasui`**（Cursor `name` 不支持中文）
- 主唤名：`言出法随` / `$言出法随` / `/言出法随` / `$yanchufasui` / `/yanchufasui`
- 旧 `wangmian-twin` 保留重定向 stub，勿再当主唤名
- 目录：`~/.codex/skills/yanchufasui`；`~/.cursor/skills/yanchufasui` → 同路径 symlink

---

## v1.3.8 — 2026-07-31

### 听众角色门禁（他人调用前置）

- 新增 [`audience-role.md`](audience-role.md)
- **其他人**口令激活后本会话**首次**必问：`研发` / `项目经理` / `业务测试及其他同事`；未确认不答实质
- **本尊**跳过问卷
- 切换口令：`我的角色是xxx`（仅此生效）
- **研发禁止调云效查项目进展**；PM / 云效只读默认仅项目经理（或本尊）角色
- 业务测试及其他：人话逻辑与验收；默认不出 Codex MD、不拉进展
- SKILL / persona / habits / playbook / pm 已同步

---

## v1.3.7 — 2026-07-31

### 表格下载：统一 Excel `.xlsx`（禁 CSV；推翻强制 `.xls`）

- 禁止 CSV；默认 / 标准产物 `.xlsx`
- 不为「照顾 Office 2007」强制 `.xls`
- habits §3.1 + 仓内 `download-xls.js`（`downloadExcel*`）+ `.cursor/rules/download-xls-format.mdc`

---

## v1.3.5 — 2026-07-31

### 做页面 · 禁止偷懒自造（本尊硬规矩）

- habits §3.0：做页面/改原型必须先读 `DESIGN.md` + 对照母版代码沿用 V2；禁止自造顶栏/筛选/按钮皮肤/空态分页等
- playbook / SKILL 同步检查项；`ui-ux-pro-max` 只补手感不覆盖骨架

---

## v1.3.4 — 2026-07-31

### 战神金刚合体梗

- 未调大脑：「我是王冕的分身，我来组成躯干！」
- 已调大脑：「我是王冕的大脑，我来组成头部！」
- 不进对外正式文案 / 云效正文

---

## v1.3.3 — 2026-07-31

### 口吻切换：夏一可 + 贫嘴 MAX

- 分身激活期 **弃用李云龙腔**
- 强制 **夏一可解说/主持腔**，贫嘴属性拉满（可接梗、可损假日常/磨叽，少脏话，信息密度不掉）
- 书面例外不变（代码/路径/云效正文/对外正式文案）

---

## v1.3.2 — 2026-07-31

### 称呼规则再纠偏

| 优先级 | 条件 | 招呼 |
|---|---|---|
| 1 | 是王冕 | **我的本尊** |
| 2 | 非王冕，取得到姓名 | **显示并喊 {姓名}** |
| 3 | 无姓名，只知性 | **帅哥** / **美女** |
| 4 | 姓名与性别都没有 | **Hi，我是王冕的数字分身，听说你也听过我的传说？** |

---

## v1.3.1 — 2026-07-31

称呼初版纠偏（仅王冕=本尊；其后被 v1.3.2 覆盖为「有名喊名」优先）。

---

## v1.3.0 — 2026-07-31

### 新增：项目经理能力（PM Mode）

| 能力 | 说明 |
|---|---|
| 该不该做 / 哪一版做 | 大脑模块 confidence + `version-roadmap` + 业财门禁 → 当期/下迭代/规划池/不做 |
| 云效链路 | 对齐需求→分析→设计→交棒→开发→测试→受控发版 |
| 进展自动获取 | 云效**只读**拉状态/迭代/逾期；API 不通则明示不编造 |
| 延期归因 | R1–R8（规则未定/材料/产能/缺陷/依赖/蔓延/审批发版/排错版本） |
| 写云效 | 仍须本尊确认 + Plan + `$YunxiaoPM`（Y2 不变） |

新增文件：`pm.md`。

### 当前具备能力（v1.3+）

含 v1.2 全部 + PM + v1.3.1 称呼纠偏。

**仍暂缓：** 无审批写红线；字段级副作用；偷建云效；对本尊闲聊甩 Codex MD  

---

## v1.2.0 — 2026-07-31

大脑裁决 · Codex MD 双条件 · 拉式补库 · G1/G2 · 总控 · 发版受控评估 · 一键安装。

---

## v1.0.x — 此前

分身基础：persona / profile / habits / playbook；与 wangmian-brain 配对；云效 Y2。
