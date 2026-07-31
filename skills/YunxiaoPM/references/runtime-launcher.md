# 跨平台脚本启动器

## 统一业务口令

所有文档、交接信息和后续动作只记录逻辑口令：

```text
skill-run <script.py> [参数...]
```

`skill-run` 不是要求员工另外安装的系统命令。执行当前 Skill 的 Agent 必须将它解析为本 Skill 自带的本地启动器，禁止到其他 Skill 或任何预设的物理安装目录中搜索脚本。

## 本地解析规则

- Windows：执行当前 Skill 根目录下的 `scripts/run-skill-script.ps1`。
- macOS/Linux：执行当前 Skill 根目录下的 `scripts/run-skill-script.sh`。
- 启动器只允许运行同一 `scripts` 目录中的 `.py` 文件，不接受绝对路径、相对目录或路径穿越。
- Windows 由启动器探测可用的 Python 3；macOS/Linux 同样只接受通过版本检查的 Python 3。
- 临时目录通过系统运行时获取并写入 `ONEOS_YUNXIAO_TEMP_DIR`，禁止硬编码平台专用临时目录。
- 标准输出、标准错误和退出码必须原样返回；找不到 Python 3、脚本不存在或参数非法时必须明确失败，不得伪造成功或静默改走浏览器。

## Agent 调用示意

以下内容仅说明解析关系，不得复制物理安装路径到业务交接：

```text
Windows    当前 Skill/scripts/run-skill-script.ps1 <script.py> [参数...]
macOS      当前 Skill/scripts/run-skill-script.sh  <script.py> [参数...]
Linux      当前 Skill/scripts/run-skill-script.sh  <script.py> [参数...]
```

业务链路因此只传递 Skill 正式名、任务编号、状态/关系和必要证据；Cosa、Code X 或其他宿主无需知道另一端的安装目录。
