# 安装 / 更新 知识库意图分析师（oneos-kb-intent-analyst）

## 正式单源（当前仓）

1. Skill 正文：`.cursor/skills/oneos-kb-intent-analyst/`  
2. 配对：知识典藏 `oneos-kb-ops`（定版入库）；业务口径 `fayanruju` / `oneos-biz-rules`  
3. **新开对话**，口令 `/oneos-kb-intent-analyst` / 「意图分析」/ 「群聊语料」/ 「体微绘画」  
4. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包  

> **只做草案**：部位→类型→变体 MD/JSON；**不裁业务规则、不改 Bot 真码、不定版入库**。  
> 定版入库交典藏官。指挥塔已挂卡（2026-09-03）；立绘/性别未拍板，卡顶不挂假图。

## 同事一键

见 [`../INSTALL-ONEOS-SKILL-MAP.md`](../INSTALL-ONEOS-SKILL-MAP.md)。只装本分身：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
```

装完 **新开 Chat**，口令 `/oneos-kb-intent-analyst`。

## 本尊机 · 软链（强制 · 禁 cp）

```bash
REPO="/Users/sylvawong/oneos_pc"   # 若单源在其他仓，改此根

ln -sfn "$REPO/.cursor/skills/oneos-kb-intent-analyst" ~/.agents/skills/oneos-kb-intent-analyst
ln -sfn "$REPO/.cursor/skills/oneos-kb-intent-analyst" ~/.cursor/skills/oneos-kb-intent-analyst
ln -sfn "$REPO/.cursor/skills/oneos-kb-intent-analyst" ~/.codex/skills/oneos-kb-intent-analyst
```

- ✅ 仓内单源 + 软链  
- ❌ 禁止把目录 `cp` 成 `~/.agents/skills/` 实体副本  

装完 **新开 Chat**。

## 瘦启动冒烟

1. 新开 Chat → 喊「意图分析师」或 `/oneos-kb-intent-analyst` → 应读本 `SKILL.md`  
2. 签名含「王冕驱动 · 玉衡 · 知识库意图分析」  
3. 未给 Excel/语料就要定版入库 → 应拒绝并指向典藏官  
4. 口径/能不能做 → 转合规官  

## 与友邻

| Skill | 关系 |
|-------|------|
| oneos-kb-ops | 定版入库、manifest、向量 ingest |
| fayanruju / oneos-biz-rules | 口径裁决 |
| oneos-wave-router | 不知喊谁时指路 |
