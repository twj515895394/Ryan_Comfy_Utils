# Workflow Agent 结构化产物与上下文预算 V1

> **文档状态：历史 V1 设计，不是当前六阶段内容合同。**  
> 当前 Agent 能力、输出类型与音频交接以 `docs/agents/工作流Agent能力说明-v1.md`、`docs/superpowers/specs/2026-08-12-workflow-agent-content-contract-design.md` 以及各 Skill 目录下的 `SKILL.md` / `agent-contract.json` 为准。当前流程包含创意、美术、剧本、分镜、音频、视频提示词六类 Agent；音频导演主要向视频提示词导演交接按 `SEG_###` 对齐的 `Audio Design Canon`，独立 `audio_prompt` 仅按需输出。

## 1. 目标

在不破坏现有 Workflow Agent Chat、Draft、Commit、`RYAN_CONTEXT` 和 Queue 链路的前提下，让创作型 Agent 的 Commit 同时保存：

- 可供后续 Agent 理解的结构化创作内容；
- 可直接连接生图 / 视频节点的模型无关语义提示词；
- 角色、场景、分镜和视频之间的连续性约束；
- 可追溯的来源 Agent、revision 和 AssetRef。

核心约束：完整产物可以保存在 DAG 中，但不能默认完整注入每个下游 Agent 的模型 Prompt。

## 2. 已确认决策

### 2.1 基于现有 Agent 升级

继续使用当前已经可用的创作 Agent，不新增固定的“提示词解析 Agent”。现有 Agent 的 Commit 输出增加结构化产物协议；Chat、Session、Commit 隔离和 Queue 执行语义保持不变。

只有在处理历史 Markdown、且用户明确要求转换时，才允许增加一次性的 Legacy Markdown 转换工具。它不是主流程节点。

### 2.2 输出策略

采用“统一产物包 + 常用直接输出 + 选择器”的组合：

- Agent 节点继续输出统一 `RYAN_CONTEXT`；
- 常用产物可以作为文本输出直接连接下游节点；
- `Ryan Artifact Selector` 用于提取任意 `output_id`、`shot_id` 或产物类型；
- 提示词保持模型无关，不绑定 Flux、SDXL、Veo、Kling 等模型语法。

### 2.3 分镜粒度

分镜 Agent 同时保存：

- 整组分镜 / 分镜表提示词；
- 逐镜头 `shots[]`；
- 每个镜头的景别、机位、动作、时长和连续性约束。

## 3. 数据结构

`RyanContext` 仍然是 Agent 之间唯一的主 Context Socket。现有 `RyanContextEntry` 继续保留 `content`、`summary`、`kind`、`revision`、`asset_refs` 和 `lineage`。

结构化产物放在 Entry 的受控扩展字段中，建议使用 `metadata.artifact_bundle`，避免破坏已有 Entry 顶层合同：

```json
{
  "artifact_type": "character_design",
  "schema_version": 1,
  "source_agent_uid": "agent_character",
  "revision": 1,
  "content": {
    "design_document": "角色设定正文",
    "semantic_prompts": {
      "character_key_visual": "模型无关的角色主视觉提示词",
      "character_turnaround": "模型无关的角色三视图提示词"
    },
    "constraints": {
      "identity": ["发型", "服装", "脸部特征"],
      "continuity": ["后续镜头必须保持的特征"]
    },
    "shots": []
  },
  "outputs": [
    {
      "output_id": "character_key_visual",
      "kind": "image_prompt",
      "label": "角色主视觉提示词",
      "text": "模型无关的语义提示词",
      "priority": 90
    }
  ]
}
```

### 3.1 `outputs[]` 规则

每个可被节点消费的输出必须具备：

- `output_id`：在同一产物包内稳定唯一；
- `kind`：如 `image_prompt`、`storyboard_sheet_prompt`、`video_prompt`；
- `label`：供 UI 展示；
- `text`：实际输出文本；
- `priority`：用于超预算筛选，不代表模型质量评分。

### 3.2 `shots[]` 规则

