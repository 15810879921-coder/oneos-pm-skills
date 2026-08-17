# Gemini 交棒 · OneOS 七 Skill 现代职场定妆重绘

> **本尊 2026-08-16** · 人设圣经：[`skill-persona-bible.md`](skill-persona-bible.md)  
> **风格红线**：**彻底摒弃武侠、仙侠、古风法袍与神话铠甲**！全部采用**现代高级职场装束**（Modern Corporate / High-Tech Workplace Attire），根据岗位与性格定制专属职场服饰、道具与办公场景。  
> **性别**：女×6（主理人/合规官/架构师/质检官/设计官/协调官）+ 男×1（安全官）。  
> **版式参考图（上传）**：`src/prototypes/oneos-project-war-room/assets/avatar-style-reference-family-ssr.png`  
> （只学金框/SSR/竖幅/底盒版式；**人物、服装与文案以本包为准**）

---

## 0. 总指令（每次会话先贴）

```text
Generate ONE premium SSR gacha character card per request, 1024×1024 PNG.

Match ONLY the FRAME LANGUAGE of the attached reference (ornate gold filigree border, SSR + 6 gold stars top-left, left vertical dark-blue Chinese banner, bottom dark-blue gold text panel, bottom-left pill “虚拟形象 · 定妆”).

STYLE DIRECTIVE: Modern high-tech corporate / workplace setting. No ancient Chinese wuxia/xianxia robes, no fantasy armor, no magic spells. Characters must wear modern tailored business suits, tech-workplace uniforms, or stylish high-end office attire.

Semi-realistic cinematic modern anime / premium gacha CGI, crisp lighting, high-end office / tech lab background, glowing holographic data displays.
Burn EXACT Chinese strings provided — no paraphrase, no translation.
No watermark, no extra English UI except the SSR badge.
```

---

## 1. 导出文件名

| Skill | 文件名 | 覆盖旧资产 |
|-------|--------|------------|
| 产品交付 | `yanchufasui-avatar.png` 与 `oneos-pm-product-avatar.png` | 是 |
| 业务口径 | `fayanruju-avatar.png` + `oneos-biz-rules-avatar.png` | 是 |
| 开发落地 | `mingjingzhishui-avatar.png` + `oneos-dev-delivery-avatar.png` | 是 |
| 测试验收 | `oneos-qa-verify-avatar.png` | 新 |
| 体验规范 | `oneos-ux-guide-avatar.png` | 新 |
| 任务指路 | `oneos-wave-router-avatar.png` | 新 |
| 上线守闸 | `oneos-release-gate-avatar.png` | 新 |

落仓：`src/prototypes/oneos-project-war-room/assets/`

---

## 2. 七卡 Prompt（每次只生成一张）

### 2.1 产品交付 · 主理人（女）

**Exact text**
- Banner: `产品交付 · 主理人`
- Title: `【交付主理 · 一锤定音】`
- L1: `谁要做什么 → 故事·原型·交棒一条龙；止于交开发`
- L2: `磨叽盘问禁连环 · 歧义只问一题 · 拍板后直接干`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern corporate tech aesthetic. East-Asian woman ~28, confident and commanding C-suite / Lead Product Manager aura, elegant dark hair with soft waves, wearing a tailored luxury deep-violet business suit with satin lapels and delicate gold brooch. Holding a glowing ultra-thin glass tablet showing agile product Kanban boards and user story flows. Background of a high-rise executive corner office with panoramic floor-to-ceiling glass windows overlooking a modern skyline at dusk. Layout per reference frame rules. Exact Chinese strings. No fantasy robes, purely modern workplace.
```

### 2.2 业务口径 · 合规官（女）

**Exact text**
- Banner: `业务口径 · 合规官`
- Title: `【口径合规 · 零臆断】`
- L1: `能不能做只看依据；不明白就停，禁止「我觉得」`
- L2: `答复包：结论·依据·置信度·交棒码 · 不改码`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern corporate tech aesthetic. East-Asian woman ~30, sharp intellectual eyes behind slim gold/titanium rectangular glasses, sleek shoulder-length hair. Wearing a formal tailored navy-blue bespoke blazer, crisp white collar shirt, holding a luminous holographic data analysis cube with business logic rules and audit charts. Background is a modern high-tech fintech compliance and risk-control operations center with cool cyan ambient lighting. Layout per reference frame rules. Exact Chinese strings. No fantasy robes, purely modern workplace.
```

### 2.3 开发落地 · 架构师（女）

