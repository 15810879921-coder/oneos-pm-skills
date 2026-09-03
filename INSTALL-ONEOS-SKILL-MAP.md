# OneOS 用途名 Skill · 安装

发给同事请直接复制 **「同事一键」** 整段。装完 **新开 Chat**。

## 仓内单源

路径：工作仓 `.cursor/skills/oneos-*/`（本尊机花名运行时链到 **oneos-v2**）

| 用途名 | 目录 | 状态 |
|--------|------|------|
| 任务指路 | `oneos-wave-router` | 启用 |
| 产品交付 | `oneos-pm-product` | 启用（运行时→yanchufasui） |
| 业务口径 | `oneos-biz-rules` | 启用（运行时→fayanruju） |
| 开发落地 | `oneos-dev-delivery` | 启用（运行时→mingjingzhishui） |
| 系统架构 | `oneos-system-arch` | 启用（运行时→dingliqiankun）· 单源 **oneos_pc** |
| 测试验收 | `oneos-qa-verify` | 启用（云效工具→YunxiaoQA） |
| 体验规范 | `oneos-ux-guide` | 启用 |
| 数据口径 | `oneos-data-metrics` | 启用 · 单源 **oneos_pc** |
| 知识典藏 | `oneos-kb-ops` | 启用 · 单源 **oneos_pc** |
| 知识库意图分析 | `oneos-kb-intent-analyst` | 启用 · 单源 **oneos_pc** |
| 项目汇报 | `oneos-briefing-aide` | 启用 · 单源 **oneos_pc** |
| 上线守闸 | `oneos-release-gate` | **休眠** |

速查：[`oneos-wave-router/SKILL-MAP.md`](oneos-wave-router/SKILL-MAP.md)

## 同事一键（npx skills · 安装页）

安装页：https://15810879921-coder.github.io/oneos-pm-skills/

仓库：https://github.com/15810879921-coder/oneos-pm-skills

花名包 `yanchufasui` / `fayanruju` / `mingjingzhishui` **已下架**，装用途名即可。系统架构运行时已并进 `oneos-system-arch`。

```bash
# 曾装过旧花名：先卸再装（没有可忽略报错）
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills remove mingjingzhishui -g -y -a cursor -a codex

npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-wave-router -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-pm-product -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-biz-rules -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-dev-delivery -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-qa-verify -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-ux-guide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-data-metrics -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-ops -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-release-gate -a cursor -a codex -g -y
```

只装新分身（已有旧包时）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-data-metrics -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-ops -a cursor -a codex -g -y
```

更新：

```bash
npx skills update oneos-wave-router oneos-pm-product oneos-biz-rules oneos-dev-delivery oneos-system-arch oneos-qa-verify oneos-ux-guide oneos-data-metrics oneos-kb-ops oneos-kb-intent-analyst oneos-briefing-aide oneos-release-gate -g -y
```

装完 **新开 Chat**。完整知识库与改原型请打开工作仓（oneos_pc / oneos-v2）。

口令速查：`/oneos-briefing-aide` 项目汇报 · `/oneos-system-arch` 系统架构 · `/oneos-kb-intent-analyst` 意图分析。一期上线守闸休眠，发版权在本尊。

## 本尊机软链

```bash
cd ~/.cursor/skills
for s in oneos-wave-router oneos-pm-product oneos-biz-rules oneos-dev-delivery oneos-qa-verify oneos-ux-guide oneos-release-gate; do
  ln -sfn "$HOME/oneos-v2/.cursor/skills/$s" "$s"
done

# 总构官 / 度量官 / 典藏官 / 意图分析师 / 讲解官：单源在 oneos_pc（禁 cp）
REPO="$HOME/oneos_pc"
for s in oneos-system-arch dingliqiankun oneos-data-metrics oneos-kb-ops oneos-kb-intent-analyst oneos-briefing-aide; do
  ln -sfn "$REPO/.cursor/skills/$s" ~/.cursor/skills/$s
  ln -sfn "$REPO/.cursor/skills/$s" ~/.agents/skills/$s
  ln -sfn "$REPO/.cursor/skills/$s" ~/.codex/skills/$s
done
```

装完 **新开 Chat**。花名软链必须指向 **oneos-v2**（`yanchufasui` / `fayanruju` / `mingjingzhishui`）；本仓 `oneos_pc/.cursor/skills/` 下这三名只允许是通向 v2 的软链，**禁止实体副本**。  
**本尊机**不要用 `-g` 覆盖仓内软链。

## 同事

优先告诉用途名口令；花名仅兼容。一期上线守闸休眠，发版权在本尊。
