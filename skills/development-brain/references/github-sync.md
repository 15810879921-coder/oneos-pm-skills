# GitHub 同步门禁

本大脑的权威发布仓为 `https://github.com/15810879921-coder/oneos-pm-skills.git`，目标分支为 `main`。安装目录、临时克隆和本地草稿不是权威知识库。

## 必经流程

1. 在写入任何新知识前，定位该仓的可写、干净工作副本；确认 `origin` 精确指向上述仓库、当前分支为 `main`。
2. `fetch` 后确认本地 `HEAD` 等于 `origin/main`。远端已变化、存在非本次改动、认证/写权限不可用或目标不明确时，停止；不得把知识写进安装目录或本地大脑文件。
3. 再次执行相同/近似模式排除。命中即结束，不产生提交或上传。
4. 仅对新知识修改 `skills/development-brain/knowledge/` 的必要文件；运行 Skill 校验，并用 `build-dual-client-packages.ps1 -SkillNames development-brain` 生成 Codex/Cursor 包，校验两个 ZIP 的 SHA-256 与 manifest。
5. 精确暂存本次知识文件、双端 ZIP、两个 manifest 及其直接相关说明；提交信息使用中文并含知识 ID；推送 `main` 后读取 `refs/heads/main`，确认提交一致。
6. 只有第 5 步读回成功，回执才能写“已入脑/已推送 <commit>”。

## 失败降级

- 任何预检、校验、提交、推送或读回失败：不把内容标记为大脑知识；在当次回执保留候选摘要、评分、证据和失败原因。
- 不使用强推、重置、覆盖、凭据读取或绕过保护规则。远端变化或冲突时停止，等待何斐处理或在新的干净副本重新开始。
