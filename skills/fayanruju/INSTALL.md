# 安装 / 更新 法眼如炬（fayanruju）

## 同事一键（npx skills · 与 YunxiaoPM 同通道）

安装页：https://15810879921-coder.github.io/oneos-pm-skills/

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

更新：

```bash
npx skills update fayanruju yanchufasui mingjingzhishui -g -y
```

完整 KB 在 oneos-v2 `src/resources/oneos-knowledge-base/`。请在 **oneos-v2 工作区**里用法眼。

**本尊机**不要用 `-g` 覆盖仓内软链。

## 正式单源（oneos-v2）

1. 打开 / 拉取 **oneos-v2**（Skill 正文：`.cursor/skills/fayanruju/`）
2. 知识库单源：`src/resources/oneos-knowledge-base/`（Skill 内 `kb/` 为软链）
3. **新开对话**，口令 `法眼如炬` / `$fayanruju`
4. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包

## 本尊机 · 菜单去重（强制）

Cursor / Codex 会同时索引「仓内 Skill」与 `~/.cursor/skills`、`~/.codex/skills`。  
**禁止**再挂全局软链，否则菜单会出现多份法眼如炬。

- ✅ 只留：`oneos-v2/.cursor/skills/fayanruju/`（当前 v1.3.7）
- ✅ 配对躯干：同仓 `oneos-v2/.cursor/skills/yanchufasui/`（言出法随 · 仓库单源 v1.4.61）
- ❌ 不要：`~/.cursor/skills/fayanruju`、`~/.codex/skills/fayanruju` 实体第二份（软链到仓内可保留供 User Rule）
- ❌ 不要：`~/.codex/skills/fayanruju.bak-*`（备份也勿放在 skills 目录；`name: fayanruju` 会被当成第二份）
- ❌ 旧入口 `wangmian-brain` / `wangmian-twin` stub **已下架**；口令请用 `法眼如炬` / `言出法随`

清理后请 **新开 Chat** 再打开 Skills 菜单验收（旧会话缓存可能仍显示）。

## 冒烟

在 oneos-v2 根目录：

```bash
python3 .cursor/skills/fayanruju/scripts/smoke-system-qa.py
```

## 旧入口

`wangmian-brain` / `wangmian-twin` 兼容 stub 已移出 skills 目录；勿再装回。
