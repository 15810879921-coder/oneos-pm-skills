# 测试缺陷特殊修复通道

## 触发

```text
提交缺陷修复请求：缺陷=ONEOS-123；测试任务=ONEOS-456；证据清单=C:\path\bug-evidence.json；描述=登录后列表为空
```

证据清单至少包含：

```json
{
  "schemaVersion": "oneos.test-bug-evidence/v1",
  "environment": "test",
  "steps": ["登录", "进入列表"],
  "actual": "列表为空",
  "expected": "显示当前用户数据",
  "evidence": [{"type": "screenshot", "ref": "https://..."}],
  "diagnosis": {
    "classification": "待确认",
    "confidence": "unknown",
    "basis": []
  }
}
```

## 处理边界

1. QA 只负责证据规范化、Bug/【测试】关系核验、重复请求幂等和评论回读。
2. 评论使用`oneos.test-bug-repair-request/v1`，保存证据哈希和当前测试用户；不得写入密码、Cookie、Token、OTP或私钥。
3. QA 不改Bug状态、不改代码、不建分支、不提交MR。Bug 必须正式`ASSOCIATED→【测试】`且当前状态为`待确认`、`处理中`或`再次打开`。
4. 开发入口重新读取最新评论和Bug负责人；通过后追加`oneos.development-bug-repair-acceptance/v1`评论，直接进入已有`修复bug:<ID>`链路。
5. 开发完成只能二选一：
   - `已修复`：真实代码验证、MR合并和官方回读证据齐全，并记录待部署、待交付测试；
   - `暂不修复`：提交原因、批准人、批准证据和后续动作，追加受管记录后再改状态。

请求评论只是修复输入，不等于代码已修复、测试已回归或可以关闭Bug。测试仍须在真实测试版本上复测，之后才能执行`已修复→已关闭`。
