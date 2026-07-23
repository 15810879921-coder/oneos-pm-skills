# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

## Skills 列表

| Skill | 说明 | 安装 / 更新 |
|-------|------|----------|
| `oneos-autoprd`（展示名 OneOS-AutoPRD） | 整模块 AutoPRD + 标注目录；**需求定稿**写功能变更；云效建需求写说明/更新内容；推进到分析中/设计中/待开发时建同名任务 | 见下方 |
| `yunxiao-requirement-lifecycle` | 云效需求全生命周期口语化口令 + 统一运营管理平台记录需求快路径（A/B/C 门禁、30 标签、API 建单打标） | 见下方 |
| `AutoVUL` | 按云效迭代名拉关联需求，自动生成 PC 版本更新日志（含成功/失败重输） | 见下方 |
| `AutoRDO` | 将碎片化聊天记录、语音转写文本清洗整理为书面「原始诉求」（去口头禅、末尾去句号、标注待确认） | 见下方 |

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

### 需求定稿

对 AI 说：

```text
保险采购需求定稿
```

会在 PRD 下方追加「功能变更记录」（仅功能/逻辑），并更新 `.spec/autoprd-baseline.json`。

### 与云效组合

建需求时先跑本 Skill，再写云效「需求说明」「更新内容」。口令见 `yunxiao-requirement-lifecycle`。

需求推进到 **分析中 / 设计中 / 待开发** 时，会自动创建与需求**同名**的关联任务（标签与时间沿用需求；分析中/设计中负责人=创建人，待开发负责人=何斐）。详见 `skills/oneos-autoprd/references/yunxiao-stage-tasks.md`。

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

## AutoVUL · 版本更新日志

测试人员输入云效**迭代名称**，自动拉取该迭代关联需求并生成 OneOS PC 对外版本更新日志；也支持手动粘贴清单。

原理说明（可转发同事）：
- Markdown：[`docs/OneOS-AutoVUL-Skill运作原理说明.md`](docs/OneOS-AutoVUL-Skill运作原理说明.md)
- HTML（可打印/转 PDF）：[`docs/OneOS-AutoVUL-Skill运作原理说明.html`](docs/OneOS-AutoVUL-Skill运作原理说明.html)

### 何时使用

- 测试发版前：按云效迭代生成 PC 整包更新日志
- 工作台「版本更新」弹框 / 对内发版通知需要统一口径
- 迭代名读失败后，重新输入名称再生成

### 怎么用

1. 在 Cursor 或 Codex 终端粘贴安装命令并执行（或把「发给 AI」文案粘贴给 Agent 代装）。
2. 对 AI 说：按 `$AutoVUL` 生成版本更新日志；并给出**迭代名称**（及可选更新时间）。
3. 看反馈：`✅` 成功则核对需求清单并出成稿；`❌` 失败则重新输入迭代名称。
4. 确认成稿后对外发布；预计维护时长由人工单独通知。
5. 云效不可用时：用 `skills/AutoVUL/input-template.md` 手动清单兜底。

口令示例：

```text
按 $AutoVUL 生成版本更新日志。
项目：统一运营管理平台PC端
迭代名称：V1.1.5发版迭代
更新时间：07月16日16:00
```

### 一键安装

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoVUL -a cursor -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill：
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoVUL -a cursor -y
```

路径：`skills/AutoVUL` · 更新已安装：`npx skills update AutoVUL`

---

## yunxiao-requirement-lifecycle · 云效需求生命周期

产品/研发/测试用**短口令**推进云效需求（记录需求、开始分析、安排开发、提交测试、发布成功、验收通过等）；统一运营管理平台「记录需求」走已验证 **API 快路径**（Plan 点选优先级 / 推进至 / 标签 → AutoPRD → 建单 → 打标 → 状态推进）。

### 何时使用

- 口语化口令：`记录需求`、`确认需求`、`开始分析`、`开始设计`、`安排开发`、`提交测试`、`测试完成`、`发布成功`、`验收通过`
- 统一运营管理平台建需求：配合 `$oneos-autoprd`，A/B/C 三门禁 + 30 项云效标签 catalog
- 需求推进至分析中 / 设计中 / 待开发：自动建与需求同名阶段任务（见 skill 内 `auto-stage-task.md`）

完整可复制建单口令：`skills/yunxiao-requirement-lifecycle/references/oneos-pc-record-requirement-prompt.md`

### 一键安装

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yunxiao-requirement-lifecycle -a cursor -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill：
npx skills add 15810879921-coder/oneos-pm-skills --skill yunxiao-requirement-lifecycle -a cursor -y
```

