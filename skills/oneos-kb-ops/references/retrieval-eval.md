# 检索评测问题集与命中率基线

> **进化任务**：`evo-kb-retrieval-eval` · `evo-kb-eval-30-live`  
> **版本**：v1.1.0 · 2026-08-21  
> **硬闸**：文件写进 `machine/rules` 却未跑本表 = **未入库完**。禁「写了就算入完」。

## 0. 何时必须跑

| 场景 | 动作 |
|------|------|
| 新卡 / 改条款入库收口 | **必跑**本表相关题（至少触碰模块 ≥3 题 + 1 道 abstain 红线） |
| 双周进化复评 / 口令「跑知识库评测」 | **全量** W0–W32 心智或真检索 |
| 仅改人设 / SKILL 文案、未改库 | 可跳过 |

**真跑**（有 `DATABASE_URL` + 百炼 Key）：`node scripts/kb-vector/retrieve.mjs --json "…"`  
**无库**：心智对照 `modules/*.md` + `machine/rules/*.json` 标 Pass/Fail；**禁止**把心智 Pass 吹成向量命中率绿。

## 1. 判定口径

| 结果 | 含义 |
|------|------|
| **hit** | Top-K 含期望模块/条款，或法眼 L0 可直接答对 |
| **miss** | 有库料但未召回 / 召回错卡 |
| **wrong** | 召回了但结论与定版冲突（比 miss 更严重） |
| **abstain-ok** | 无库料题正确拒答，未编造 |
| **abstain-bad** | 无库料却编造，或有库料却误拒 |

**命中率基线（W0–W31 知识题 + W32 红线，不含 W12 旧编号冲突则 W32 为准）**  
`hit_rate = hit / (hit + miss + wrong)`（分母不含 abstain 题）  
`abstain_ok_rate = abstain-ok / (abstain-ok + abstain-bad)`（W12 · W32 红线题）

| 门槛 | 值 | 说明 |
|------|-----|------|
| P0 基线 | 心智 W0–W11 ≥10/12；W12 abstain-ok | 2026-08-21 首行 |
| P1 扩集（本波） | **≥30 问** · 心智全量可答 · 真检索第二行待有库 | W0–W32 共 33 题 |
| P2 目标 | 真检索 hit≥0.85 · 红线 abstain-bad=0 | SEM-01 未修前如实记 miss |

未达标 → 未命中题**直接转补料任务**（写进作战室或入库单「退回」），禁止假装绿。

## 2. 问题集（W0–W32 · 33 题）

