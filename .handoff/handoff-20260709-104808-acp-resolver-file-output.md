# Ryan_Comfy_Utils ACP Handoff - Skill Resolver & File Output

时间：2026-07-09 10:48:08 Asia/Singapore

基于上一版交接：`.handoff/handoff-20260708-233204.md`

## 1. 本次修正重点

本次主要修正两个概念：

1. `File Generator Agent` 命名不准确，后续不再按 Agent 命名。
2. `Skill Resolver` 当前是隐式逻辑，需要独立模块化。

---

# 2. File Generator 命名修正

## 2.1 结论

后续不使用：

```text
Ryan File Generator Agent
```

原因：

该能力本质不是调用 Agent 执行某个 Skill，而是把已有节点输出内容写入文件、生成文件路径、管理导出文件。

它更接近工具节点 / 导出节点，而不是 Agent 节点。

## 2.2 新命名建议

推荐命名：

```text
Ryan File Exporter
```

或者：

```text
Ryan Text File Exporter
```

如果后续需要支持更多类型，可扩展为：

```text
Ryan File Exporter
Ryan Markdown Exporter
Ryan JSON Exporter
Ryan Prompt Exporter
```

第一版建议只做一个通用：

```text
Ryan File Exporter
```

## 2.3 节点定位

`Ryan File Exporter` 是普通工具节点，不走 ACP Runtime。

它不需要：

- Skill Resolver
- Context Builder
- Claude CLI
- Codex CLI
- Skill Repository

它只负责：

- 接收文本
- 写入 ComfyUI output 目录
- 返回文件路径
- 可选返回原文本

## 2.4 建议节点输入

```text
text: STRING
output_subdir: STRING，默认 ryan_acp_exports/manual
filename: STRING，可空
default_extension: 选项 txt / md / json
append_timestamp: BOOLEAN，默认 true
overwrite: BOOLEAN，默认 false
```

## 2.5 建议节点输出

```text
file_path: STRING
file_text: STRING
```

## 2.6 与现有 file_exporter.py 的关系

当前已存在：

```text
ryan_comfy_utils/acp/file_exporter.py
```

当前用途：

- Image Prompt / Video Prompt / Image Analyze 节点内部 export_to_file 开关使用。

后续建议：

1. 保留该工具模块。
2. 基于它新增独立 ComfyUI 工具节点 `Ryan File Exporter`。
3. 不把该节点放入 `Ryan Utils / ACP`，而是放入：

```text
Ryan Utils / File
```

或：

```text
Ryan Utils / Output
```

推荐：

```text
Ryan Utils / File
```

---

# 3. Skill Resolver 独立模块化

## 3.1 当前状态

当前 Skill 解析逻辑已经存在，但不是独立模块。

分散在：

```text
ryan_comfy_utils/nodes/acp_nodes.py
ryan_comfy_utils/acp/skill_loader.py
ryan_comfy_utils/acp/contracts.py
```

典型逻辑：

- 固定节点从 manifest 读取 skill_id。
- Universal Agent 允许用户输入 skill_id。
- resolve_skill_root 解析 Skill 根目录。
- execute_text_session 接收 skill_id 与 skill_root。

## 3.2 问题

当前实现能跑，但职责不够清晰。

问题：

1. Fixed Skill Binding 和 User Selectable Skill 的差异散落在节点逻辑里。
2. Universal Agent 与固定 Agent 都自己处理 skill_id。
3. 后续新增节点时容易重复写绑定逻辑。
4. Skill 目录、Skill ID、Manifest 默认值、用户覆盖值之间的优先级没有独立表达。

## 3.3 目标设计

新增独立模块：

```text
ryan_comfy_utils/acp/skill_resolver.py
```

职责：

- 解析当前节点最终使用哪个 Skill。
- 统一处理 Fixed Binding 与 User Selectable Skill。
- 统一处理 skill_root。
- 输出标准 SkillBinding 对象。

## 3.4 核心概念

### SkillBinding

建议数据结构：

```python
@dataclass
class SkillBinding:
    skill_id: str
    skill_root: Path
    skill_dir: Path
    mode: str  # fixed | selectable
    source: str  # manifest | user_input | default
```

## 3.5 Resolver 输入

