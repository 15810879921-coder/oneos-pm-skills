# 2026-08-31 Skill 远端同步与回滚说明

## 目标

让 `origin/main` 同时保留远端和本地已经确认的最新能力，并确保 Codex、Cursor 两套公开安装包与源码一致：

- 保留远端 `DB-C-005` 外部写接口防重复提交约束；
- 保留本地发版更新日志机器数据外露修复；
- 同步开发任务 Codex 分段索引与实际工时核算能力；
- 为 `YunxiaoPM`、`yunxiao-development-delivery`、`development-brain`、`YunxiaoQA`、`yunxiao-release-operations` 增加每日首次触发的用户级全局自动更新；
- 重新构建 Codex、Cursor 双端归档和 SHA-256 清单。

## 合并过程

1. 执行前远端基线：`3d25fad2eb82981a5e62d6c2bb2080626af5ab55`。
2. 原本地分支：`codex/release-changelog-visible-only-20260827`，提交为 `f033a9a`，同时存在未提交修改。
3. 为避免改动原始脏工作区，创建独立干净发布工作树：
   `D:\codex\worktrees\oneos-pm-skills-daily-update-publish-20260831`。
4. 在远端基线上重放本地发版修复。冲突只发生在：
   - `packages/codex/manifest.json`
   - `packages/cursor/manifest.json`
5. 冲突处理原则是保留双方有效条目：远端的 `development-brain` 包与哈希、本地的 `yunxiao-release-operations` 包与哈希均不丢失；随后通过最终构建重新生成全部哈希，不手工沿用旧哈希。
6. 发版修复形成提交：`5b26c9b`（`修复发版更新日志机器数据外露`）。
7. 把原工作区中的开发工时核算和每日自动更新修改应用到干净发布工作树，运行测试并重建双端包。
8. 最新能力和安装包形成提交：`d496c53a4e79e705ec8a1d7e2e4acaba853989c1`（`同步云效技能最新能力并增加每日自动更新`）。

原始脏工作区 `D:\codex\work\oneos-dev-release-rules-20260827` 未执行 `reset`、`stash`、清理或覆盖，仍可作为本地恢复副本。

## 验证结果

- Python：`python -m unittest discover -s tests -p 'test_*.py' -v`，29 项通过，0 失败，0 错误。
- 当前环境未安装 `pytest`，因此 `python -m pytest -q` 未执行成功；同一批测试已由标准库 `unittest` 完整运行。
- 每日更新行为测试通过：同日只成功一次、并发互斥、失败冷却 30 分钟、失败不阻断业务。
- 全局安装口令检查通过。
- 开发、测试、开发大脑语义路由检查通过。
- 五份 `ensure-daily-skill-update.mjs` 源码 SHA-256 一致：`C201C4A5E0F8E9EE72C172F27EDEE8970EDF601078CADB82880980AA1CA2D669`。
- Codex、Cursor 各 7 个归档均存在，清单技能唯一，归档 SHA-256 与清单一致；五个目标 Skill 的双端归档均包含每日更新器。
- 通用 Skill 校验中，三个小写名称 Skill 通过；`YunxiaoPM`、`YunxiaoQA` 仍有既有的大写命名兼容提示。为保持已经公开的安装选择器兼容，本次不改名。

## 功能回滚

以下方式通过新增反向提交回滚，不改写远端历史、不使用 `reset --hard` 或强推。它会撤销本次每日自动更新、开发工时核算同步和发版更新日志修复，同时保留回滚前已经在远端的 `DB-C-005`：

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c rollback/skill-sync-20260831
git revert --no-edit d496c53a4e79e705ec8a1d7e2e4acaba853989c1
git revert --no-edit 5b26c9b
git push origin HEAD:main
```

执行回滚前仍需先确认 `origin/main` 没有新的并行提交；若出现冲突，停止并逐项核对，不自动覆盖后续提交。

`d496c53` 同时包含每日自动更新和开发工时核算，两项共用 Skill 文档与安装包。若只想撤销其中一项，不应直接整提交回滚，而应从该提交创建定向反向修改，重新构建双端包并校验清单哈希后再提交。

## 远端读回标准

推送完成必须满足：

- `origin/main` 包含 `5b26c9b`、`d496c53` 及本说明提交；
- 本地发布分支与 `origin/main` 无差异；
- 远端树可读到五份每日更新器、两个检查脚本、两套最新清单和本说明；
- 推送过程未使用 `--force`。
