# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

## Skills 列表

| Skill | 说明 | 安装命令 |
|-------|------|----------|
| `oneos-autoprd` | 整模块产品需求说明（AutoPRD）+ 同步 Axhub 标注目录 PRD | 见下方 |
| `version-update-log-format` | OneOS PC 版本更新日志：新功能/Bug修复分类、同模块合并 | 见下方 |

---

## oneos-autoprd · 产品需求说明（AutoPRD）

为 OneOS 业务模块生成**产品经理可读**的需求说明：目标、边界、用户故事（业务条线说明口径：起点 → 怎么运作 → 闭环）、故事点、正逆向、流程图、验收；并同步到 Axhub Make 标注工具「原型目录」。

**适用场景**：整模块 PRD、改原型后同步需求文档、给业务/研发对齐评审

原理说明（可转发同事）：[`docs/OneOS-AutoPRD-Skill运作原理说明.pdf`](docs/OneOS-AutoPRD-Skill运作原理说明.pdf)

### 一键安装

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd
```

仅安装到 Cursor：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -y
```

安装到用户目录（全局，所有项目可用）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -g -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill：
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -y
```

### 建议同时安装「改原型自动跟进」规则（可选）

Skill 负责「怎么写」；Rule 负责「改了原型别忘同步」。把仓库里的规则文件复制到本机：

```bash
# 全局（所有项目）
mkdir -p ~/.cursor/rules
curl -fsSL https://raw.githubusercontent.com/15810879921-coder/oneos-pm-skills/main/rules/oneos-autoprd-sync.mdc \
  -o ~/.cursor/rules/oneos-autoprd-sync.mdc

# 或仅当前 OneOS 项目
mkdir -p .cursor/rules
curl -fsSL https://raw.githubusercontent.com/15810879921-coder/oneos-pm-skills/main/rules/oneos-autoprd-sync.mdc \
  -o .cursor/rules/oneos-autoprd-sync.mdc
```

### 使用方式

对 AI 说，例如：

```text
按 $oneos-autoprd 为「保险采购」写整模块产品需求说明，并同步到标注目录。
```

或在改完原型后：

```text
按 oneos-autoprd 同步更新本原型的 PRD 和标注目录。
```

### 更新已安装的 Skill

```bash
npx skills update oneos-autoprd
```

---

## version-update-log-format · 版本更新日志

把发版变更清单整理成可直接对外发布的 OneOS PC 版本更新日志正文。

**适用场景**：发版公告、工作台更新弹框文案、内部版本通知

### 一键安装

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill version-update-log-format
```

仅安装到 Cursor：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill version-update-log-format -a cursor -y
```

安装到用户目录（全局，所有项目可用）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill version-update-log-format -g -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill：
npx skills add 15810879921-coder/oneos-pm-skills --skill version-update-log-format -a cursor -y
```

### 使用方式

1. 填写 `skills/version-update-log-format/input-template.md`
2. 对 AI 说：

```text
按 $version-update-log-format 生成 OneOS PC 版本更新日志成稿。
```

### 更新已安装的 Skill

```bash
npx skills update version-update-log-format
```

---

## 一次安装仓库内全部 Skill

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill '*' -a cursor -y
```

### 查看仓库内所有 Skill

```bash
npx skills add 15810879921-coder/oneos-pm-skills --list
```

---

## 仓库结构

```text
oneos-pm-skills/
├── README.md
├── docs/
│   └── OneOS-AutoPRD-Skill运作原理说明.pdf
├── rules/
│   └── oneos-autoprd-sync.mdc          # 可选：改原型自动跟进 PRD
└── skills/
    ├── oneos-autoprd/
    │   ├── SKILL.md
    │   └── references/
    └── version-update-log-format/
        ├── SKILL.md
        ├── examples.md
        ├── input-template.md
        └── module-role-mapping.md
```

---

## 仓库地址

https://github.com/15810879921-coder/oneos-pm-skills

---

## License

MIT