```python
resolve_skill_binding(
    manifest: dict,
    skill_root_text: str,
    user_skill_id: str = "",
    allow_user_skill: bool = False,
) -> SkillBinding
```

## 3.6 Resolver 规则

### Fixed Skill Binding

适用于：

- Ryan Image Prompt Agent
- Ryan Video Prompt Agent
- Ryan Image Analyze Agent

规则：

```text
allow_user_skill = false
最终 skill_id = manifest.skill_id
用户不能覆盖
```

### User Selectable Skill

适用于：

- Ryan ACP Universal Agent

规则：

```text
allow_user_skill = true
如果用户填写 skill_id，则使用用户输入
否则 fallback 到 manifest.skill_id
```

## 3.7 Resolver 输出给 Runtime

所有 ACP Agent 节点最终都不直接传 skill_id，而是传：

```text
SkillBinding.skill_id
SkillBinding.skill_root
SkillBinding.skill_dir
```

给：

```text
execute_text_session
```

或未来 Runtime 入口。

## 3.8 重构后流程

```text
Agent Node
        |
        v
load_manifest
        |
        v
resolve_skill_binding
        |
        v
resolve images/files
        |
        v
execute_text_session
        |
        v
map_result_fields
        |
        v
ComfyUI outputs
```

---

# 4. 两块后续开发任务

## P0：Skill Resolver 独立化

任务：

1. 新增 `ryan_comfy_utils/acp/skill_resolver.py`。
2. 定义 `SkillBinding`。
3. 实现 `resolve_skill_binding()`。
4. 修改 `RyanACPUniversalAgent`，改用 resolver。
5. 修改 `run_fixed_acp_agent()`，改用 resolver。
6. 增加单元测试：
   - fixed 模式不能被用户覆盖
   - selectable 模式优先用户 skill_id
   - selectable 模式 fallback manifest skill_id
   - skill_root 为空时使用默认解析规则

## P1：File Exporter 工具节点

任务：

1. 新增 ComfyUI 节点：`Ryan File Exporter`。
2. 分类：`Ryan Utils / File`。
3. 复用 `ryan_comfy_utils/acp/file_exporter.py` 或抽出更通用模块。
4. 输入：`text / output_subdir / filename / extension / append_timestamp / overwrite`。
5. 输出：`file_path / file_text`。
6. 单元测试：
   - txt 写入
   - md 写入
   - json 写入
   - timestamp 防覆盖
   - overwrite 行为

## P2：文档修正

任务：

1. 更新 ACP Runtime 架构文档，移除 `File Generator Agent` 命名。
2. 更新 handoff-20260708-233204.md 的后续任务引用，标注 supersede。
3. 更新 README 节点列表。
4. 增加 File Exporter 使用示例。

---

# 5. 当前节点完成度校准

## 已完成

```text
Ryan ACP Universal Agent
Ryan Image Prompt Agent
Ryan Video Prompt Agent
Ryan Image Analyze Agent
```

## 已完成但需要重构

```text
Skill Binding / Skill Resolve 逻辑
```

当前可用，但需要独立成 `skill_resolver.py`。

## 已完成部分能力，但不应叫 Agent

```text
file_exporter.py
export_to_file 开关
```

后续应演化为：

```text
Ryan File Exporter
```

## 暂缓

```text
Ryan Storyboard Agent
Ryan Character Design Agent
```

目前仍建议先用 Universal Agent 探索，不急于固定。

---

# 6. 下一步推荐顺序

推荐下一刀：

```text
1. Skill Resolver 独立模块化
2. Ryan File Exporter 工具节点
3. Claude/Codex 真实 CLI 联调
4. 再考虑 Storyboard / Character 固定节点
```

原因：

- Resolver 是 ACP 架构稳定性的核心。
- File Exporter 是当前 issue 11 剩余项，但不应走 Agent 命名。
- CLI 联调前，需要先把 Runtime 结构收紧。

---

# 7. 关键架构结论

最终原则继续保持：

```text
Node = 稳定 ComfyUI 入口
Skill = 可复用 Agent 能力资产
ACP = Agent 执行 Runtime
File Exporter = 普通文件工具节点，不是 Agent
Skill Resolver = ACP Runtime 的独立模块
```
