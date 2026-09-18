# 实现

router.py 负责确定模型和阶段账本；execution_gate.py 负责覆盖路径上的评估/派工检查；原生 spawn_agent 执行模型调用；usage_hook.py/meter.py 仍是独立统计附件。

Astra 协调保留当前实际强度。独立派工条件是宿主约束，2.1 没有删除它；删除的是“条件不满足就默认昂贵主模型做”的路径。任务语义分类由协调者完成，门禁不提供绝对判断保证。

原生门禁单独使用 SQLite 按实际线程和轮次隔离、按 tool_use_id 关联调用结果，并回读子任务模型和强度。详细限制、验收和原生信任见技能 references/execution-gate.md。安装与回滚复用事务式文件备份机制。
