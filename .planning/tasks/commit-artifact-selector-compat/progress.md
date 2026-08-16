# Progress Log

## 2026-08-12

- 已读取 `.scratch/commit-artifact-selector-compat/` 三个问题、现有 artifacts parser、Commit service、Context merge、Selector 与测试。
- 已确认真实旧 Production Design 使用 `revision`、`id`、`role`、`prompt`、`constraint`，导致现有 parser 返回 invalid。
- 尚未修改业务代码。

## 2026-08-12 - Implementation and verification

- `artifacts.py` 新增旧字段规范化：`id -> output_id`、`prompt/constraint -> text`、旧 `revision` 兼容为 `schema_version=1`，并保留旧 Bundle 顶层内容字段。
- `append_commit` 在进入下游 Context 前，将正文中的合法旧 artifact block 提升到 `entry.metadata.artifact_bundle`，同时清理 JSON 区块；解析失败仍保留原正文和 invalid 状态。
- Commit Prompt 明确要求 output/shot 规范字段，并禁止普通 output 使用 `prompt`、`id`、`constraint` 替代字段。
- 新增旧 Production Design、Context 传递、Selector 输出和未来 schema 拒绝回归测试。
- 专项测试通过：41 tests。
- 完整测试套件执行到 125 tests，4 个既有模块因环境缺少 `aiohttp`、`openai`、`scenedetect` 导入失败；与本次改动无关，已记录为环境阻塞。

- 发现并修复前端 Selector 在 Queue 后复用旧空 choices 的问题；现在每次更新都从最新 `_ryanContext` 重建动态选项。
- 前端语法检查通过，暂未启动浏览器或 ComfyUI，符合项目浏览器边界。

## 2026-08-12 - Selector 动态镜头与旧 Bundle 修复

- `shot` 改为后端 `STRING`、前端动态 Combo；避免 ComfyUI 用静态 COMBO 白名单拒绝运行时镜头标签。
- 兼容旧前端值 `自动选择对象`，并统一新旧默认值为 `自动选择镜头`。
- 前端 Selector 在 metadata 缺失或标记 invalid 时，读取正文中的旧 `ryan-artifact` block；兼容 `id/prompt/constraint`、缺失 `shots` 和缺失 `priority`。
- 回归与 Smoke：65 个 Python 测试通过；Node 语法检查通过；真实旧 Commit 前端恢复 16 个输出，其中 9 个图像 Prompt；V2 `SHOT_001` 动态对象可被发现。
