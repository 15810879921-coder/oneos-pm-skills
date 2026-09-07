# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

**同事安装页（一键复制安装/更新）：** https://15810879921-coder.github.io/oneos-pm-skills/

> **安装范围约定：** 本仓库公开的新装和更新口令默认使用 `-g`，统一安装到当前操作系统用户的全局 Skill 目录，对该用户的所有项目生效，不再提供项目级安装口令。

> **临时客户端维护口径（2026-09-07 起）：** 后续 Skill 只维护 Codex 版本，暂停更新 Cursor 包、manifest 和安装说明；仓库中既有 Cursor 内容仅作为历史产物保留，直到何斐明确恢复。下文既有 Cursor 命令在此期间不作为当前维护或验收要求。

## Skills 列表

| Skill | 说明 | 安装 / 更新 |
|-------|------|----------|
| **`YunxiaoPM`**（推荐 · 口令 YunxiaoPM / 需求任务） | 记录需求 → 分析/设计 → 交棒待开发；压缩点选；迭代只挂交付；**不建【开发】/【测试】** | 见下方「发给产品同事」 |
| **`yunxiao-development-delivery`** | 接收待开发交棒 → 分配开发 → 开始/完成开发 → Bug闭环 → 严格按项目唯一测试主管创建测试任务 | 见下方「云效开发交付」 |
| **`development-brain`**（知行合一） | 云效开发 Skill 的强制知识层：前置预检、执行中约束、通用经验准入与结束复盘 | 见下方「知行合一」 |
| **`YunxiaoQA`** | 接收测试任务 → 执行用例 → 创建/复测缺陷 → 测试完成 → 交接发布 | Codex/Cursor 双版本 |
| **`yunxiao-release-operations`** | 组建发布批次 → 生产发布 → 上线验证 → 自动回滚/重新发布 → 交接产品验收 | Codex/Cursor 双版本 |
| `oneos-autoprd`（展示名 OneOS-AutoPRD） | 整模块 AutoPRD + 标注目录；**需求定稿**写功能变更；云效描述「需求说明/更新内容」 | 见下方 |
| `AutoRDO` | 清洗为标题+描述；自动识别类型/优先级/标签/提交部门/提交人；多行拆多条；有待确认则强制 Plan | 见下方 |
| `AutoVUL` | 按云效迭代名生成 PC 版本更新日志 | 见下方 |
| **`oneos-wave-router`**（任务指路） | 只指路不办事：下一步喊哪个 Skill | 见下方「七 Skill 用途名」 |
| **`oneos-pm-product`**（产品交付） | AI 产品经理一号位（旧花名言出法随已并入） | 见下方「七 Skill 用途名」 |
| **`oneos-biz-rules`**（业务口径） | 规则一号位（旧花名法眼如炬已并入） | 见下方「七 Skill 用途名」 |
| **`oneos-dev-delivery`**（开发落地） | AI 开发经理一号位（旧花名明镜止水已并入） | 见下方「七 Skill 用途名」 |
| **`oneos-qa-verify`**（测试验收） | 测试一号位；云效工具层→YunxiaoQA | 见下方「七 Skill 用途名」 |
| **`oneos-ux-guide`**（体验规范） | 体验一号位；UI/AI 交互原则 | 见下方「七 Skill 用途名」 |
| **`oneos-release-gate`**（上线守闸） | 发布一号位【一期休眠】 | 见下方「七 Skill 用途名」 |
| **`oneos-system-arch`**（系统架构） | 总构官：怎么拆 / ADR / 人机边界 | 见下方新分身 |
| **`oneos-data-metrics`**（数据口径） | 度量官：这个数怎么算 | 见下方新分身 |
| **`oneos-kb-ops`**（知识典藏） | 典藏官：知识库唯一写入 | 见下方新分身 |
| **`oneos-kb-intent-analyst`**（意图分析） | 群聊口语草案，不定版入库 | 见下方新分身 |
| **`oneos-briefing-aide`**（项目汇报） | 讲解官：一线培训 / 方案图解 | 见下方新分身 |

