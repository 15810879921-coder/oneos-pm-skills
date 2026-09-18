# 原生执行检查

执行检查命令用 Python 3.11+ 运行 `scripts/execution_gate.py`。`describe` 返回当前评估模板；`assess --thread-id ID --turn-id ID --json JSON` 评估本阶段并落盘；`status` 读取岗位记录和实际模型回执；`retry` 只允许原生明确派工失败后重试一次。评估时 available_roles 必须来自当前 spawn 工具角色；磁盘配置只是交叉核验。

## 岗位检查

`assess` 在原模型字段以外接受 `prompt`、`job_roles`、`job_role_skills` 和 `job_role_exclusions`。岗位使用 `product`、`ux`、`development`、`qa`；具体触发、作用域和交接内容见 [岗位自动介入协议](job-role-protocol.md)。

- 原生 `UserPromptSubmit` 的用户提示用于推断所需岗位；CLI 模式由主任务补充当前用户任务，来源分别标注。用户引用或讨论四岗位规则，不等于当轮已经进入四个业务阶段。
- `job_roles` 指定当前实际执行的岗位；后续阶段仍保留在所需岗位中。推断误判时，使用 `job_role_exclusions` 对被排除岗位写明具体原因，不通过空名单静默取消要求。
- `job_role_skills` 用于明确项目对应技能；当前目录只提供候选。全局或跨项目任务、当前目录与实际目标不同的任务，主助手必须按目标主动填写该映射，不依赖目录自动推荐，不把目录名当作业务授权；用户无需手填。
- `role-read --thread-id ID --turn-id ID --role ROLE [--skill NAME]` 输出技能正文和读取标记。随后 `status` 或受覆盖工具检查对应的真实调用与成功输出；仅运行一次命令或声称读过不算成功。
- `role-status` 查看岗位记录；`role-confirm` 仅用于主动核对读取证据，不是额外的用户确认步骤。
- `role-result --thread-id ID --turn-id ID --json JSON` 记录 `role`、具体 `summary` 及非空 `evidence`。证据是实际文件，或能定位真实调用的任务记录。
- `role-handoff --thread-id ID --turn-id ID --json JSON` 记录 `role`、`disposition`、`boundary`、`artifacts`、`unresolved`、`acceptance`；交下个岗位时增加 `next_role`，本阶段收口则使用 `disposition: closed`。

读过技能、结果已记录、交接已完成分别显示。读取标记并不证明结果质量，主任务仍须验收实际产物；不存在的文件、缺少回执或尚未执行的验证不能写成通过。

## 模型派工与覆盖

门禁挂载 UserPromptSubmit、PreToolUse、PostToolUse、Stop。PreToolUse 覆盖 Bash（包括代码模式嵌套的 exec_command）、apply_patch、Agent/spawn_agent 及 mcp__ 工具名。外层 functions.exec、托管 WebSearch、已有终端 write_stdin 和其他未覆盖工具没有完整拦截保证。这是工作流防护，不是安全隔离边界，也不保证模型对任务复杂度判断永远正确。

没有本轮评估时拒绝受覆盖工具；describe/assess/status/retry 的单条本地命令是启动通道。应委派时核验固定角色、精简上下文和唯一 task_name。PreToolUse 记录原生 tool_use_id；PostToolUse 必须回传相同调用的 agent_id/task_name，再根据原生子任务上下文核对 parent_thread_id、创建时间、model、effort。只有配置或只有 attempted 都不算实际模型回执。缺失 transcript、身份不明、未知结果均保持阻塞；不会猜测为成功。子任务身份由原生 transcript 的 session_meta 分开识别，不能用共享 session_id 一概继承父任务状态。该读取依赖非稳定 JSONL 格式，宿主升级须再验收。

多个独立阶段使用不同 phase，保留先前回执；新阶段仍需 parent_work。已知原生启动失败可 retry 一次，未知结果不可重试。微小直做最多两次被覆盖工具调用；不要包装成大脚本规避。任务的所有权和复杂度由协调者判断，门禁无法证明任意 shell 的语义边界。

Stop 保存审计，提示缺少派工回执或岗位读取、结果及交接记录，不返回 decision:block，不额外启动收费轮次。不含完整对照运行时 token_savings 仍为 unknown。

钩子尚未激活时，CLI 可从父任务的真实 spawn 调用、原生启动事件和相同调用的返回值恢复派工，再核对子任务的父线程、模型与强度。该证据明确标为 `transcript_recovered_manual_cli`；不会补造原生 hook_events，也不把它称为钩子已生效。

激活验收必须同时有：安装文件一致；hooks/list 显示新四项 enabled 且 trustStatus=trusted；真实任务经过 PreToolUse；原生 PostToolUse 与子任务日志对上；最终产物验收。单元测试模拟 payload、CLI 手动评估、hook_payload_received 都不能代替整条原生触发验收。

官方协议：https://learn.chatgpt.com/zh-Hans/docs/hooks 。新增定义或定义变更后需在 Codex 原生 hooks 界面确认信任。安装器不写信任哈希、不修改管理来源、不绕过安全设置。
