# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

**同事安装页（一键复制安装/更新）：** https://15810879921-coder.github.io/oneos-pm-skills/

## Skills 列表

| Skill | 说明 | 安装 / 更新 |
|-------|------|----------|
| **`YunxiaoPM`**（推荐 · 口令 YunxiaoPM / 需求任务） | 记录需求 → 分析/设计 → 交棒待开发；压缩点选；迭代只挂交付；**不建【开发】/【测试】** | 见下方「发给产品同事」 |
| **`yunxiao-development-delivery`** | 接收待开发交棒 → 分配开发 → 开始/完成开发 → Bug闭环 → 严格按项目唯一测试主管创建测试任务 | 见下方「云效开发交付」 |
| **`YunxiaoQA`** | 接收测试任务 → 执行用例 → 创建/复测缺陷 → 测试完成 → 交接发布 | Codex/Cursor 双版本 |
| **`yunxiao-release-operations`** | 组建发布批次 → 生产发布 → 上线验证 → 自动回滚/重新发布 → 交接产品验收 | Codex/Cursor 双版本 |
| `oneos-autoprd`（展示名 OneOS-AutoPRD） | 整模块 AutoPRD + 标注目录；**需求定稿**写功能变更；云效描述「需求说明/更新内容」 | 见下方 |
| `AutoRDO` | 清洗为标题+描述；自动识别类型/优先级/标签/提交部门/提交人；多行拆多条；有待确认则强制 Plan | 见下方 |
| `AutoVUL` | 按云效迭代名生成 PC 版本更新日志 | 见下方 |
| **`yanchufasui`**（言出法随） | 王冕驱动产品分身：落需求 / 改原型；写云效先确认 | 见下方「王冕驱动三 skill」 |
| **`fayanruju`**（法眼如炬） | 口径裁决；完整 KB 在 oneos-v2 工作区 | 见下方「王冕驱动三 skill」 |
| **`mingjingzhishui`**（明镜止水） | AI 开发分身：只吃交棒包；双轨本机模拟（原型→真仓） | 见下方「王冕驱动三 skill」 |
| **`oneos-wave-router`**（任务指路） | 只指路不办事：下一步喊哪个 Skill | 见下方「七 Skill 用途名」 |
| **`oneos-pm-product`**（产品交付） | AI 产品经理一号位；运行时→言出法随 | 见下方「七 Skill 用途名」 |
| **`oneos-biz-rules`**（业务口径） | 规则一号位；运行时→法眼如炬 | 见下方「七 Skill 用途名」 |
| **`oneos-dev-delivery`**（开发落地） | AI 开发经理一号位；运行时→明镜止水 | 见下方「七 Skill 用途名」 |
| **`oneos-qa-verify`**（测试验收） | 测试一号位；云效工具层→YunxiaoQA | 见下方「七 Skill 用途名」 |
| **`oneos-ux-guide`**（体验规范） | 体验一号位；UI/AI 交互原则 | 见下方「七 Skill 用途名」 |
| **`oneos-release-gate`**（上线守闸） | 发布一号位【一期休眠】 | 见下方「七 Skill 用途名」 |

> **已下架：** `yunxiao-requirement-lifecycle`（旧全生命周期 Skill）已从本仓库删除。产品侧云效**只**用 `YunxiaoPM`；`oneos-autoprd` **只**写 PRD/标注/描述，**不**建同名阶段任务。本机若仍有旧包请卸载：  
> `npx skills remove yunxiao-requirement-lifecycle -g -y -a cursor -a codex`

---

## 双端一键安装 / 更新（Cursor + Codex）

