# 安装 / 更新 项目汇报助手（oneos-briefing-aide）

## 正式单源（当前仓）

1. Skill 正文：`.cursor/skills/oneos-briefing-aide/`  
2. 配对：业务口径（规则对错）；决策层大屏走 `pdf-report-plain-language`；数字走度量官  
3. **新开对话**，口令 `/oneos-briefing-aide` / 「项目汇报助手」/ 「按张兰总口径写培训」/ 「按张兰总图解改方案」  
4. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包  

> 一线培训走轨 A；产品方案图解走轨 B。落到已有页改内容，不另起一张。**不裁业务规则、不改真码、不写云效。**  
> 指挥塔已挂卡（2026-09-03）；定妆未拍板，卡顶不挂假图。

## 同事一键

见 [`../INSTALL-ONEOS-SKILL-MAP.md`](../INSTALL-ONEOS-SKILL-MAP.md)。只装本分身：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
```

装完 **新开 Chat**，口令 `/oneos-briefing-aide`。

## 本尊机 · 软链（强制 · 禁 cp）

```bash
REPO="/Users/sylvawong/oneos_pc"

ln -sfn "$REPO/.cursor/skills/oneos-briefing-aide" ~/.agents/skills/oneos-briefing-aide
ln -sfn "$REPO/.cursor/skills/oneos-briefing-aide" ~/.cursor/skills/oneos-briefing-aide
ln -sfn "$REPO/.cursor/skills/oneos-briefing-aide" ~/.codex/skills/oneos-briefing-aide
```

- ✅ 仓内单源 + 软链  
- ❌ 禁止把目录 `cp` 成 `~/.agents/skills/` 实体副本  

装完 **新开 Chat**。

## 瘦启动冒烟

1. 新开 Chat → 喊「项目汇报助手」或「按张兰总口径写培训」→ 应读本 `SKILL.md`  
2. 签名含「王冕驱动 · 玉衡 · 项目汇报」  
3. 「给董事长做驾驶舱」→ 应改指决策层汇报规则，不套一线骨架、也不套图解方案  
4. 「按张兰总图解改产品方案」→ 走轨 B（`zhanglan-scheme.md`），不套培训 12 节  
5. 业务能不能做 → 转合规官  

## 与友邻

| Skill / 规则 | 关系 |
|--------------|------|
| oneos-biz-rules / fayanruju | 业务对错 |
| pdf-report-plain-language | 决策层大屏/PDF（不要混用骨架） |
| oneos-data-metrics | 汇报数字怎么算 |
| oneos-pm-product | 落需求/改原型；本 Skill 不替代产品交付 |
| oneos-wave-router | 不知喊谁时指路 |