**Exact text**
- Banner: `开发落地 · 架构师`
- Title: `【落地架构 · 无包拒做】`
- L1: `只吃交棒包；双轨可点→可跑；止于待测`
- L2: `缺项列清单 · 偏差就停 · 回执写清楚`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern tech workplace aesthetic. East-Asian woman ~26, calm and dependable senior software architect, neat medium-length hair, wearing a stylish minimalist light-grey tech blazer over a fine-knit turtleneck, professional over-ear headset around neck and tech ID badge. Holding a transparent foldable dual-screen laptop showing Git branch tree diagrams and deployment checklist receipts. Floating subtle cyan binary code nodes '01'. Background is a bright modern Silicon Valley style open-plan engineering workshop. IMPORTANT: Adult woman, NOT a child. Layout per reference frame rules. Exact Chinese strings.
```

### 2.4 测试验收 · 质检官（女）

**Exact text**
- Banner: `测试验收 · 质检官`
- Title: `【找茬王牌 · 证据门神】`
- L1: `无证据不得通关；阻断未清禁止喊「可上线」`
- L2: `打回必带波次 ID · 复测通过率拉满 · 假绿秒破防`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern tech workplace aesthetic. East-Asian woman mid-20s, sharp detective-like QA lead, stylish half-up dark hair, wearing a British-tailored dark emerald-green office vest and blazer suit with subtle gold chain pin. Holding a digital stylus pen and a glowing inspection checklist with green checkmarks and one bold red 'FAIL' stamp. Background is a modern software quality testing operations center with multi-monitor test metrics. Layout per reference frame rules. Exact Chinese strings.
```

### 2.5 体验规范 · 设计官（女）

**Exact text**
- Banner: `体验规范 · 设计官`
- Title: `【颜值立法 · 反AI味】`
- L1: `禁说明书墙与假紫渐变；首屏一眼主任务`
- L2: `AI 四级信任写进界面 · Pattern 不页页发明`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern luxury design studio aesthetic. Elegant East-Asian woman as Head of Design / UX Director, sophisticated updo hairstyle, wearing a champagne-gold and soft blush pink luxury silk blouse with tailored wide-leg trousers. Holding a glowing golden-ratio spiral ring and an ultra-clean minimalist UI wireframe hologram, surrounded by floating design tokens and color swatches. Background of a spacious high-end architectural design atelier. Layout per reference frame rules. Exact Chinese strings.
```

### 2.6 任务指路 · 协调官（女）

**Exact text**
- Banner: `任务指路 · 协调官`
- Title: `【全家导航 · 只指路】`
- L1: `「谁要做什么」一秒分流；自己不改码不办事`
- L2: `指错人算暴击失败 · 路由命中率 +999%`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern tech campus aesthetic. Energetic and cheerful young East-Asian woman agile coordinator / operations lead, high ponytail, wearing a pastel sky-blue casual blazer over a white tee, lightweight single-ear wireless headset. Holding a smart digital dispatching tablet, pointing brightly towards floating modern UI department navigation signs: 产品交付 / 业务口径 / 开发落地 / 测试验收. Background of a sunlit modern tech campus glass atrium with subtle cyan particle sparkles. Layout per reference frame rules. Exact Chinese strings.
```

### 2.7 上线守闸 · 安全官（男 · 休眠）

**Exact text**
- Banner: `上线守闸 · 安全官`
- Title: `【上线休眠 · 本尊钥匙】`
- L1: `一期封印自动发版；误唤只递自检清单`
- L2: `唤醒须本尊口令 · 合 Master 禁自动`
- Pill: `虚拟形象 · 定妆`

**Art prompt**
```text
SSR card 1024x1024. Modern high-security server vault aesthetic. Imposing and solemn East-Asian adult male Head of Security & Release, broad shoulders, wearing a tailored charcoal-black heavy wool overcoat and bespoke 3-piece business suit. Standing with arms crossed, eyes calmly closed in meditative rest, in front of a colossal titanium high-tech server vault door locked by electronic orange neon warning seals reading '休眠'. Background is a dark ultra-secure data center with subtle amber status lights. Quiet dormant authority. Male only. Layout per reference frame rules. Exact Chinese strings.
```

---

## 3. 验收勾选

```text
□ 七张皆 1024×1024，版式元素齐全
□ 中文与表内一字不差
□ 纯现代职场西装与科技工装；彻底无古风/法袍/神话铠甲
□ 性别：前六女、安全官男
□ 文件名按 §1；回传分身接线并更新作战室
```

---

## 3. 验收勾选

```text
□ 七张皆 1024×1024，版式元素齐全
□ 中文与表内一字不差
□ 无旧母亲/父亲/幼子脸；镜心为成年女性
□ 性别：前六女、门神男
□ 文件名按 §1；可先单张回传分身接线
```
