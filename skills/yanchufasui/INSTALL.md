# 安装 / 更新 言出法随（yanchufasui）

> **团队请优先用用途名**：**产品交付** `/oneos-pm-product`  
> 完整版图：[`../oneos-wave-router/SKILL-MAP.md`](../oneos-wave-router/SKILL-MAP.md) · [`../INSTALL-ONEOS-SKILL-MAP.md`](../INSTALL-ONEOS-SKILL-MAP.md)

## 同事一键（npx skills · 与 YunxiaoPM 同通道）

安装页：https://15810879921-coder.github.io/oneos-pm-skills/

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

更新：

```bash
npx skills update yanchufasui fayanruju mingjingzhishui -g -y
```

装完 **新开 Chat**。完整知识库仍在 **oneos-v2**；改原型请打开该工作区。  
用途名 Skill（`oneos-*`）目前以 **oneos-v2 仓内 + 本尊机软链** 为主；同步到同事安装页为后续波次。

**本尊机**继续用仓内软链，不要用 `-g` 覆盖 `~/.cursor/skills/yanchufasui`。

## 正式单源（oneos-v2）

1. 打开 / 拉取 **oneos-v2**（Skill 正文：`.cursor/skills/yanchufasui/`）
2. 配对法眼：同仓 `.cursor/skills/fayanruju/`（KB：`src/resources/oneos-knowledge-base/`）
3. **新开对话**，口令 `产品交付` / `oneos-pm-product` / `言出法随` / `$yanchufasui`（或 User Rule 全局常驻）
4. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包

发布到同事安装页：把本目录同步进 `oneos-pm-skills/skills/yanchufasui/` 后 push。

## 本尊机 · 菜单去重（强制）

Cursor / Codex 会同时索引「仓内 Skill」与 `~/.cursor/skills`、`~/.codex/skills`。

- ✅ 仓内单源：`oneos-v2/.cursor/skills/yanchufasui/`
- ✅ 本尊机 User Rule 路径：`~/.cursor/skills/yanchufasui` → **软链到仓内**（勿再维护第二份实体拷贝）
- ✅ 用途名：`~/.cursor/skills/oneos-pm-product` → 仓内（见 INSTALL-ONEOS-SKILL-MAP）
- ❌ 不要：`~/.codex/skills/yanchufasui` 实体目录（会与仓内双份）
- ❌ 不要：`yanchufasui.bak-*` 放在 skills 目录
- ❌ 旧入口 `wangmian-twin` stub **已下架**；口令请用 `产品交付` / `言出法随` / `yanchufasui`

清理后请 **新开 Chat** 再打开 Skills 菜单验收。

## 瘦启动冒烟

1. 新开 Chat → 应自动读 `boot.md`
2. 喊 `$oneos-pm-product` 或 `$yanchufasui` → 签名「王冕驱动 · 言出法随 / 产品交付」
3. 业务题应能升档到同仓 `../fayanruju/SKILL.md` 或 `../oneos-biz-rules/SKILL.md`

## 旧入口

`wangmian-twin` 兼容 stub 已移出 skills 目录；勿再装回。
