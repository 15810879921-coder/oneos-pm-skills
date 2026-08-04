# TestHub CLI 适配

## 适用范围

测试计划、用例和执行结果优先使用官方阿里云 CLI `devops` 插件。当前 CLI `3.4.11` / devops插件 `0.5.2` 尚未暴露“把已有用例规划进测试计划”的命令，公开OpenAPI也没有该写接口。本 Skill 必须如实返回`CLI_CAPABILITY_GAP`并零写入；不得改用Cookie或浏览器写入绕过。

环境变量：

- `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN`
- `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID`
- 可选 `ALIYUN_CLI_PATH`

## 规划并执行单条用例

先预检：

```powershell
skill-run yunxiao_cli_testhub.py `
  --test-plan-id <计划ID> `
  --test-repo-id <用例库ID> `
  --testcase-id <用例内部ID> `
  --executor-id <执行人userId>
```

确认后执行：

```powershell
skill-run yunxiao_cli_testhub.py `
  --test-plan-id <计划ID> `
  --test-repo-id <用例库ID> `
  --testcase-id <用例内部ID> `
  --executor-id <执行人userId> `
  --status PASS `
  --apply
```

适配器的硬门禁：

1. 先用官方 CLI 回读用例和计划目录。
2. 若用例未规划，返回`CLI_CAPABILITY_GAP`，回执记录阻塞原因并停止；不得猜测未公开OAPI路由。
3. 只有官方 CLI 的计划结果目录和结果列表已回读到同一用例，才允许更新执行结果。
4. PASS/FAILURE/POSTPONE/TODO 更新调用官方 `test-hub-update-test-result`。
5. 最后回读计划进度和用例结果；未匹配目标状态时返回失败，不得据此关闭测试任务。
6. 回执不写 PAT，所有异常信息都执行令牌脱敏。
