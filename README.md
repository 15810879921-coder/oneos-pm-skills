# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

## Skills 列表

| Skill | 说明 | 安装 / 更新 |
|-------|------|----------|
| **`YunxiaoPM`**（推荐 · 口令 YunxiaoPM / 需求任务） | 记录需求 → 分析/设计 → 交棒待开发；压缩点选；迭代只挂交付；**不建【开发】/【测试】** | 见下方「发给产品同事」 |
| **`yunxiao-development-delivery`** | 接收待开发交棒 → 分配开发 → 开始/完成开发 → Bug闭环 → 严格按项目唯一测试主管创建测试任务 | 见下方「云效开发交付」 |
| `oneos-autoprd`（展示名 OneOS-AutoPRD） | 整模块 AutoPRD + 标注目录；**需求定稿**写功能变更；云效描述「需求说明/更新内容」 | 见下方 |
| `AutoRDO` | 清洗为标题+描述；自动识别类型/优先级/标签/提交部门/提交人；多行拆多条；有待确认则强制 Plan | 见下方 |
| `AutoVUL` | 按云效迭代名生成 PC 版本更新日志 | 见下方 |
| `yunxiao-requirement-lifecycle` | 旧版云效全生命周期口令（**产品会话勿与 YunxiaoPM 同时挂载**） | 见下方 |

---

## YunxiaoPM · 产品经理云效自动化（推荐）

产品侧从「记需求」到「交棒开发」的正式 Skill（口令也可说 **YunxiaoPM / 需求任务 / `/YunxiaoPM`**）：

- 需求状态 = 看板真相；每需求最多 1 条 **【交付】**；下挂 **【分析】/【设计】**
- 压缩点选 `1a2b3a4d`（类型/项目/优先级/标签）；查重只认 `ONEOS-xx`
- 快轨待开发 / 编号直推；创建迭代 **只挂【交付】**（不挂需求）
- 终点：待开发且【交付】负责人=何斐；**不建【开发】/【测试】**

**不要**在同一会话同时挂载 `yunxiao-requirement-lifecycle`，避免双建任务。

**开发部门对接原理：** [`docs/YunxiaoPM-实现原理-开发Skill对接.md`](docs/YunxiaoPM-实现原理-开发Skill对接.md)

### 发给产品同事 · 丢进 AI 一键安装（推荐复制整段）

把下面整段发给同事，让他们粘贴到 Cursor / Claude 对话即可（AI 会代跑命令）：

```text
请帮我全局安装 OneOS 产品云效 Skill（Cursor）：

npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -g -y

装完后：
1. 确认可用口令「记录需求」或「/YunxiaoPM」触发
2. 使用前请先在浏览器登录 https://devops.aliyun.com（Cookie 会话）
3. 凡写云效会先 Plan，我确认后再执行
```

**产品套装（云效 + 清洗诉求 + 写 PRD，推荐一次装齐）：**

```text
请帮我全局安装 OneOS 产品 Skill 套装（Cursor）：

npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -g -y

装完后确认口令可用：记录需求 / AutoRDO / oneos-autoprd。
使用云效前请先登录 https://devops.aliyun.com 。
```

### 终端自己装（同事有命令行时）

全局 Cursor（推荐）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -g -y
```

同时装 Cursor + Claude Code：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a claude-code -g -y
```

仅当前项目：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -y
```

### 更新到最新版

```bash
npx skills update YunxiaoPM
```

或对 AI 说：

```text
请帮我更新 YunxiaoPM：npx skills update YunxiaoPM
```

> **曾安装旧名 `YunxiaoPMapp` 的同事：** 请改装新名（旧目录可删）：
> `npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -g -y`

### 怎么用（装完后对 AI 说）

```text
/YunxiaoPM 提需求
记录需求：…；推进至=暂不推进|已确认|分析中|设计中|设计完成|待开发|待开发(快轨)
受理确认：ONEOS-xx
开始分析：ONEOS-xx
开始设计：ONEOS-xx；交付任务=ONEOS-a；分析任务=ONEOS-b
设计完成：ONEOS-xx；设计任务=ONEOS-c；原型=…
交棒开发：ONEOS-xx；交付任务=ONEOS-a
快轨待开发：ONEOS-xx
创建迭代：版本类型=副；交付任务=ONEOS-a,ONEOS-b；名称前缀=ONEOS_PC端
```

凡写云效会先进入 Plan，确认后再执行。

仓库：https://github.com/15810879921-coder/oneos-pm-skills

---

## yunxiao-development-delivery · 云效开发交付

从 `YunxiaoPM` 的待开发交棒开始，负责创建和分配【开发】任务、开发实现、完成开发、Bug修复、代码资产提交以及测试交接。

v7.7.0 提供两种开发任务执行模式：

- `/go 开发任务:任务=ONEOS-789 输出执行方案`：完整读取需求与代码事实后输出可落地方案，确认前零写入；确认时先检查方案快照是否仍然有效。
- `/go 开发任务:任务=ONEOS-789`：内部执行同等分析和门禁，不展示方案、不等待确认，直接实现。
- 批量实现固定使用直接执行模式，不逐项等待方案确认。
- 测试交接继续要求当前项目恰好一名“测试主管”，并回读验证测试任务负责人用户 ID。

### 全局安装到 Cursor

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yunxiao-development-delivery -a cursor -g -y
```

### 全局安装到 Codex

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yunxiao-development-delivery -a codex -g -y
```

### 更新已安装的 Skill

```bash
npx skills update yunxiao-development-delivery
```

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

建需求描述时先跑本 Skill；**产品侧写云效请用 `YunxiaoPM`**（勿与旧 `yunxiao-requirement-lifecycle` 同会话混用）。设计完成阶段由 YunxiaoPM 调用本 Skill 灌 PRD。

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

将碎片化文字、聊天记录、录音转写或**反馈台账**，在**保留原意**前提下拆解为清晰**标题**与**描述**，并**自动识别**类型（【新增】/【优化】）、优先级（P1/P2/P3）、标签（标准模块+端）、提交部门、提交人。清洗 ONE-OS 材料时先读 `oneos-domain.md` 与 `meta-fields.md`。  
多行独立诉求自动拆成多份；**有待确认则同轮强制进 Plan**（无需再说「确认待确认」）。本 Skill 只出推荐元数据，不直接写云效打标。

### 何时使用

- 收到碎片的聊天记录、会议速记、录音转写稿时
- 粘贴反馈台账（含部门/优先级/模块/反馈人列）时
- 记录需求到云效前准备标准标题、描述与元数据
- 口令：`AutoRDO：<粘贴聊天或台账>`

### 怎么用

1. 安装：`npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -y`
2. 对 AI 说：`AutoRDO：<材料>`；台账可整表粘贴
3. 输出每条含：标题、类型、优先级、标签、提交部门、提交人、描述；有待确认则自动切 Plan 选择题确认
4. 定稿后交 YunxiaoPM 按条记录需求（可带上元数据字段）

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
    ├── YunxiaoPM/
    ├── yunxiao-development-delivery/
    ├── oneos-autoprd/
    ├── yunxiao-requirement-lifecycle/
    ├── AutoVUL/
    └── AutoRDO/
```

---

## 仓库地址

https://github.com/15810879921-coder/oneos-pm-skills

---

## License

MIT
