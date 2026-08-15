# 安装 / 更新 明镜止水（mingjingzhishui）

## 同事一键（npx skills · 与言出法随同通道）

安装页：https://15810879921-coder.github.io/oneos-pm-skills/

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

建议与言出法随 / 法眼一起装（三 skill）：

```bash
npx skills add 15810879921-coder/oneos-pm-skills --skill yanchufasui -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill fayanruju -a cursor -a codex -g -y
npx skills add 15810879921-coder/oneos-pm-skills --skill mingjingzhishui -a cursor -a codex -g -y
```

更新：

```bash
npx skills update mingjingzhishui -g -y
# 或三件套：
npx skills update yanchufasui fayanruju mingjingzhishui -g -y
```

装完 **新开 Chat**。真仓本机根与完整联调文档仍在本机 `~/oneos-prod`；改原型请打开 **oneos-v2**。

**本尊机**继续用仓内软链，不要用 `-g` 覆盖 `~/.cursor/skills/mingjingzhishui`。

## 正式单源（oneos-v2）

1. 打开 / 拉取 **oneos-v2**（Skill 正文：`.cursor/skills/mingjingzhishui/`）
2. 配对产品分身：同仓 `.cursor/skills/yanchufasui/`（交棒出口 `handoff-to-dev.md`）
3. 真仓本机根：`/Users/sylvawong/oneos-prod`（`docs/repo-map.md` · `docs/runtime.md`）
4. **新开对话**，口令 `明镜止水` / `$mingjingzhishui`
5. 工作区更新 = `git pull` → 再新开对话。禁止发 zip / rsync 整包

> **改码默认不常驻**：不要做成与言出法随同级的全局 Always「改真码」规则，避免双分身抢落地。  
> **技术顾问旁路（v1.0.5）**：工程阻塞时言出法随须代挂「明镜建议」；本尊无需每次喊 `/明镜止水`。

发布到同事安装页：把本目录同步进 `oneos-pm-skills/skills/mingjingzhishui/` 后 push。

## 本尊机 · 软链（强制偏好）

```bash
ln -sfn /Users/sylvawong/oneos-v2/.cursor/skills/mingjingzhishui \
  ~/.cursor/skills/mingjingzhishui
```

可选 Codex 菜单：

```bash
ln -sfn /Users/sylvawong/oneos-v2/.cursor/skills/mingjingzhishui \
  ~/.codex/skills/mingjingzhishui
```

- ✅ 仓内单源 + 软链  
- ❌ 不要在 `~/.cursor/skills/mingjingzhishui` 维护第二份实体拷贝  

装完 **新开 Chat**。

## 瘦启动冒烟

1. 新开 Chat → 喊「明镜止水」→ 应只读 `boot.md`  
2. 签名「王冕驱动 · 明镜止水」  
3. 无交棒包时拒做并列缺项  
4. 完整交棒 + `A_then_B` → 声明本轮只做轨 A  

## 与友邻

| Skill | 关系 |
|-------|------|
| yanchufasui | 上游交棒 |
| fayanruju | 口径升档 |
| YunxiaoPM / yunxiao-development-delivery | 云效树；明镜默认本机模拟 |
