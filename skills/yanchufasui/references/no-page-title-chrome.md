# 禁页头模块标题 + 标题下描述（标准包 · L0）

> 本尊拍板 2026-08-16 · 言出法随 v1.5.1 · evo-yc-no-page-title-chrome  
> 事实源：`src/resources/design-system/DESIGN.md` **§2.4.0**（本卡只摘要，改口径先改 DESIGN）

## 硬门禁

业务台账 / 列表 / 看板 / 工作台主内容区：

| 禁止 | 允许 |
|---|---|
| 模块 `h1` / `.v2-ledger-chrome__heading` | 直接从 KPI / Pill / 筛选 / 主操作起笔 |
| 标题下灰字描述 / `pageSubtitle` / `__sub` | 有 CTA 时仅右侧操作行（`V2LedgerChrome` 只吃 `actions`） |
| 白底说明卡片、三词组副文案墙 | — |

## 豁免（勿误砍）

| 场景 | 口径 |
|---|---|
| 详情 / 表单 §4.8 | **保留**业务页名 + 返回 + CTA；**禁**页名下再挂描述 |
| 口令门 | 可留模块名（直链认页） |
| 对外汇报大屏叙事标题 | 属内容本身（`pdf-report-plain-language`） |
| Showcase | 教学页可留示范标题 |
| H5 `V2MobileHeader` 导航标题 | 无侧栏时保留壳内导航名 |

## 落地锚点

- 组件：`src/resources/design-system/components/V2LedgerChrome.tsx`（`title`/`subtitle` deprecated，不渲染）
- CSS：`oneos-ds-page-chrome.css`（heading/sub `display:none` 兜底）
- 迁移台账：`MigrateLedgerHub` 列表顶栏不渲染 `config.title` / `pageSubtitle`
- Rule：`oneos-v2-copy-no-overexplain` · `oneos-v2-prototype-visual-align` #1 / #7c
- habits：§3.0 条 7 / §3.0.4 · eval **20**

## 交付自检

```text
✅ 列表顶栏无模块 h1、无标题下描述
✅ 有主操作 → 仅右侧按钮行
✅ 详情有页名则其下无说明书墙
❌ 再写「必须带三词组副文案」= 旧口径，Fail
```