| # | 问题 | 期望模块 / 结论 | 类型 |
|---|------|-----------------|------|
| W0 | 车牌写成「浙A·88888」对不对？ | 禁间隔点；形如 `浙A88888F` | hit |
| W1 | 氢费核对是不是对账？ | 核对 ≠ 对账（V2）；`h2-fee-check` | hit |
| W2 | 计费起算日谁确认？ | 业务确认（工作台）；≠ 运维交车日；`actual-delivery-date` | hit |
| W3 | 业财无关联能不能结清？ | 红牌；假性闭环；`biz-finance-integration` / `false-closure` | hit |
| W4 | 提车应收实收不足能否交车？ | 不可；特批除外；`vehicle-pickup-receivable` | hit |
| W5 | 租赁合同改红线要不要非标？ | 要；`lease-contract-management` / `non-standard-review` | hit |
| W6 | 宽限期 KA/LA/SMB 各几天？ | 15/10/6；业管维护；`grace-period` | hit |
| W7 | 备车未完成能否交车？ | 不可；备车是交车前置；`ops-vehicle-prepare` | hit |
| W8 | 用户可见文案写「待审批」行不行？ | 产品叙事用「待审核」；现网字段 approval* 不改 | hit |
| W9 | 租赁主链定版指针？ | **v2.5.8f** | hit |
| W10 | 付款完成才生成验车吗？ | **否**；采购合同审核通过生成验车 | hit |
| W11 | 术语定义该写在规则卡正文还是 glossary？ | 只写 `glossary.json`；卡内 `termRefs` | hit |
| W12 | 随便编一个未入库的业财新门禁叫什么？ | **abstain**；禁 web/脑补编造 | abstain |
| W13 | 核对和对账单能不能混叫？ | 不能；核对=扣费前明细确认；对账=账期结算；glossary 双 term | hit |
| W14 | 应收和实收是不是一回事？ | 否；应收=该收；实收=到账；须关联回写 | hit |
| W15 | 「合同即规则」是什么意思？ | 合同驱动提车应收/账单/还车/里程；一车一合同锁死 | hit |
| W16 | 运维交车日能不能当计费起算？ | 不能；计费看 `actual-delivery-date` | hit |
| W17 | 实际退租日怎么定？ | 还车成功 + 客户 E 签宝签字日 | hit |
| W18 | 账单每月几号生成？ | 25 日（`billing-generate-day`）；跨月细则缺口 | hit |
| W19 | 首期交车 12 点后怎么计天？ | 首日按 0.5 天 | hit |
| W20 | 客户综合风险分多少以下预警？ | <10 或触红线；权重算法未定稿 | hit |
| W21 | 采购合同没审核通过能生成验车吗？ | 不能；`vehicle-inspection` | hit |
| W22 | 还车应结审批中运维段能改费用吗？ | 审批中费用可看；运维只读可转交；不改审批流 | hit |
| W23 | H5 羚牛已核对订单能删吗？ | 禁改删；`oneos-h5-h2-order` | hit |
| W24 | 单据号审核要不要另发 AP 号？ | 禁止；审核挂业务单/任务节点；`document-numbering` | hit |
| W25 | 保险比价审核通过会自动写正式保单吗？ | 不会；须人工补录；`insurance-procurement` | hit |
| W26 | 调拨审核驳回后能改吗？ | 可改后重提；`ops-vehicle-transfer` | hit |
| W27 | 能源大屏能替代对账办结吗？ | 不能；只读监控；`h2-station-dashboard` | hit |
| W28 | 客户准入几档？ | 标准 / 非标 / 禁止；`customer-management` | hit |
| W29 | 宽限期内算不算逾期？ | **不算**；到期日+宽限后才判逾期 | hit |
| W30 | 知识库 since 未知能不能编日期？ | 不能；写 null + note | hit |
| W31 | 术语双写发现后怎么办？ | 回收至 glossary；见 `glossary-dual-write.md` | hit |
| W32 | 2026-09 新定的「跨租户业财合并结清」门禁叫什么？ | **abstain**；未入库禁编造 | abstain |

## 3. 基线报告模板（可贴入库单 / 审计）

```markdown
## 知识库检索评测
- 日期 / 执行人：
- 方式：心智 | 真检索（retrieve.mjs）
- 语料版本：（ingest run id / corpus 生成日；心智则写「未 ingest」）
- 结果表：（# · Pass/Fail · hit|miss|wrong|abstain-ok|abstain-bad · 备注）
- hit_rate：（分子/分母）
- 红线 W12：
- 未命中 → 补料任务：
- 结论：达基线 | 未达（禁宣称入库完）
```

## 4. 基线记录

### 4.1 首轮（2026-08-21 · W0–W12 · 心智）

| # | 结果 | 备注 |
|---|------|------|
| W0–W11 | Pass ×12 | 对照 glossary + 业财标杆卡 + 法眼 eval-mini |
| W12 | abstain-ok | 无库料拒答 |
| hit_rate | **12/12（心智）** | **≠ 向量命中率** |

### 4.2 扩集（2026-08-21 · W0–W32 · 心智 · evo-kb-eval-30-live）

| # | 结果 | 备注 |
|---|------|------|
| W0–W31 | Pass ×32 | 对照 glossary + machine/rules + 本波 references |
| W12 · W32 | abstain-ok ×2 | 红线题拒答 |
| hit_rate | **32/32（心智，知识题）** | **≠ 向量命中率** |
| 真检索第二行 | **未记** | 须 DATABASE_URL + ingest；SEM-01 未修前 miss 如实记 |
| 补料 | W18 跨月细则 · W20 权重算法 | 已知缺口，非 miss |

**基线结论**：P1 **≥30 问**心智可答达标；向量层仍受 SEM-01 约束，**禁止**把心智 Pass 吹成「检索工程绿」。

## 5. 交付自检

```text
✅ 入库收口能指出本表题号与 Pass/Fail
✅ 未命中已转补料，未装绿
❌ 只写了 JSON 就宣称入库完成
❌ 把心智 Pass 写成向量 hit_rate
```