### 建议同时安装「记录需求快路径」规则（可选）

```bash
mkdir -p ~/.cursor/rules
curl -fsSL https://raw.githubusercontent.com/15810879921-coder/oneos-pm-skills/main/rules/yunxiao-record-requirement-fast-path.mdc \
  -o ~/.cursor/rules/yunxiao-record-requirement-fast-path.mdc
```

### 使用方式

建需求（先点选 A/B/C，再执行）：

```text
使用 $yunxiao-requirement-lifecycle + $oneos-autoprd
记录需求到云效 · 统一运营管理平台
【需求名】…
【描述来源】$oneos-autoprd，原型/模块：…
请先 Plan 让我点选 A 优先级、B 推进至、C 标签（30 项 catalog）。
```

日常推进：

```text
项目：统一运营管理平台PC端
开始分析：ONEOS-91；负责人=王冕
```

### 更新已安装的 Skill

```bash
npx skills update yunxiao-requirement-lifecycle
```

---

## AutoRDO · 需求描述优化（原始诉求）

将碎片化文字、聊天记录或录音转写文本，在**保留原意**前提下整理成书面表达，供入库写入云效需求 `## 原始诉求（AutoRDO）`。

### 何时使用

- 收到碎片的聊天记录、会议速记、录音转写稿时
- 记录需求到云效前，将需求材料清洗为标准化格式
- 口令：`AutoRDO：<粘贴聊天或转写>`

### 怎么用

1. 在 Cursor 或 Codex 终端粘贴安装命令并执行（或把「发给 AI」文案粘贴给 Agent 代装）。
2. 对 AI 说：`AutoRDO：<粘贴聊天记录或转写文本>`
3. AI 将输出格式化的 `## 原始诉求（AutoRDO）`，去除口头禅与句末句号，并梳理待确认事项。

### 一键安装

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill：
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -y
```

路径：`skills/AutoRDO` · 更新已安装：`npx skills update AutoRDO`

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
│   ├── OneOS-AutoPRD-Skill运作原理说明.pdf
│   ├── OneOS-AutoVUL-Skill运作原理说明.md
│   └── OneOS-AutoVUL-Skill运作原理说明.html
├── rules/
│   ├── oneos-autoprd-sync.mdc          # 可选：改原型自动跟进 PRD
│   └── yunxiao-record-requirement-fast-path.mdc  # 可选：记录需求 A/B/C 门禁与快路径
└── skills/
    ├── oneos-autoprd/
    │   ├── SKILL.md
    │   └── references/
    ├── yunxiao-requirement-lifecycle/
    │   ├── SKILL.md
    │   ├── assets/                       # oneos-pc-runtime-ids.json、标签 catalog
    │   ├── references/                   # 快路径、口语口令、完整建单提示词
    │   └── scripts/
    ├── AutoVUL/
    │   ├── SKILL.md
    │   ├── examples.md
    │   ├── input-template.md
    │   ├── module-role-mapping.md
    │   └── references/
    │       └── yunxiao-sprint.md
    └── AutoRDO/
        ├── SKILL.md
        ├── agents/
        └── references/
```

---

## 仓库地址

https://github.com/15810879921-coder/oneos-pm-skills

---

## License

MIT