`shots[]` 中每个镜头具备：

- `shot_id`；
- `index`；
- `prompt`；
- `shot_size`；
- `camera`；
- `action`；
- `duration`；
- `continuity_constraints`。

## 4. Agent 默认产物映射

| Agent | `artifact_type` | 默认产物 |
|---|---|---|
| 角色设计 | `character_design` | 角色主视觉、三视图、表情表、角色身份与一致性约束 |
| 美术 / 场景设计 | `production_design` / `location_design` | 场景概念图、环境设计、风格参考、场景连续性约束 |
| 分镜导演 | `storyboard_plan` | 整组分镜提示词、`shots[]`、镜头连续性约束 |
| 视频提示词导演 | `video_prompts` | 视频总提示词、逐镜头视频提示词、运动与镜头参数 |

Runtime 不把这些类型写死为唯一枚举。Starter Skill 通过已有的 `accepts_context_kinds`、`produces_context_kind` 等合同声明输入和输出类型。

## 5. Context View：传输 Context 与模型 Context 分离

### 5.1 完整 Context

完整 `RYAN_CONTEXT` 保留在 DAG、仓库和节点输出中，用于：

- lineage 和来源追溯；
- revision 比较；
- UI 检查；
- 产物选择器读取；
- Asset 引用；
- 显式的完整内容读取。

### 5.2 模型 Context

调用 Pi 前，代码根据当前 Agent 的 Context Policy 生成有限的 Context View。当前实现不能继续直接把 `upstream_context.to_json()` 作为唯一模型输入。

```text
完整 RYAN_CONTEXT
  -> 最新 active revision 筛选
  -> 当前 Agent 的 kind 白名单
  -> summary / selected / full 模式
  -> 字符预算
  -> Pi Prompt
```

### 5.3 三种读取模式

| 模式 | 默认使用位置 | 内容 |
|---|---|---|
| `summary` | Agent 自动衔接 | 摘要、来源、revision、必要约束 |
| `selected` | 生图 / 视频 / 逐镜头节点 | 明确选择的 `output_id` 或 `shot_id` |
| `full` | 用户显式请求或人工检查 | 完整产物内容，仍受总预算保护 |

默认 Agent 使用 `summary`；生成节点使用 `selected`；`full` 不作为隐式默认值。

### 5.4 当前 Agent 的默认输入白名单

| 当前 Agent | 默认允许的 Context |
|---|---|
| 角色设计 | 用户需求、必要的主题设定摘要 |
| 美术 / 场景设计 | 角色身份摘要、世界观摘要、选定参考 Asset |
| 分镜导演 | 角色摘要、场景摘要、风格约束、选定 Asset |
| 视频提示词导演 | 分镜摘要、选定 `shots[]`、连续性约束、参考 Asset |

不默认注入 Chat history、旧 revision、未选择的完整产物或二进制内容。

## 6. V1 上下文预算

用户确认使用较宽松的 V1 字符预算。字符预算用于跨模型稳定控制，不引入额外 Tokenizer 依赖。

| 项目 | V1 默认上限 | 备注 |
|---|---:|---|
| 单个 `summary` | 12,000 字符 | 用户指定 |
| 单个选中产物 | 4,000 字符 | 原 3,000 + 1,000 |
| 单个来源总量 | 16,000 字符 | 由 12,000 summary + 至少一个 4,000 output 推导，不能机械设为 6,000 |
| 上游 Context View 总量 | 24,000 字符 | 允许多个来源同时提供摘要和少量选定产物 |
| 当前 Agent Draft | 7,000 字符 | 原 6,000 + 1,000 |
| 用户本轮消息 | 5,000 字符 | 原 4,000 + 1,000 |
| Asset 元数据 | 3,000 字符 | 原 2,000 + 1,000；只传 ID、类型和描述 |

“单个来源总量”和“上游 Context View 总量”是结构约束，不机械套用“加 1,000”规则：它们必须大于能够容纳的摘要和选定产物，否则预算本身互相矛盾。

### 6.1 超预算处理

超预算时按以下优先级保留：

