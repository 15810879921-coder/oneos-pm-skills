# 开发大脑知识索引

索引版本：`1`

- `confirmed_sha256`: `b706d901f99f9e4df003eb74d981e07bf97cd554efb9e31584bc9fdca2e8a176`
- `candidate_sha256`: `b5b9a81a4afc2dff9620c534135c017eb7a07a7da6c13b023447368d125bb37f`

本文件只用于快速路由。规则是否强制、完整边界和证据以源记录为准；命中后必须通过 `scripts/select-knowledge.mjs` 读取完整原文。修改任一知识源时，必须同步更新本索引及对应 SHA-256，并通过 `--check`。

| ID | 状态 | 范围标签 | 命中线索 | 路由摘要 | 源文件 |
| --- | --- | --- | --- | --- | --- |
| DB-C-001 | confirmed | yunxiao-development-delivery | 云效开发交付、代码写入、外部系统写入、预检 | 交付动作写入前必须完成开发大脑预检 | confirmed-constraints.md |
| DB-C-002 | confirmed | knowledge-governance | candidate、pending、未确认经验、强制规则 | 未确认经验不能作为写入强制依据 | confirmed-constraints.md |
| DB-C-003 | confirmed | development-lifecycle | 实现、修改、修复、重构、构建、测试、提交、MR | 真实开发写前预检、完成后证据化复盘 | confirmed-constraints.md |
| DB-C-004 | confirmed | skill-development | SKILL.md、Skill 脚本、校验器、打包、development-brain 自身治理 | Skill 开发知识隔离及大脑自改人工确认 | confirmed-constraints.md |
| DB-C-005 | confirmed | java-spring-http-write | Java、Spring MVC、RuoYi、Controller、HTTP 写接口、创建、更新、删除、RepeatSubmit、资金、结算 | 外部同步写接口按风险采用重复提交或业务幂等 | confirmed-constraints.md |
| DB-C-006 | confirmed | unattended-alibaba-cloud-auth | 无人值守、Windows 服务、计划任务、CI Agent、阿里云 CLI、OAuth、AccessKey、RAM 角色、凭据存储、GetCallerIdentity | 无人值守云认证优先工作负载身份，受控使用最小权限 RAM AccessKey | confirmed-constraints.md |
| DB-C-007 | confirmed | skill-client-distribution | Skill、Cursor、Codex、双端、打包、安装、更新、manifest、发布 | 临时只维护 Codex，Cursor 历史产物保留但不更新 | confirmed-constraints.md |
| DB-C-008 | confirmed | skill-github-https-proxy | Skill、GitHub、HTTPS、代理、合并、提交、clone、fetch、pull、push、ls-remote、连接重置 | 已授权代理环境的 Skill GitHub 网络命令显式走代理，同步后合并并推送读回 | confirmed-constraints.md |
| DB-R-001 | candidate | browser-frontend-security | 浏览器、前端构建变量、运行时配置、密钥、令牌、加密初始化 | 浏览器可读配置不得承载认证材料 | retrospective-candidates.md |
| DB-R-002 | candidate | local-automation-lock | 本地自动化、文件锁、运行 token、外层调度、内层总控、重复 finish | 同一运行只获取一次不可重入互斥锁 | retrospective-candidates.md |

## 读取规则

1. 用任务事实匹配“范围标签”和“命中线索”，不得只按单个泛化词命中。
2. `confirmed` 命中后读取完整记录，只有完整记录可进入执行中约束。
3. `candidate` 仅用于相同/近似排除，不得作为强制规则。
4. 无命中时回执写“无匹配 confirmed 规则”；不加载完整知识文件。
5. 范围不明、多个摘要可能冲突或索引校验失败时，回退完整读取。
