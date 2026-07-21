# 统一运营管理平台 · 云效标签清单（选择器用）

来源：`GET /projex/api/workspace/space/tag/search?spaceType=Space&spaceIdentifier=1280be963a5a2cc126a4118dca&q=`  
抓取时间：2026-07-21  
机器可读：同目录 `oneos-pc-runtime-ids.json` → `tags`

## 使用约定

- **记录需求**时标签由用户用选择器点选（`AskQuestion` / Plan ○），**不要**再按 `lines.ts` 业务条线说明自动推断。
- Agent 用点选到的 `name` 查 `tags.by_name` → `identifier`，再 `PATCH` 打标。
- 完整建单提示词（含 A/B/C 与 30 标签枚举）：[references/oneos-pc-record-requirement-prompt.md](../references/oneos-pc-record-requirement-prompt.md)

## 全量标签（30）

| # | 标签名 | identifier |
|---|---|---|
| 1 | 运维管理条线 | `a611b2f2b7c3fd3623ba2d5f52` |
| 2 | 报表中心 | `8428d15f45a5b34173202db758` |
| 3 | 能源管理 | `3396ebb527358fe6f89fe42849` |
| 4 | 维修站管理 | `e7b4da7984801e75630645f437` |
| 5 | 充电站管理 | `6ea830485f28a0d8a6e14851a8` |
| 6 | 还车应结款 | `4204960ce658c94b17abb7c5f6` |
| 7 | 交车应收款 | `6e7a9127d0f70281ca65d335d9` |
| 8 | 加氢站管理 | `6cdacae673f9e1fba96296f2ad` |
| 9 | 保险管理 | `578ed5ba12bfcf274721e956f2` |
| 10 | 合同管理 | `23873be81931cb0dc1bf87a456` |
| 11 | 租赁账单 | `3e9433f571b20e80b02626d2de` |
| 12 | 供应商管理 | `7b86b7c1f3b3da21b814c5a39d` |
| 13 | 客户管理 | `dbf959a70bc979106dc78afa90` |
| 14 | 还车任务 | `763de323cefee45e5270e4661e` |
| 15 | 安全培训 | `76988b5f73ef515de5930d59b9` |
| 16 | 备件管理 | `5d09c864767d898a4f8c0ca804` |
| 17 | 停车场管理 | `7c522e2fb29213d7d390e78b97` |
| 18 | 备车管理 | `22c6a3ed0e4bf95fd99bf95695` |
| 19 | 异动管理 | `84b4333ec7c76d0fa2adcc47bf` |
| 20 | 调拨管理 | `fa88c16c152c6fb5978e3b4339` |
| 21 | 上牌管理 | `990af2fb716dd85568bc7019bf` |
| 22 | 替换车管理 | `8d1decf30259b941016cadc9d2` |
| 23 | 还车管理 | `1e0fce2d6929ff4ac13b310e97` |
| 24 | 交车管理 | `b6947b5aca82a8c759612ba039` |
| 25 | 车辆管理 | `cb71b6db9373d6d8c7aae452a5` |
| 26 | 审批中心 | `338add796f2221bbc36dd77d35` |
| 27 | 故障管理 | `ceb526a7343995577645317e9a` |
| 28 | 车辆年审 | `5193165dad1e91a161502b54c2` |
| 29 | 维修管理 | `f5202633870ff409e0ebc16d5f` |
| 30 | 工作台 | `b62d21beac55c0b43389915eab` |

## 选择器文案（C 段）

已并入 [oneos-pc-record-requirement-prompt.md](../references/oneos-pc-record-requirement-prompt.md)「用户口令」；此处仅作 identifier 对照表。