1. 当前 Agent 明确需要的选中 output；
2. 最新 active revision；
3. 来源 summary；
4. 身份 / 连续性约束；
5. Asset 描述；
6. 非目标类型摘要。

从低优先级字段开始省略，不从原始 Commit 中间截断，不修改仓库中的原始内容。Context View 必须带有省略标记：

```text
[Context truncated]
source=agent_storyboard
omitted=3 outputs
reason=model_context_budget
use=Ryan Artifact Selector to request a specific output
```

## 7. 提取、复制与失败处理

### 7.1 提取

- 优先读取结构化 `artifact_bundle`；
- 校验 `artifact_type`、`outputs[]`、`output_id` 和文本字段；
- 只把校验成功的输出注册为可连接产物；
- 通过 `Ryan Artifact Selector` 按来源、revision、`output_id`、`shot_id` 和 `kind` 读取；
- UI 显示来源 Agent 和 revision，复制按钮只复制选中的 `text`。

### 7.2 兼容旧 Commit

旧 Commit 没有结构化产物时：

- 保留原始 Markdown；
- 生成有限摘要视图；
- 不自动猜测其中哪段是提示词；
- 不伪造 `outputs[]`；
- 需要结构化时由用户显式发起一次转换。

### 7.3 失败处理

当 Agent 输出结构不完整、字段类型错误或超出可接受格式时：

- Commit 不因可选产物解析失败而丢失 Draft；
- 保留原始 Commit 正文；
- 标记 `artifact_status=invalid` 或 `artifact_status=partial`；
- UI 显示具体失败原因；
- 下游只暴露校验成功的字段；
- 不把未经确认的文本当成提示词。

## 8. 预计改动范围

### 后端

- `ryan_comfy_utils/workflow_agent/models.py`：增加产物包和镜头结构的 JSON 校验模型；
- `ryan_comfy_utils/workflow_agent/commit_service.py`：Commit 产物规范化和状态记录；
- `ryan_comfy_utils/workflow_agent/context_select.py`：增加 Context Policy、读取模式和预算裁剪；
- `ryan_comfy_utils/workflow_agent/context_merge.py`：保留产物引用、去重和 lineage；
- `ryan_comfy_utils/workflow_agent/chat_service.py`：使用 Context View 构建 Pi Prompt，不再默认注入完整 JSON；
- `ryan_comfy_utils/nodes/workflow_agent_node.py`：保留现有输出并增加常用文本输出。

### 节点与前端

- 新增确定性的 `Ryan Artifact Selector` 节点及其注册；
- `agent_panel.js`：产物目录和复制入口；
- `context_inspector.js`：来源、revision、摘要和选中产物查看；
- `commit_bar.js`：Commit 后产物状态展示；
- `node_extension.js`：常用产物输出、选择器交互和状态同步。

### 不在本次范围

- 不重写现有 Pi Runner；
- 不改变 Chat / Commit API 的基本请求身份字段；
- 不把 Chat history 放入 DAG；
- 不把模型专用语法塞进 Artifact Bundle；
- 不新增固定的 LLM 解析 Agent；
- 不引入数据库或第三方 Tokenizer；
- 不修改 ComfyUI 核心。

## 9. 验收标准

1. 现有未结构化 Commit 仍能正常保存、传递和运行。
2. 结构化 Commit 可同时展示正文、产物目录和来源 revision。
3. Agent 节点仍可输出 `RYAN_CONTEXT`，旧连接不失效。
4. 产物选择器可读取单个 `output_id` 和 `shot_id`，并输出普通文本。
5. Agent 自动衔接只收到 Context View，不收到完整历史 JSON。
6. 同一来源旧 revision 不会默认重复注入。
7. 超预算只省略低优先级 Context，不破坏原始 Commit。
8. 结构化解析失败不会丢失 Draft 或阻断普通 Commit。
9. 角色、场景、分镜、视频四类 Agent 均有明确默认产物映射。
10. Context View 具备来源、revision、省略原因和模式信息，便于诊断漂移问题。