> **已下架：** `yunxiao-requirement-lifecycle`（旧全生命周期 Skill）已从本仓库删除。产品侧云效**只**用 `YunxiaoPM`；`oneos-autoprd` **只**写 PRD/标注/描述，**不**建同名阶段任务。本机若仍有旧包请卸载：  
> `npx skills remove yunxiao-requirement-lifecycle -g -y -a cursor -a codex`  
> **已下架：** `yanchufasui` / `fayanruju` / `mingjingzhishui` 已更名为 `oneos-pm-product` / `oneos-biz-rules` / `oneos-dev-delivery`。本机旧目录请卸载：  
> `npx skills remove yanchufasui fayanruju mingjingzhishui -g -y -a cursor -a codex`

---

## 双端一键安装 / 更新（Cursor + Codex）

统一用 [skills.sh](https://skills.sh) 的 `npx skills`；`-a cursor -a codex` 一次装到两端。

### 双版本发布模型

七套需双端分发的 Skill 使用同一份业务规则源，发布时生成两个独立版本，避免两端业务口径漂移：

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

构建七套双版本离线包：

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

### 旧花名已下架（言出法随 / 法眼如炬 / 明镜止水）

已更名为用途名，不要再装这三个旧目录。本机若还在，先卸：

```bash
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills remove mingjingzhishui -g -y -a cursor -a codex
```

改装：`oneos-pm-product` / `oneos-biz-rules` / `oneos-dev-delivery`。完整知识库与改原型请打开 **oneos-v2**；真仓本机根 `~/oneos-prod`。本机若已把用途名软链到仓内，不要用 `-g` 覆盖。

### 七 Skill 用途名（推荐团队 · 用途名优先）

同事优先喊用途名口令。上线守闸一期休眠。  
**曾装过旧花名：一键脚本会先 `remove` 再装用途名。**

#### 职责与功用

| 用途名 · 称号 | 职责 | 什么时候喊 | 不做 |
|---------------|------|------------|------|
| **任务指路 · 协调官** `oneos-wave-router` | 只指路，不代打 | 不知道该喊谁 | 不改需求/码/云效 |
| **产品交付 · 主理人** `oneos-pm-product` | PRD · 可点原型 · 验收剧本 · 交棒包 | 写需求、出原型、交开发 | 止于交开发；不上线 |
| **业务口径 · 合规官** `oneos-biz-rules` | 能不能做、规则/字段裁决 | 问规则、冲突、查口径 | 不改原型/真码 |
| **开发落地 · 架构师** `oneos-dev-delivery` | 只吃交棒；双轨落地；回执 | 按包改原型/真仓、待测交接 | 无包拒做；不合 Master |
| **测试验收 · 质检官** `oneos-qa-verify` | 测计划 · 证据 · 缺陷 · 打回 | 开始测试、提缺陷、复测 | 不替本尊点发版 |
| **体验规范 · 设计官** `oneos-ux-guide` | UI/AI 交互原则、反 AI 味 | 页面评审、交互争议 | 不定业务能不能做 |
| **上线守闸 · 安全官** `oneos-release-gate` | **一期休眠**；发版权在本尊 | 问发版会被拦回 | 禁止自动推生产 |

主链路：`产品交付 →（业务口径）→ 开发落地 → 测试验收 → 【本尊上线】`

```bash
# 先卸旧花名（没有可忽略报错）
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills remove mingjingzhishui -g -y -a cursor -a codex
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-wave-router -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-pm-product -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-biz-rules -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-dev-delivery -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-qa-verify -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-ux-guide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-data-metrics -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-ops -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-release-gate -a cursor -a codex -g -y
```

更新：

```bash
npx skills update oneos-wave-router oneos-pm-product oneos-biz-rules oneos-dev-delivery oneos-system-arch oneos-qa-verify oneos-ux-guide oneos-data-metrics oneos-kb-ops oneos-kb-intent-analyst oneos-briefing-aide oneos-release-gate -g -y
```

丢进 AI：

```text
请帮我全局安装 OneOS 七 Skill 用途名到 Cursor + Codex：

【七分身职责速览】
- 任务指路：只指路喊谁，不代打
- 产品交付：PRD·原型·交棒；止于交开发
- 业务口径：能不能做；不改码
- 开发落地：只吃交棒双轨落地；止于待测
- 测试验收：证据·缺陷·打回；不点发版
- 体验规范：UI/AI 原则；不定业务口径
- 上线守闸：一期休眠，发版权在本尊

若本机曾装过旧花名 yanchufasui / fayanruju / mingjingzhishui，必须先卸再装（没有可忽略报错）：
npx skills remove yanchufasui -g -y -a cursor -a codex
npx skills remove fayanruju -g -y -a cursor -a codex
npx skills remove mingjingzhishui -g -y -a cursor -a codex

再安装：
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-wave-router -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-pm-product -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-biz-rules -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-dev-delivery -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-qa-verify -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-ux-guide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-data-metrics -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-ops -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-release-gate -a cursor -a codex -g -y

装完请新开 Chat。
用途名：任务指路 / 产品交付 / 业务口径 / 开发落地 / 测试验收 / 体验规范 / 上线守闸（休眠）。
```


### 新分身（2026-09 · 已有旧包时只装这些）

| 用途名 · 称号 | 口令 | 什么时候喊 |
|---------------|------|------------|
| **系统架构 · 总构官** | `/oneos-system-arch` | 怎么拆、ADR、人机边界 |
| **数据口径 · 度量官** | `/oneos-data-metrics` | 这个数怎么算 |
| **知识典藏 · 典藏官** | `/oneos-kb-ops` | 结论入库、库里缺料 |
| **意图分析 · 意图分析师** | `/oneos-kb-intent-analyst` | 群聊语料 / 体微绘画 |
| **项目汇报 · 讲解官** | `/oneos-briefing-aide` | 一线培训 / 产品方案图解 |

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-system-arch -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-data-metrics -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-ops -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-kb-intent-analyst -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill oneos-briefing-aide -a cursor -a codex -g -y
```

装完 **新开 Chat**。

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

v9.7.0 在保留两种开发任务执行模式、真实变更回报和测试交接的基础上，增加自然语言主动识别：用户无需记忆Skill名和标准口令，系统会先唯一定位开发任务或Bug，再路由到已有正式命令；零候选或多候选保持零写入。原有官方 CLI 闭环、开发完成工时审计和优先级继承门禁保持不变：

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

### 用户级全局更新已安装的 Skill

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yunxiao-development-delivery -a cursor -a codex -g -y
```

`YunxiaoQA`现统一从本仓库发布。曾从独立`15810879921-coder/YunxiaoQA`安装的用户，重新执行以下全局命令即可迁移到带主动识别能力的当前版本：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill YunxiaoQA -a cursor -a codex -g -y
```

### 每日首次触发自动更新

安装包含本能力的新版本后，每个本地自然日第一次触发 `YunxiaoPM`、`yunxiao-development-delivery`、`development-brain`、`YunxiaoQA` 或 `yunxiao-release-operations` 中的任意一个，都会先统一更新这五个用户级全局 Skill；当天后续触发直接复用成功状态，不重复联网。更新失败会进入 30 分钟冷却并继续当前工作，不修改项目级 Skill、业务仓、云效数据、流水线或生产环境。

旧版本无法自行获得更新器，因此需要先手工全局安装或更新一次带本能力的新版本；此后才进入每日自动更新。

---

## development-brain · 知行合一

全局主动开发知识层：即使没有输入固定口令，只要自然语言或当前工作区表明正在开始、继续或完成真实开发，它就会在首次写入前自动预检，并在代码与测试/MR 证据闭环后自动复盘。新模式第一次只进入候选；由第二个独立开发任务再次验证并通过安全门槛后，才可自动转为正式规则。破坏性、扩权、生产发布、强推和敏感凭据类规则始终需要何斐确认。

### 全局安装到 Cursor + Codex

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill development-brain -a cursor -a codex -g -y
```

### 更新已安装的 Skill（重新执行全局安装，确保 Cursor + Codex 同步）

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill development-brain -a cursor -a codex -g -y
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
    ├── development-brain/
    ├── oneos-autoprd/
    ├── AutoVUL/
    ├── AutoRDO/
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
