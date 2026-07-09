Status: ready-for-agent

# ACP Runtime Foundation PRD

## 问题陈述

当前 `Ryan_Comfy_Utils` 已经具备一批 ComfyUI 基础节点，但 ACP 方向仍停留在架构文档阶段。用户无法在 ComfyUI 中以稳定、可追踪、可调试的方式调用本地 Claude CLI / Codex CLI，也无法把 Skill 能力资产与 ComfyUI 工作流解耦后复用。

缺少的不是单个节点，而是一层稳定的 ACP Runtime Foundation：它需要定义 Node 与 Skill 的契约、负责 session/workspace 生命周期、组织上下文、执行 CLI，并将结果映射回 ComfyUI 输出。

## 解决方案

构建一个独立的 ACP Runtime Foundation，先支持最小的文本输入输出闭环，再逐步扩展图片、文件与固定绑定节点。

该方案分三层：

1. 定义稳定协议：`Node Manifest`、`ACP Profile`、`ACP Context`、`Result Payload`
2. 实现最小 runtime：session/workspace、skill/context、CLI runner、result parser
3. 接入一个最小 `Ryan ACP Universal Agent` 节点，验证从 ComfyUI 输入到 CLI 输出再回到 ComfyUI 的完整链路

## 用户故事

1. 作为 ComfyUI 工作流作者，我想通过一个通用 Agent 节点调用本地 CLI，以便把 Agent 能力接入现有工作流。
2. 作为节点开发者，我想为 Agent 节点声明稳定的 manifest，以便节点输入输出与 skill 绑定关系不会散落在代码里。
3. 作为 runtime 维护者，我想为不同 CLI 运行器声明 profile，以便统一管理命令、超时、workspace 根目录和环境变量。
4. 作为 Skill 使用者，我想把 Skill 目录与 ComfyUI 节点解耦，以便同一 Skill 可以被多个入口复用。
5. 作为调试者，我想让每次节点执行都生成独立 session，以便复盘输入、上下文、日志和输出。
6. 作为实现者，我想把 ComfyUI 文本输入转换成结构化 ACP Context，以便 CLI 调用前后都有明确的数据边界。
7. 作为实现者，我想让 Context Template 只负责占位符替换和上下文封装，以便 Skill 规则继续保留在 Skill 本身。
8. 作为 CLI 运行时，我想捕获 stdout、stderr、退出码和超时信息，以便定位失败原因。
9. 作为结果解析器，我想优先读取结构化结果文件，并在缺失时回退到 stdout，以便兼容不同运行器能力。
10. 作为 ComfyUI 用户，我想先获得文本输入输出的最小闭环，以便在不引入图片/文件复杂度的情况下验证 ACP 基础能力。
11. 作为后续扩展者，我想在 runtime 稳定后再增加图片和文件输入，以便减少第一阶段的实现面和返工风险。
12. 作为产品设计者，我想在 Universal Agent 打通后再决定固定绑定节点集合，以便避免节点爆炸和错误的产品切分。

## 实现决策

- ACP 在本项目中是 runtime，不是 skill。本轮不把 ACP 实现成某个 Skill，而是在 `ryan_comfy_utils/acp/` 下新增运行时包。
- Skill 与 ComfyUI Node 保持解耦。Node 只负责输入输出 contract 和 runtime 适配，Skill 继续负责 instructions、专业规则与行为约束。
- 第一阶段只实现文本输入输出闭环。`images`、`files` 和复杂 output mapping 作为后续增量能力处理。
- `Node Manifest` 至少要包含：`node_id`、`skill_id`、`mode`、`context_template`、`input_contract`、`output_contract`、`result_mapping`。
- `ACP Profile` 至少要包含：`runner`、`command`、`workspace_root`、`timeout_seconds`、`environment`。
- `ACP Context` 至少要包含：`skill`、`input`、`workspace` 三段，其中 `input` 第一阶段保证 `text` 可用。
- `Result Payload` 至少要包含：`status`、`outputs`，并允许携带 `raw_result_json` 用于调试。
- Session 模式采用同步 blocking 模型：一次节点执行等于一次 ACP Session，等于一次 CLI 调用。
- Session 默认持久化到 `output/acp_workspace/sessions/session_xxx/`，目录下至少保留 `input/`、`output/`、`logs/`、`metadata.json`、`context.json`。
- `Ryan ACP Universal Agent` 作为第一阶段唯一接入节点，默认支持 user-selected skill，不在第一阶段创建多组固定绑定节点。
- CLI runner 第一阶段先用假命令和本地 fixture 跑测试，不要求在单元测试里依赖真实 Codex/Claude CLI。

## 测试决策

- 好测试应只验证外部行为，不绑定内部实现细节。例如：验证 manifest 是否能加载、workspace 目录是否创建、runtime 是否返回约定字段，而不是验证某个私有函数内部怎么拼字符串。
- 需要测试的模块：
  - `contracts.py`
  - `session.py`
  - `workspace.py`
  - `context_builder.py`
  - `template_engine.py`
  - `cli_runner.py`
  - `result_parser.py`
  - `runtime.py`
  - `nodes/acp_nodes.py`
- 第一阶段优先使用 `unittest` 和 fake CLI 命令进行单元测试，避免额外引入测试框架依赖。
- 节点测试重点放在 ComfyUI contract：`INPUT_TYPES`、`RETURN_TYPES`、`RETURN_NAMES` 和 runtime 调用输出，不测试 ComfyUI UI 层行为。
- 图片/文件输入与真实 CLI 联调暂不纳入这一轮测试重点，留待后续专门 issue。

## 超出范围

- 固定绑定 Agent Nodes 的完整产品矩阵
- 图片输入、视频帧输入和文件输入的完整 ACP 适配
- 复杂的多字段 output contract 映射
- session 自动清理策略
- 真实 Codex CLI / Claude CLI 的全平台兼容性联调
- 前端状态展示、历史 session 浏览、调试 UI

## 进一步说明

- 这一轮的重点是把 ACP 从“架构描述”推进到“可实现、可测试、可接入”的状态。
- Universal Agent 是验证 runtime Foundation 的手段，不是最终产品形态。
- 如果第一阶段顺利完成，下一轮优先考虑图片/文件输入和首批固定绑定节点选型。
