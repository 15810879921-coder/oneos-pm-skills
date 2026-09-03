# 开发落地 · 交棒包获取与读取协议

> **升档才读**：收到产品交棒包后、字段校验和实现之前。正常任务只执行 §1–§3；只有异常才执行 §4–§6。

## 0. 先分清两类问题

| 类别 | 判定 | 修哪里 |
|------|------|--------|
| **获取不完整** | 文件、附件、页、路由、交互状态没有全部拿到，或版本/来源不对 | 产品补材料清单，或开发修获取方法/适配器 |
| **理解错误** | 获取回执已证明材料完整，但实现语义仍与材料不符 | 等真实反馈后复盘解析步骤，补回归样本 |

产品在读取后修改内容、交棒包本来就漏内容、实现阶段忽略了正确结论、主动裁剪范围，都**不能直接算读取误差**。先归因，再改规则。

## 1. 固定顺序（禁止跳步）

```text
定位唯一交棒包
 → 解析 handoff-manifest
 → 逐项获取 required 材料
 → 核对身份 / 版本 / 完整性 / 页面与状态覆盖
 → 输出 handoff-acquisition-receipt
 → 运行轻量校验器
 → status=complete 且 allowedToParse=true 才能理解需求、校验字段和写代码
```

- 不能用聊天预览、搜索摘要、附件缩略图、浏览器错误页代替原文件。
- 不能凭“我已经看过”自报完整；完整性来自材料清单与获取证据逐项对账。
- 同一材料最多自动重试 **1 次**，从最后一个正确检查点继续；再次失败立即停，不循环消耗开发时间。
- 旧交棒没有 `handoff-manifest` 时标记 `legacy-unverified`：先从正文引用生成临时材料清单，再逐项获取；未对账前不得称“已完整读取”。

## 2. 各类材料怎么拿

| 材料 | 获取方法 | 完整证据 |
|------|----------|----------|
| 本地 Markdown / 文本 | 读取原文件；大文件分段直到 EOF | 最终路径、字节数、SHA-256（可取时）、行范围、`eof=true` |
| 云效/邮件附件 | 用官方入口下载到隔离目录后再读，禁止只看预览 | 附件 ID/最终文件名、字节数、SHA-256、读取覆盖 |
| 在线文档 | 记录最终 URL、HTTP 状态、标题/内容类型；排除登录页、错误页、预览页 | 最终 URL、身份/版本证据、全文或页码覆盖 |
| DOCX | 获取完整文件，读取段落与全部表格 | 文件身份、段落/表格数量和覆盖 |
| PDF | 获取完整文件，先取总页数，再读 1..N；扫描页须视觉读取 | 总页数、已读页集合；连续覆盖到末页 |
| 图片 | 按清单逐张读取，只采信图中可见内容 | 文件身份、尺寸、逐图状态 |
| 在线原型 | 打开权威入口，核对最终 URL/标题/原型 ID；按清单逐路由、逐交互状态读取 | 路由、状态、视口、版本/指纹（可取时）；无范围清单只能写“入口已取得，完整范围未验证” |
| 分段聊天包 | 核对包 ID、`i/N`、每段身份及总段数 | 1..N 无缺段；总哈希可取时记录 |

原型读取不能只看首页。材料清单写了 `list/detail/edit`、弹窗、空态、错态或不同视口，就必须在回执 `coverage` 中逐项出现。

## 3. 获取回执（正常路径唯一新增产物）

人话摘要后附一个 JSON 机器块；字段名和状态值不得改写：

