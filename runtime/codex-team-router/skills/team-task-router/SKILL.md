---
name: team-task-router
description: Use before task tool work to select required product, UX, development, and QA roles as well as execution models; verify real role participation, results, handoffs, and dispatch receipts.
---

# Team Task Router 2.2.0

## 岗位先行

用户要求相关岗位自动介入，无需逐次点名。先按本任务的意图和当前阶段匹配岗位，再选择执行模型：需求类 → 产品交付；页面设计、界面和交互改动 → 体验规范；代码修改、代码排查、本机环境调试 → 开发落地；测试、回归、复测和验收验证 → 测试验收。完整口径见 [岗位自动介入协议](references/job-role-protocol.md)。

岗位必须实际成功读取对应技能，并留下具体结果及必要的交接记录；模型路由成功不等于岗位已经介入。项目同类技能优先，通用任务只用岗位方法，不跨项目引入 OneOS 业务规则。主助手可承担岗位；子代理也须按分配范围读取岗位技能，但不递归派工。

当前目录只提供技能候选。遇到全局配置、跨项目工作或目标与目录不一致，主助手必须按实际目标主动填写 `job_role_skills`，通用工作选默认岗位的通用方法；不要要求用户手动选择岗位。

混合任务按阶段覆盖岗位；只分析、不改代码、不执行测试等用户边界仍有效。岗位要求不新增重复审批，不为凑岗位数量生成多余代理，也不把普通文档/Excel 操作因用了命令行就算成开发。

以下模型路由规则继续执行。岗位、模型、结果及交接分别记录，未知状态不提升。

用户选择 Astra 时，由当前 Astra 统筹、拆解、处理独立判断并验收。选择 Astra/max 作为主模型不等于要求所有执行都用 Astra。每个使用工具的任务在主要执行前评估并落实分工；已经明确的普通执行优先交 Luna，常规判断交 Terra，复杂或高风险交 Sol。短答无需工具时直接回复，不为了统计或演示额外调用模型。

先按现有上下文确定目标、范围与约束；需要读取具体业务材料才能判断时，将必要的只读诊断作为一个小阶段。不要先把整项工作做完才补路由。不得把业务实现、批量改动、测试执行、资料整理笼统标为 coordination 或 tiny 来绕过分工。

## 当前主任务

1. 有原生执行门禁时，使用 Python 3.11+ 调用本技能 `scripts/execution_gate.py describe`，随后 `assess --thread-id <当前线程> --turn-id <当前轮次> --json '<评估 JSON>'`。这会真实调用 router.py 并记录决策。门禁未受信任时仍主动遵循同一分工规则；安装文件不等于原生门禁已激活。原生门禁只覆盖 [execution-gate.md](references/execution-gate.md) 所列工具路径。
2. 按当前工具实际暴露的角色填写 available_roles；不要把磁盘上的配置当运行时可用性证明。填写独立子任务的边界和验收，以及主任务同时能完成的真实 parent_work。主任务先拆出确定的执行，不得把分工限制当做回退 Astra 的通用理由；没有真实独立工作时保持阻塞并解释原因，禁止虚构并行工作或违反宿主条件。
3. 返回 delegate 后必须实际调用 `spawn_agent`，使用返回的角色及 task_name，显式 `fork_turns="none"`，不设置 model/effort 覆盖固定角色。只传目标、负责文件、约束、验收和必需证据；说明共享工作区，保留他人改动，禁止递归派工。不要复制全历史。
4. `status` 核对原生回执，期望模型与实际模型分开。派工成功但回执尚未就绪时核对原调用，不重复创建代理；只有原生明确启动失败，才允许通过 `retry` 重试一次。仍未知或连续两次失败则报告证据。需要第二个独立阶段时使用新的 phase，保留前一阶段回执。
5. 主任务同时完成 parent_work，再验收子任务的实际文件、结果与相应测试。角色被调用不等于产物合格。交付简短列明实际使用的模型及工作；若应派未派，明确说明，不能报“路由已生效”。

## 选型与例外

| 工作 | 默认角色 |
| --- | --- |
| 清楚、低风险机械操作 | team_luna_fast / Luna low |
| 冻结方案下的局部低判断实现 | team_luna_executor / Luna medium |
| 用户明确指定 Luna max 的执行 | luna_worker / Luna max |
| 常规判断、一般模块与普通复核 | team_terra_specialist / Terra medium |
| 复杂、跨服务、高风险实施 | team_sol_expert / Sol high |
| 独立高风险审查 | team_sol_reviewer / Sol high |
| 例外高风险或确认 Sol 能力失败 | team_astra_expert / Astra high |

用户对执行模型/强度的明确指定在能力、授权、预算和实际可用性允许时优先。风险能力优先于低价。Max/ultra 不自动强加给其他角色。微小直接执行限最多两次被门禁覆盖的工具调用；更大工作必须重新评估。若有完整路径成本证据证明委派更贵，可记录证据后直做；不得编造估算。普通委派目标无法满足宿主的独立性或 parent_has_work 条件时返回 blocked，不静默改为 Astra 执行。

## 子任务与计量

子代理只执行收到的范围、验证并回报，不重走主任务评估，不递归派工。产品需求和设计门禁继续遵循项目原规则。

原 router.py 的阶段生命周期、恢复及计量命令见 [cli.md](references/cli.md)。只有真实增量 token_usage_record 可计量，按稳定 response_id 去重；缓存输入已含在 input_tokens，推理已含在输出时不重复相加。缺失保持 unknown，价格差不叫 token 节省。统计钩子不负责派工；门禁也不能切换当前主模型、接管未覆盖工具或免除原生信任。