统一用 [skills.sh](https://skills.sh) 的 `npx skills`；`-a cursor -a codex` 一次装到两端。

### 双版本发布模型

六套生命周期 Skill 使用同一份业务规则源，发布时生成两个独立版本，避免两端业务口径漂移：

- **Codex 版**：包含 `SKILL.md`、业务资源、跨平台启动器和 `agents/openai.yaml`。
- **Cursor 版**：包含相同的 `SKILL.md`、业务资源和跨平台启动器，不携带 Codex 专用 UI 元数据。
- Windows 与 macOS 均通过 Skill 自带启动器选择本机可用 Python；Skill 不读取 `~/.cursor/skills`、`~/.codex/skills` 或固定盘符。
- 双版本离线包位于 [`packages/codex`](packages/codex) 与 [`packages/cursor`](packages/cursor)，SHA-256 见各目录 `manifest.json`。

只安装 Codex 版：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a codex -g -y
```

只安装 Cursor 版：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -g -y
```

构建六套双版本离线包：

```powershell
pwsh -File ./scripts/build-dual-client-packages.ps1
```

### 产品套装（推荐）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -a codex -g -y
```

### 一键更新已装 Skill

```bash
npx skills update YunxiaoPM AutoRDO oneos-autoprd -g -y
```

### 王冕驱动三 skill（言出法随 + 法眼如炬 + 明镜止水）

与 YunxiaoPM 同一套 `npx skills`。同事安装页：https://15810879921-coder.github.io/oneos-pm-skills/

```bash
# 曾装过旧版：先卸再装（没有可忽略报错）
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

更新：

```bash
npx skills update yanchufasui fayanruju mingjingzhishui -g -y
```

装完请 **新开 Chat**。完整知识库与改原型请打开 **oneos-v2** 工作区；真仓本机根 `~/oneos-prod`。本机若已把 `~/.cursor/skills/{yanchufasui,fayanruju,mingjingzhishui}` 软链到 oneos-v2，不要用 `-g` 覆盖。

丢进 AI：

```text
请帮我全局安装王冕驱动三 skill 到 Cursor + Codex：

先卸旧版（若曾装过言出法随/法眼；没有可忽略报错）：
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex

再安装：
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y

装完请新开 Chat。口令：言出法随 / $yanchufasui ；法眼如炬 / $fayanruju ；明镜止水 / $mingjingzhishui
```

### 七 Skill 用途名（推荐团队 · 用途名优先）

同事优先喊用途名口令；花名三 skill 为运行时深协议，建议同装。上线守闸一期休眠。  
**曾装过旧版言出法随 / 法眼：一键脚本会先 `remove` 再装新包。**

#### 职责与功用

| 用途名 · 称号 | 职责 | 什么时候喊 | 不做 |
|---------------|------|------------|------|
| **任务指路 · 协调官** `oneos-wave-router` | 只指路，不代打 | 不知道该喊谁 | 不改需求/码/云效 |
| **产品交付 · 主理人** `oneos-pm-product`（花名言出法随） | PRD · 可点原型 · 验收剧本 · 交棒包 | 写需求、出原型、交开发 | 止于交开发；不上线 |
| **业务口径 · 合规官** `oneos-biz-rules`（花名法眼如炬） | 能不能做、规则/字段裁决 | 问规则、冲突、查口径 | 不改原型/真码 |
| **开发落地 · 架构师** `oneos-dev-delivery`（花名明镜止水） | 只吃交棒；双轨落地；回执 | 按包改原型/真仓、待测交接 | 无包拒做；不合 Master |
| **测试验收 · 质检官** `oneos-qa-verify` | 测计划 · 证据 · 缺陷 · 打回 | 开始测试、提缺陷、复测 | 不替本尊点发版 |
| **体验规范 · 设计官** `oneos-ux-guide` | UI/AI 交互原则、反 AI 味 | 页面评审、交互争议 | 不定业务能不能做 |
| **上线守闸 · 安全官** `oneos-release-gate` | **一期休眠**；发版权在本尊 | 问发版会被拦回 | 禁止自动推生产 |

主链路：`产品交付 →（业务口径）→ 开发落地 → 测试验收 → 【本尊上线】`

```bash
# 先卸旧版（没有可忽略报错）
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-wave-router -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-pm-product -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-biz-rules -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-dev-delivery -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-qa-verify -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-ux-guide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-release-gate -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

更新：

```bash
npx skills update oneos-wave-router oneos-pm-product oneos-biz-rules oneos-dev-delivery oneos-qa-verify oneos-ux-guide oneos-release-gate yanchufasui fayanruju mingjingzhishui -g -y
```

丢进 AI：

```text
请帮我全局安装 OneOS 七 Skill 用途名 + 三花名运行时到 Cursor + Codex：

【七分身职责速览】
- 任务指路：只指路喊谁，不代打
- 产品交付（言出法随）：PRD·原型·交棒；止于交开发
- 业务口径（法眼如炬）：能不能做；不改码
- 开发落地（明镜止水）：只吃交棒双轨落地；止于待测
- 测试验收：证据·缺陷·打回；不点发版
- 体验规范：UI/AI 原则；不定业务口径
- 上线守闸：一期休眠，发版权在本尊

重要：若本机曾装过旧版言出法随 / 法眼如炬，必须先卸再装（没有可忽略报错）：
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex

再安装：
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-wave-router -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-pm-product -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-biz-rules -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-dev-delivery -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-qa-verify -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-ux-guide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-release-gate -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y

装完请新开 Chat。
用途名：任务指路 / 产品交付 / 业务口径 / 开发落地 / 测试验收 / 体验规范 / 上线守闸（休眠）。
```

### 丢进 AI 代装（复制整段）

```text
请帮我全局安装 OneOS 产品 Skill 套装到 Cursor + Codex：

npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -a codex -g -y

若本机曾装 yunxiao-requirement-lifecycle，请先卸载：
npx skills remove yunxiao-requirement-lifecycle -g -y -a cursor -a codex

装完后确认口令可用：记录需求 / AutoRDO / oneos-autoprd。
使用云效前请先登录 https://devops.aliyun.com 。
```

仓库：https://github.com/15810879921-coder/oneos-pm-skills

---

## YunxiaoPM · 产品经理云效自动化（推荐）

产品侧从「记需求」到「交棒开发」的正式 Skill（口令也可说 **YunxiaoPM / 需求任务 / `/YunxiaoPM`**）：

- 需求状态 = 看板真相；每需求最多 1 条 **【交付】**；下挂 **【分析】/【设计】**
- 压缩点选 `1a2b3a4d`（类型/项目/优先级/标签）；查重只认 `ONEOS-xx`
- 快轨待开发 / 编号直推；创建迭代 **只挂【交付】**（不挂需求）
- 终点：待开发且【交付】负责人=何斐；**不建【开发】/【测试】**

**开发部门对接原理：** [`docs/YunxiaoPM-实现原理-开发Skill对接.md`](docs/YunxiaoPM-实现原理-开发Skill对接.md)

### 发给产品同事 · 丢进 AI 一键安装（推荐复制整段）

```text
请帮我全局安装 OneOS 产品云效 Skill 到 Cursor + Codex：

npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -g -y

装完后：
1. 确认可用口令「记录需求」或「/YunxiaoPM」触发
2. 使用前请先在浏览器登录 https://devops.aliyun.com（Cookie 会话）
3. 凡写云效会先 Plan，我确认后再执行
```

### 终端自己装

```bash
# Cursor + Codex 全局（推荐）
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -g -y

# 再加 Claude Code
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -a claude-code -g -y

# 仅当前项目
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -y
```

### 更新到最新版

```bash
npx skills update YunxiaoPM -g -y
```

或对 AI 说：

```text
请帮我更新 YunxiaoPM（Cursor + Codex）：npx skills update YunxiaoPM -g -y
```

> **曾安装旧名 `YunxiaoPMapp` 的同事：** 请改装新名（旧目录可删）：
> `npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoPM -a cursor -a codex -g -y`

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

v9.3.0 在保留两种开发任务执行模式、真实变更回报和测试交接的基础上，补齐官方 CLI 闭环、开发完成工时审计，并保证新建开发任务继承交付优先级：

- 云效 Projex、Codeup、Flow、AppStack 的读写统一通过官方 `aliyun devops` CLI，不使用浏览器或视觉回退。
- 新建`【开发】`任务复制来源`【交付】`优先级并按标识ID回读；复用已有开发任务时不覆盖其优先级。
- 开发完成时工作日期只填写开始/完成自然日期；精确开始与完成时间写入工作描述。计算工时与云效按项目精度回读的记录工时同时留痕后，才允许关闭开发任务。
- 批量修复 Bug 先冻结范围，循环修改期间不提交、不推送、不发布；全部完成后按提交组统一提交、创建并合并唯一 MR。
- 测试流水线只使用项目已经创建好的定义：按Codeup代码源、目标分支和`test/测试`名称唯一匹配；手动模式只启动一次，MR合并自动触发模式只关联唯一匹配运行。开发Skill不创建、复制或修改流水线及服务连接。

- `开发任务:任务=ONEOS-789 输出执行方案`：完整读取需求与代码事实后输出可落地方案，确认前零写入；确认时先检查方案快照是否仍然有效。
- `开发任务:任务=ONEOS-789`：内部执行同等分析和门禁，不展示方案、不等待确认，直接实现。
- 批量实现固定使用直接执行模式，不逐项等待方案确认。
- 开发任务、完成开发、单个/批量Bug节点必须输出实际执行操作，以及每个新增、修改、删除、重命名文件的代码位置、行为变化、原因、行数和验证证据。
- 批量节点逐任务或逐Bug报告，阻塞节点也必须列出当前差异和未执行动作；已有脏文件不会被冒充为本次成果。
- 测试交接继续要求当前项目恰好一名“测试主管”，并回读验证测试任务负责人用户 ID。
- 完成开发创建或复用【测试】任务时，会在保留人工描述的前提下幂等补充“测试建议”和“临时需求变更点”；描述回读通过后才允许需求进入“待测试”。
- 【测试】任务必须是源【交付】任务的正式子项，并同时关联产品需求；父交付、关联需求、负责人和描述任一回读失败都会阻塞交测。

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

### 一键安装（Cursor + Codex）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -a codex -g -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill 到 Cursor + Codex：
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-autoprd -a cursor -a codex -g -y
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

建需求描述时先跑本 Skill；**产品侧写云效请用 `YunxiaoPM`**（本 Skill 不建阶段任务）。设计完成阶段由 YunxiaoPM 调用本 Skill 灌 PRD。

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
npx skills update oneos-autoprd -g -y
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

### 一键安装（Cursor + Codex）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoVUL -a cursor -a codex -g -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill 到 Cursor + Codex：
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoVUL -a cursor -a codex -g -y
```

路径：`skills/AutoVUL` · 更新已安装：`npx skills update AutoVUL -g -y`

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

1. 安装：`npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -a codex -g -y`
2. 对 AI 说：`AutoRDO：<材料>`；台账可整表粘贴
3. 输出每条含：标题、类型、优先级、标签、提交部门、提交人、描述；有待确认则自动切 Plan 选择题确认
4. 定稿后交 YunxiaoPM 按条记录需求（可带上元数据字段）

### 一键安装（Cursor + Codex）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -a codex -g -y
```

### 发给 AI 的安装指令（复制给同事）

```text
请帮我安装 skill 到 Cursor + Codex：
npx skills add 15810879921-coder/oneos-pm-skills --skill AutoRDO -a cursor -a codex -g -y
```

路径：`skills/AutoRDO` · 更新已安装：`npx skills update AutoRDO -g -y`

---

## 一次安装仓库内全部 Skill（Cursor + Codex）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill '*' -a cursor -a codex -g -y
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
│   └── yunxiao-record-requirement-fast-path.mdc  # 产品侧云效唯一入口=YunxiaoPM
└── skills/
    ├── YunxiaoPM/
    ├── yunxiao-development-delivery/
    ├── oneos-autoprd/
    ├── AutoVUL/
    ├── AutoRDO/
    ├── yanchufasui/
    ├── fayanruju/
    ├── mingjingzhishui/
    ├── oneos-wave-router/
    ├── oneos-pm-product/
    ├── oneos-biz-rules/
    ├── oneos-dev-delivery/
    ├── oneos-qa-verify/
    ├── oneos-ux-guide/
    └── oneos-release-gate/
```

---

## 仓库地址

https://github.com/15810879921-coder/oneos-pm-skills

---

## License

MIT
