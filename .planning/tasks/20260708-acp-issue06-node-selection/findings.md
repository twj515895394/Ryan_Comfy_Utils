# Findings & Decisions

## Requirements
- 形成首批固定绑定节点候选清单。
- 每个候选节点说明默认 skill、目标场景和最小输入输出。
- 明确保留在 Universal Agent 的能力集合。
- 节点数量控制策略和命名策略要有书面结论。
- 结论需要用户确认后才算完成。

## Research Findings
- 当前仓库已经稳定落地的 ACP 能力是：
  - `Ryan ACP Universal Agent`
  - 文本输入输出闭环
  - 资产落盘与结果映射
- 仓库已有强相关基础节点集中在视频场景：
  - `Ryan Batch Video Loader`
  - `Ryan Video Frame Sampler`
  - `Ryan Prompt Template`
- 现有内置 prompt 也偏视频关键帧分析：`ryan_comfy_utils/prompts/video_frame_analysis.md`
- handoff 和架构文档中曾列过候选固定节点：
  - `Ryan Video Prompt Agent`
  - `Ryan Storyboard Agent`
  - `Ryan Image Analyze Agent`
  - `Ryan Character Design Agent`
  - `Ryan File Generator Agent`
- 其中真正与当前仓库能力最贴近的是视频分析 / 视频提示词生成，其次是通用图像分析；而 storyboard、character、file generator 都更依赖复杂输出或更强业务约束。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 第一批固定节点数量控制在 2 个以内 | 防止节点爆炸，先验证“固定绑定是否真的提升体验” |
| 优先推荐 `Ryan Video Prompt Agent` | 与当前视频加载、抽帧、内置 prompt、ACP 文本闭环最一致 |
| 第二优先推荐 `Ryan Image Analyze Agent` | 单图/多图分析是通用且稳定的视觉入口，输入输出 contract 相对简单 |
| `Storyboard / Character Design / File Generator` 先保留在 Universal Agent | 它们的场景更开放、输出更复杂，当前过早固定会锁死产品边界 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- `.scratch/acp-runtime-foundation/issues/06-fixed-agent-node-selection.md`
- `.scratch/acp-runtime-foundation/PRD.md`
- `README.md`
- `.handoff/20260708_092500_ACP_Design_Handoff_v2.md`
- `docs/20260708_ACP_Runtime_Architecture_Design_v1.md`
