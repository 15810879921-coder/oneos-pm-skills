# 安装 / 更新 鼎立乾坤（dingliqiankun）· 系统架构

## 正式单源（当前仓）

1. Skill 正文：`.cursor/skills/dingliqiankun/` + 用途门 `.cursor/skills/oneos-system-arch/`  
2. 配对：开发落地 `mingjingzhishui` / `oneos-dev-delivery`；业务口径 `fayanruju` / `oneos-biz-rules`  
3. **新开对话**，口令 `鼎立乾坤` / `$dingliqiankun` / `系统架构` / `/oneos-system-arch`  
4. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包  

> **默认不改业务码**：架构出 ADR/契约；落地改码须开发落地接棒。  
> 指挥塔已挂卡（2026-09-03）；定妆未拍板，卡顶不挂假图。

## 同事一键

见 [`../INSTALL-ONEOS-SKILL-MAP.md`](../INSTALL-ONEOS-SKILL-MAP.md)。同事只装用途名（运行时已并进该包）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
```

装完 **新开 Chat**，口令 `/oneos-system-arch` / `鼎立乾坤`。

## 本尊机 · 软链（强制 · 禁 cp）

```bash
REPO="/Users/sylvawong/oneos_pc"   # 若单源在其他仓，改此根

ln -sfn "$REPO/.cursor/skills/dingliqiankun" ~/.agents/skills/dingliqiankun
ln -sfn "$REPO/.cursor/skills/oneos-system-arch" ~/.agents/skills/oneos-system-arch

ln -sfn "$REPO/.cursor/skills/dingliqiankun" ~/.cursor/skills/dingliqiankun
ln -sfn "$REPO/.cursor/skills/oneos-system-arch" ~/.cursor/skills/oneos-system-arch
```

可选 Codex：

```bash
ln -sfn "$REPO/.cursor/skills/dingliqiankun" ~/.codex/skills/dingliqiankun
ln -sfn "$REPO/.cursor/skills/oneos-system-arch" ~/.codex/skills/oneos-system-arch
```

- ✅ 仓内单源 + 软链  
- ❌ 禁止把目录 `cp` 成 `~/.agents/skills/` 实体副本  

装完 **新开 Chat**。

## 瘦启动冒烟

1. 新开 Chat → 喊「鼎立乾坤」或「系统架构」→ 应只读 `boot.md`  
2. 签名含「王冕驱动 · 玉衡 · 系统架构（鼎立乾坤）」  
3. 未切问题就要求选型 → 应拒绝并先出切割卡  
4. 未授权改码请求 → 应拒做并指向开发落地  

## 与友邻

| Skill | 关系 |
|-------|------|
| yanchufasui / oneos-pm-product | 产品范围与交棒故事 |
| fayanruju / oneos-biz-rules | 能不能做 |
| mingjingzhishui / oneos-dev-delivery | 架构包落地改码（工程官） |
| oneos-wave-router | 不知喊谁时指路 |
