# 需求描述 vs 交付描述

两类描述职责不同；禁止混写；禁止建【交付】时把 AutoPRD 六大块提前塞进交付描述。

## A. 需求描述 · AutoRDO 清洗

| 项 | 规则 |
|---|---|
| 触发 | 对话建需求 / 碎片材料入库 |
| 调用 | **必须**使用独立 Skill「**`$AutoRDO`**」（`AutoRDO/SKILL.md`；本 Skill 不内嵌清洗细则） |
| 输入 | 聊天记录、录音、口述材料 |
| 处理 | 保留原意；书面化；去口头禅；**去除结尾句号**（细则在 AutoRDO `references/rules.md`） |
| 输出 | 写入 `## 原始诉求（AutoRDO）` |
| 不做 | 本阶段不写 AutoPRD 六大块；不要求已有原型；不覆盖已有「产品说明」 |

口令：`AutoRDO：…` → 确认后 `记录需求：【新增】标题；描述=整理稿；推进至=…`

## B. 交付描述 · 设计完成前占位

| 时机 | 【交付】描述 |
|---|---|
| 首次创建起至设计完成前 | 固定文案：`等待设计任务完成后自动填入` |
| 设计完成时 | 用 AutoPRD「产品说明」正文替换占位 |

## C. 需求描述双段模板（不可互相覆盖）

```markdown
## 原始诉求（AutoRDO）
（清洗稿；设计完成也不删除）

## 产品说明（AutoPRD）
（六大块+对象存储链接；未设计完成前可无此节或写「待设计完成后填入」）

## 工作项编号（系统）
- 交付：…
- 分析：…
- 设计：…
```

## D. 设计完成 · AutoPRD + 附件

前提：设计任务完成且已关联对应原型页。

1. 调用 **`$oneos-autoprd`（AutoPRD）**，产出并落盘 `.spec/requirements-prd.md` + 标注同步：
   - 对象存储预览链接：`{baseUrl}/{prototype-id}/index.html`（禁止加 `prototypes/` 前缀、禁止去掉 `index.html`）
   - 产品说明 Markdown（总览/角色/流程/状态/风险/交付等，见 AutoPRD 模板）
2. 写入需求 `## 产品说明（AutoPRD）`；**禁止覆盖** `## 原始诉求（AutoRDO）` / `## 工作项编号（系统）`。
3. 【交付】描述：按**交付任务编号**用产品说明正文**替换**占位（细则见 AutoPRD `references/yunxiao-delivery-sync.md`）；可附「原始诉求见需求描述」。**创建【交付】时不得提前灌 MD。**
4. 附件（需求 +【交付】均挂；失败则不得声称成功）：
   - Make「导出 HTML（含源码）」ZIP → [make-export-attach.md](make-export-attach.md)
   - Make「复制截图」全交互页 → 同上

缺原型 / AutoPRD 失败 / 导出或截图失败 → **不得**报到设计完成并宣称附件齐全；停下并列出缺项。

执行顺序：先 AutoPRD 落盘与附件就绪 → 再改需求/交付描述与设计计划完成 → 最后改需求状态。

**禁止**加载 `yunxiao-requirement-lifecycle`；阶段任务树只由本 Skill（YunxiaoPMapp）创建。
