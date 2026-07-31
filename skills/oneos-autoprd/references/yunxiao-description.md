# 云效需求描述：产品说明（对接 YunxiaoPM）

发云效 / 完善需求描述时，与 **`$YunxiaoPM`** 双段模板对齐。
旧包 lifecycle **已下架**勿加载。

## 需求描述固定结构（不可互相覆盖）

```markdown
## 原始诉求（AutoRDO）
（由 AutoRDO 清洗；设计完成也不删除；本 Skill 不覆盖本段）

## 产品说明（AutoPRD）
（本 Skill 写入：原型链接 + requirements-prd 正文或等价产品说明）

## 工作项编号（系统）
（由 YunxiaoPM 维护；本 Skill 不改本段）
```

## 产品说明段推荐拼装

```markdown
## 产品说明（AutoPRD）

### 原型链接
<{baseUrl}/{prototype-id}/index.html；禁止加 prototypes/ 前缀；禁止去掉 index.html>
无则写「待发布」

### 需求说明
<src/prototypes/<id>/.spec/requirements-prd.md 全文原样粘贴；禁止摘要顶替>

### 更新内容
<第 10 章最新定稿块；无则「首版定稿」或「本轮无功能/逻辑增量」>

### 更新内容·历史
<旧更新内容倒序；勿删>
```

若 YunxiaoPM 本轮只要求「产品说明」短写：至少包含原型链接 + MD 全文或与交付回填一致的正文；**仍禁止**覆盖 AutoRDO / 工作项编号段。

## 真相源文件

1. `src/prototypes/<prototype-id>/.spec/requirements-prd.md`（主）
2. 否则 `src/resources/prd/<prototype-id>-autoprd.md`

先 Read 文件再写入；不要凭记忆重写。

## 执行步骤

1. 确认 prototype-id 与需求编号（若写云效）。
2. 读 MD 全文。
3. PATCH/更新需求描述时**只改**「产品说明（AutoPRD）」相关内容；保留原始诉求与工作项编号。
4. 若同时设计完成：按 [yunxiao-delivery-sync.md](yunxiao-delivery-sync.md) 回填【交付】。
5. 回报：需求编号、MD 路径、是否全文写入、是否已回填交付编号。

## 禁止

- 只用第 9 章摘要顶替全文（除非用户只要链接）
- 二次删减章节、去掉 mermaid/表格却声称全文已写
- 创建【交付】时灌入 PRD（须等设计完成；见交付回填）
- 引用或配合已下架的 lifecycle Skill
