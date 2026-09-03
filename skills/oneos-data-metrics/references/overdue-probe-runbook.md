# 逾期账单率 · 产线只读探针 Runbook

> **进化任务**：`evo-dm-overdue-probe`  
> **版本**：v1.0.0 · 2026-08-21  
> **关联口径卡**：`first-e2e-overdue-rate.md` · id `dm-lease-overdue-bill-rate` v0.1  
> **硬闸**：探针未通 / 表未核对 = **不出数**；禁止用 mock 或估算填「逾期率」。

## 0. 本机冒烟结论（诚实）

| 项 | 结果 |
|----|------|
| 脚本存在 | ✅ `~/oneos-prod/scripts/prod-ro-probe.sh` |
| 连通冒烟 | ❌ **未跑通** — `ping` → `ERROR 2013 Lost connection to MySQL server at 'reading initial communication packet'` |
| 日期 | 2026-08-21 |
| 含义 | Runbook 与命令清单已落盘；**真表核对阻塞于网络/VPN/库连通**，非口径纸面缺失 |

**禁止**因本文件存在而宣称「逾期率已对表现网」。

## 1. 前置

1. 合规官结论已引用（宽限期内不算逾期 · KA/LA/SMB 15/10/6）— 见 `first-e2e-overdue-rate.md` §1。  
2. VPN / 堡垒 / 本机 `~/oneos-prod` 密钥与 `external-facts/README.md` 协议就绪。  
3. 只读；**禁** INSERT/UPDATE/DELETE。

## 2. 探针命令清单（连通恢复后按序执行）

```bash
# ① 连通
~/oneos-prod/scripts/prod-ro-probe.sh ping

# ② 库列表（确认租赁/业财库名 — 以探针输出为准，禁止脑补）
~/oneos-prod/scripts/prod-ro-probe.sh dbs

# ③ 表名模糊匹配（示例 pattern，命中后改实际 db/table）
~/oneos-prod/scripts/prod-ro-probe.sh match bill
~/oneos-prod/scripts/prod-ro-probe.sh match receivable
~/oneos-prod/scripts/prod-ro-probe.sh match lease

# ④ 结构（替换 <db> <table>）
~/oneos-prod/scripts/prod-ro-probe.sh desc <db> <table>

# ⑤ 抽样 SQL（只读 · 须 LIMIT · 字段名以 desc 为准）
~/oneos-prod/scripts/prod-ro-probe.sh sql "
SELECT COUNT(*) AS cnt
FROM <db>.<lease_bill_table>
WHERE <status_col> = '<逾期枚举>'
LIMIT 1
"
```

## 3. 核对清单（探针通后打勾）

| # | 核对项 | 期望 | 结果 |
|---|--------|------|------|
| P1 | 账单「到期日」字段存在且语义 = 口径卡「账单到期日」 | 字段名写入 external-facts | ☐ 未跑 |
| P2 | 「逾期」状态枚举与合规官判定一致（含宽限） | 非仅 `due_date < today` | ☐ 未跑 |
| P3 | 客户分级 / 宽限天数来源表与客户管理一致 | KA/LA/SMB 可 JOIN | ☐ 未跑 |
| P4 | 排除项：作废/冲销/非租赁应收 | SQL 可表达 | ☐ 未跑 |
| P5 | 观察窗：到期日 ∈ [start,end] + 窗末日快照 | 与口径卡一致 | ☐ 未跑 |

## 4. 产出物

1. 报告路径：`~/oneos-prod/docs/external-facts/dm-lease-overdue-bill-rate-probe-YYYYMMDD.md`  
2. 更新口径卡 `dataSource`（status: mapped | unmapped + evidenceRef）  
3. 交典藏官入库单 — **度量官不写库**  
4. 仍未 mapped → 清册/对外维持 **取不到**

## 5. 交付自检

```text
✅ 连通失败已诚实记录，附命令清单
✅ 未编造逾期率样例数字
❌ ping 失败却写「探针已绿」
❌ 用 HOST_KPI / 原型 mock 填 dataSource
```
