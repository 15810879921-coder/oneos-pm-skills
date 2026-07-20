# OneOS PM Skills

OneOS 产品团队自用的 AI Agent Skills 合集，支持 `npx skills` 一键安装（[skills.sh](https://skills.sh) 生态）。

## Skills 列表

| Skill | 说明 | 安装 |
|-------|------|------|
| `version-update-log-format` | OneOS PC 版本更新日志：新功能/Bug修复分类、同模块合并、责任部门自然表述 | 见下方 |

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

### 查看仓库内所有 Skill

```bash
npx skills add 15810879921-coder/oneos-pm-skills --list
```

---

## 仓库结构

```text
oneos-pm-skills/
├── README.md
└── skills/
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