```handoff-acquisition
{
  "schema": "oneos.handoff-acquisition-receipt/v1",
  "packageId": "HANDOFF-ONEOS-000-P0-v1",
  "status": "complete",
  "allowedToParse": true,
  "manifestMaterialCount": 2,
  "requiredMaterialCount": 2,
  "verifiedRequiredCount": 2,
  "materialResults": [
    {
      "id": "prd",
      "status": "verified",
      "evidence": {
        "method": "local_file_raw",
        "finalSource": "src/prototypes/demo/.spec/requirements-prd.md",
        "bytes": 1234,
        "sha256": "可取时填写",
        "coverage": {"lineRanges": ["1-120"], "eof": true}
      }
    },
    {
      "id": "prototype",
      "status": "verified",
      "evidence": {
        "method": "browser_route_state_walk",
        "finalSource": "https://example/prototype",
        "coverage": {"routes": ["/list", "/detail"], "states": ["list", "detail", "edit"], "viewports": ["1440x900"]}
      }
    }
  ]
}
```

`materialResults[].status` 只能为 `verified | missing | partial | conflict | inaccessible`。任一 required 材料不是 `verified`，总状态就不能是 `complete`，`allowedToParse` 必须为 `false`。

校验命令：

```powershell
python skills/oneos-dev-delivery/scripts/validate_handoff_acquisition.py --handoff <交棒包.md> --receipt <获取回执.md> --json
```

退出码：`0=完整可解析`，`2=诚实阻断（不完整/冲突/旧包未验证）`，`1=清单或回执结构错误/虚假完成声明`。

## 4. 什么时候触发“读取误差优化”

以下任一信号只会**打开调查**，不会直接改规则：

1. 开发、产品或测试明确反馈“读错了 / 漏读了”；
2. 同一来源、同一版本两次读取结果不同；
3. 两个 Agent 对同一材料的范围或结论不一致；
4. AI 称完整，但清单计数、页/路由/状态覆盖或校验器不通过；
5. 校验器曾判完整，后续却证实漏材料（`VALIDATOR_FALSE_PASS`）；
6. 反复询问材料中已经明确写出的内容，或重读后方案大幅改变但来源未变；
7. 输出引用了清单外来源，或把推测写成原型事实；
8. 工具、权限、附件格式、原型框架、模型版本变化后，既有回归样本失败；
9. 多个下游实现同时偏离同一原型节点，怀疑上游读取结果系统性错误。

## 5. 异常时怎么找“哪一步、为什么跑偏”

只在 §4 触发后补一份最小追踪，不要求正常任务常驻记录全部思考过程：

```markdown
## 交棒读取偏差追踪
- packageId：
- 信号来源：开发反馈 / 产品反馈 / 测试缺陷 / 一致性检查 / 回归失败
- 期望步骤：
- 实际步骤：
- 最后正确步骤：
- 首个偏离步骤：
- 工具与输入：仅记录工具名、来源身份和参数摘要，不记录凭据
- 可核验输出：状态码、最终 URL、字节/页/行/路由/状态覆盖
- 直接原因：
- 深层原因：为什么会跳步、截断、取错版本或误判完整
- 原门禁为何没拦住：
- 归因：发送端材料 / 获取适配 / 语义解析 / 实现执行 / 非读取问题
- 修复与回归样本：
```

建议原因码：`PACKAGE_MISSING`、`SOURCE_MISMATCH`、`ACCESS_DENIED`、`ADAPTER_MISSING`、`TOOL_FAILURE`、`CONTENT_TRUNCATED`、`STEP_SKIPPED`、`STATE_OMITTED`、`VALIDATOR_FALSE_PASS`、`VERSION_DRIFT`、`CONTEXT_OVERFLOW`。

## 6. 什么时候真的改逻辑

- 证据确认是**获取/解析根因**后，才改对应一步；不要因为出现 Bug 就泛化加门禁。
- 修复必须带最小复现样本：原输入、错误输出特征、正确输出特征、修复后结果。
- 单一 Skill 的样本、脚本和失败记录留在本 Skill；只有跨至少两个不同 Skill/任务重复成立，才提炼为 `development-brain` 候选。
- 优先局部修复：能改材料清单就不加全局重读；能补一个适配器就不要求所有任务截图；能用快速校验器发现就不增加人工确认。

返回：[`handoff-from-pm.md`](handoff-from-pm.md) · [`SKILL.md`](SKILL.md)
