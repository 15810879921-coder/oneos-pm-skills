# Make 导出与截图附件

设计完成（步骤 4）且已关联原型页时：需求与【交付】均挂附件。任一侧失败 → 不得声称设计完成附件齐全。

## 1. 导出 HTML（含源码）ZIP

与 Make「发布 → 导出 HTML（含源码）」对齐。

优先本地 Make Admin：

```http
GET {adminOrigin}/api/export-html?path={prototypePath}&projectId={projectId}&includeSource=true
```

| 参数 | 要求 |
|---|---|
| `path` | 原型路径（如 `prototypes/oneos-h5-vehicle-assets`） |
| `includeSource` | **必须** `true` |
| 响应 | ZIP（`PK` 头）；文件名建议 `{prototype-id}-html-source.zip` |

失败时：提示用户在 Make 客户端对该原型执行「发布 → 导出 HTML（含源码）」，把 ZIP 路径发回。  
**禁止**用「仅对象存储链接」冒充已附带源码包。

## 2. 复制截图（全交互页）

1. Make「发布 → **复制截图**」（或等价：导出该原型主界面及所有交互页截图）。
2. 上传到需求附件与【交付】附件。
3. 缺页/失败 → 列出缺项，不得报成功。

## 3. 挂载范围

同一 ZIP / 同一批截图：

1. 上传到需求 identifier  
2. 上传到【交付】任务 identifier  

优先 API；未知 upload 端点时用已登录浏览器在详情页「附件」上传。

## 4. 与对象存储的关系

| 产物 | 用途 |
|---|---|
| `{baseUrl}/{id}/index.html` | AutoPRD 描述内可点预览链接 |
| 导出 ZIP（含源码） | 附件，供开发离线打开 |
| 交互页截图 | 附件，供评审/开发对照 |

三者职责不同，不可互相替代。

## 负向

- 不得导出错误原型页（须 Plan 确认原型路径/名称）。
- 不得把别的需求的旧 ZIP 复用到新需求。
- 快轨交棒默认不跑本附件流程（除非口令同时设计完成+原型）。
