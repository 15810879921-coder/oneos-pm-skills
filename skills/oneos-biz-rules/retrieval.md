# 法眼如炬 · 检索深读（按需）

> **默认勿读。** 主协议已内联 `SKILL.md`。仅冲突展开 / 业财长链路时打开。

## KB 根

1. `<工作区>/src/resources/oneos-knowledge-base/`（正式单源）
2. `<本 Skill>/kb/`（软链到仓内 KB）
3. `/Users/sylvawong/oneos-v2/src/resources/oneos-knowledge-base/`（本机兜底）

更新靠拉仓，禁止发文件夹。

## 定位（省 token）

1. Grep `machine/kb-alias-index.tsv`（优先）或 `kb-alias-index.json`
2. 命中模糊 → 升 L2/L3 读卡确认
3. **禁止**默认整读 `kb-manifest.json`（仅 alias 全无命中且需枚举时局部读）

## 冲突裁决

1. 中期闭环与最新 AutoPRD 优先；租赁主链 → **v2.5.8f**（本 Skill `references/lease-v2.5.8f.md` + 仓内 e2e）  
2. 业财资金闭环与门禁 → `foundations/biz-finance-integration`  
3. V1.2 操作细节 → Desktop `web端`（`00-source-corpus.md`）  
4. 氢费核对 ≠ 对账 → V2  
5. 未来/试验页 → 不作现网强验收  

## 业财类默认

1. `foundations/biz-finance-integration.md` + `machine/rules/biz-finance-integration.json`  
2. 相关模块卡  
3. 人读全文：`src/resources/业财一体化全链条方案-汇报稿.md`（仅汇报/完整对齐）

## 禁止

- 一次读完 `modules/`
- `__MACOSX` / zip 垃圾路径当语料
- 对终端用户朗读绝对路径与 confidence 字段名
