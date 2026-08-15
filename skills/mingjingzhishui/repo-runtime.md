# 明镜止水 · 真仓运行指针（repo-runtime）

> **升档才读**：轨指令含 B、准备进 `oneos-prod`、选仓/起服时。  
> **禁止**把数据库口令、生产密钥抄进本文件或 Skill 正文。

## 0. 根路径（钉死）

```text
/Users/sylvawong/oneos-prod
```

权威地图与运行说明（本机私有，不进 oneos-v2 公开原型）：

| 文档 | 用途 |
|------|------|
| `/Users/sylvawong/oneos-prod/docs/repo-map.md` | 子仓职责、分支、端口、核心 vs 备查 |
| `/Users/sylvawong/oneos-prod/docs/runtime.md` | 本机起服、登录、通关证据 |
| `/Users/sylvawong/oneos-prod/docs/nacos-local/` | 本地 Nacos 配置源（只读参照） |
| `/Users/sylvawong/oneos-prod/local-config/` | 本地覆盖配置 |

进轨 B 时：**先 Read 上述两份 docs**，再动代码。若存在可再读：

| 可选 | 用途 |
|---|---|
| `docs/v1-architecture.md` | V1 请求链 / 定表工作法 §8.1 |
| `docs/pre-dev-checklist.md` | 开发前绿红黄（过期以现场为准） |

文档与现场不一致 → 以现场+本尊裁决为准，并回执写偏差。  
**禁止**把 `oneos-v2` 原型当作 V1 表结构。

## 1. 默认核心三件套

| 目录 | 角色 | 默认分支 |
|------|------|----------|
| `ln-cloud` | 网关/认证/系统等 | `dev` |
| `ln-asset-management` | 业务后端 | `dev`（本地须 `dev` profile，勿用默认 `lz` 乱注册） |
| `ln-one-os-web` | 前端 Vben | `develop` |

常用端口（以 `runtime.md` 为准）：Nacos 8848 · Gateway 8080 · Web 5666 · Asset 8701 …

## 2. 非核心仓

`ln-ocr` / `ln-energy-v2` / `ln-xiaolingling` / `oneos_asset_management_mini` / `ln-weixin-ai-helper` 等：

- 交棒「真仓锚点」未点名 → **不动**  
- 需要时先问本尊  

**禁默认整套 V2 Git。** 同仓演进是默认；单域新仓（换库+换网关前缀+旧服并存）须本尊/交棒点名，对齐 `ln-energy-v2`，禁止八仓翻倍。  

## 3. 起服与验收（摘要）

- 优先按 `runtime.md`：`tmux attach -t oneos-core` 或仓库内启动脚本  
- 登录走前端（RSA 加密）；裸 curl 易 403  
- B 轨最低通关（本机）：`/auth/login` 成功 + `getInfo` + `getRouters`（经网关）；再叠加交棒正/逆/门禁  
- **可勾表**：明镜 habits **§3.2**（v1.0.10）；视觉对表另见 habits §2.2  
- 通关至少：登录成功 + 交棒正路径可点；逆路径/门禁按交棒演示  

## 3b. VPN / 网关直连硬闸（2026-08-15 实战）

开了 VPN/TUN（常见 `198.18.x`）时：服务若按局域网 IP 注册进 Nacos，网关 `lb://ruoyi-auth` 会打到不可达地址 → **Connection reset** → 前端「内部服务器错误」。

| 做法 | 规则 |
|------|------|
| **推荐** | 本机 `docs/nacos-local/ruoyi-gateway.yml`：auth/system/resource/asset 用 `http://127.0.0.1:端口` 直连（见 runtime.md） |
| **禁止** | 钉 `spring.cloud.nacos.discovery.ip=127.0.0.1` 或 `dubbo.protocol.host=127.0.0.1` 当「万能修复」——会污染 Dubbo `DUBBO_IP_TO_REGISTRY`，auth/system **起不来** |
| **排查顺序** | 先看 gateway 日志上游 IP / Connection reset → 再查主题 CSS；禁先怪 Token 刀 |

细节与重启命令以 `~/oneos-prod/docs/runtime.md` 为准。

## 4. 安全

- Skill / 回执 / 作战室 **禁止**粘贴生产口令  
- 本机 MySQL/Redis 口令只存在本机 docs；对话里用「见 runtime.md」代替回显  
- **禁止对产线 MySQL 写**（含 DDL）。只读：`scripts/prod-ro-probe.sh`；灌本机用 `--no-data` 脚本。  
- 氢/能定表：跟前端 URL 前缀（`/asset` → asset 库；`/energy-v2` → `ln_energy_v2`；`/energy` 无 v2 → 现役 ln-energy，未点名不克隆）。禁止预判改哪库。  

## 5. 多微服务路由 × 复杂逆路径仿真（evo-mj-repo-sim）

覆盖链：**lease**（`/asset/**`→asset:8701）· **vehicle**（同）· **audit**（`/workflow/**` `/warm-flow**`→workflow:9205）。

```bash
python3 ~/oneos-prod/scripts/repo-sim-multi-ms.py
# 报告：docs/external-facts/repo-sim-lease-audit-vehicle.md
```

| 验什么 | 绿 | 诚实红/缺口 |
|---|---|---|
| 网关 Path 挂载 | asset/workflow 有；`/lease` `/energy-v2` 本机无 | 产线 energy-v2 另核 |
| 无 Token | body `code=401` / msg 含 token | 网关抖 502 → 重试用 curl |
| workflow 未起 | :9205 DOWN 可演示逆路径 | 不装「审核链已闭环」 |
| MySQL | 本机计数 + 产线 dump 表名；RO ping | 2013 → 只用 dump，禁脑补列 |
| 表名 | `vehicle_lease_contract_info` | 禁原型名 `contract_info` |

**禁止**：仿真绿 = 业务正路径已可点。本机 `ln_asset_management` 几乎空时，有 Token 后业务 500 → **标缺口不装闭环**。

返回：[`habits.md`](habits.md) · [`boot.md`](boot.md)
