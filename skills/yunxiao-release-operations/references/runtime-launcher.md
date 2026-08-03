# 跨平台脚本启动器

所有文档和跨 Skill 交接只记录统一逻辑口令：

```text
skill-run <script.py> [参数...]
```

执行当前 Skill 的 Agent 将 `skill-run` 解析为本 Skill 自带启动器：Windows 使用 `scripts/run-skill-script.ps1`，macOS/Linux 使用 `scripts/run-skill-script.sh`。禁止读取其他 Skill 的安装目录或固定用户路径。

启动器只允许运行同一 `scripts` 目录中的 `.py` 文件，自动选择通过版本检查的 Python 3，通过系统运行时取得临时目录，并原样返回输出、错误与退出码。找不到解释器、官方 CLI、devops 插件、脚本或认证环境变量，以及参数非法时必须明确失败，不得伪造分类或验收成功，也不得改用浏览器或连接器。

业务接口继续只传递发版任务编号、需求/交付/开发/测试关系、状态和证据；Cosa、Code X 无需共享物理安装路径。
