# Task Plan: Artifact Selector UX V1

## Goal
将 Ryan Artifact Selector 改为“默认自动取上游最新产物/正文 + 可选精确选择”，让普通用户无需理解 UID、Bundle schema 或 kind，并让未 Queue、未 Commit、无结构化产物时的下一步清晰可见。

## Current Phase
Phase 7: Selector现场修复与验证 (complete)

## Phases

### Phase 1: Implementation Planning
- [x] 完成 Python 语义选择合同与兼容映射计划
- [x] 完成前端动态下拉和普通/精确模式计划
- [x] 完成测试、空状态和回归计划
- **Status:** complete

### Phase 2: Implementation
- [x] 按确认后的 A+B 方案更新节点与前端
- [x] 默认 auto 在无结构化 Bundle 时读取最新 Entry 正文
- [x] 保留旧 Workflow 内部字段兼容读取，但不再展示内部字段名称
- **Status:** complete

### Phase 3: User Feedback Design
- [x] 明确默认自动流转与用户可选语义范围
- [x] 明确无 Commit / 无结构化产物 / 未 Queue 的用户提示
- [x] 用户确认本地 HTML 中的 A+B 方案
- **Status:** complete

### Phase 4: Verification
- [x] 运行 Selector 后端与上下游节点回归
- [x] 运行受影响前端语法检查
- [x] 记录用户侧重载工作流、Queue 和视觉验收边界（未启动浏览器或 ComfyUI）
- **Status:** complete

## Errors Encountered

| 完整测试套件缺少 `aiohttp`、`openai`、`scenedetect` | 既有全量测试导入阶段 | 继续使用 Selector、Workflow Agent 与 Context 受影响专项测试；未声称全量通过。 |
| 新增集成测试首次运行缺少 `Path` 导入 | 修改 `test_workflow_agent_node.py` 时误替换原导入行 | 恢复 `from pathlib import Path`，重跑 25 个节点测试通过。 |

### Phase 5: Commit 故障诊断
- [x] 定位 Pi CLI/RPC 与 Commit 错误透传边界
- [x] 复现最小失败场景并验证完整上下文调用
- [x] 修复 Commit 错误详情与最终正文提取
- [x] 运行 Commit、Pi RPC、路由和模块语法回归
- **Status:** complete

## Commit 修复决策

- Pi CLI/RPC 在当前环境可正常启动；不修改命令行配置或 Selector 参数。
- Commit 错误保留底层异常消息，由 HTTP 层现有 `_safe_error()` 负责脱敏。
- `agent_end.final_text` 是 Commit 的权威正文；仅在不存在时回退流式 delta。

## Decisions

- 普通模式只暴露语义下拉，默认 `自动选择`。
- 自动选择优先读取最新结构化产物；没有 Bundle 时读取最新 active Entry 正文，避免下游展示空白。
- 精确模式仍只显示 Agent 名称、产物类型、输出/镜头标签、类型过滤和“第 N 版”，不显示内部 ID。
- 无上游 Context、未 Queue、无 Commit、无结构化产物分别显示下一步提示。
- 显式选择图像/分镜/视频/镜头时不回退到 Entry 正文，避免语义错误。
- 后端继续接受旧字段，前端隐藏旧字段并使用可读标签。


### Phase 6: Windows Pi RPC 进程边界
- [x] 复核 Windows `shell=True` 参数传递与 Pi RPC 事件行为
- [x] 修复可执行文件解析、`shell=False`、会话/授权隔离参数
- [x] 运行专项回归与真实 `get_state` smoke
- **Status:** complete

## Windows Pi RPC 决策

- 进程边界统一使用 `shell=False`；Windows 通过 `shutil.which()` 解析命令入口，避免 `pi`/`pi.cmd` 参数被 `cmd.exe` 重解释。
- 每次 RPC 使用 `--no-session --approve`，避免全局 Session 锁和无 UI 授权等待。
- Provider/模型实际生成仍依赖本机凭据与网络；本次只验证进程启动、RPC 状态响应和本地回归，不伪称模型响应成功。

### Phase 7: Selector 现场修复与验证
- [x] 修复旧字段真正隐藏与基础字段中文标签
- [x] 修复 Commit 结构化 JSON 字段提示与 invalid 状态提示
- [x] 增加默认参数、invalid Bundle 回退正文和 Prompt 合同回归
- [x] 运行 40 个专项测试、前端语法检查和 Python 编译检查
- **Status:** complete