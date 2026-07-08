Status: ready-for-human

# 首批固定绑定 Agent Nodes 选型

## 父问题

`.scratch/acp-runtime-foundation/PRD.md`

## 要构建什么

基于 Universal Agent 的使用反馈，确定第一批固定绑定 Agent Nodes 的产品切分，而不是直接把所有候选节点都做出来。

这一片是一个 HITL 决策切片，需要产出清晰的节点选型结论，包括：

- 哪些 skill 值得升级为固定节点
- 每个固定节点的目标用户与最小输入输出 contract
- 哪些候选能力继续保留在 Universal Agent 里

完成后，后续固定节点实现才有稳定边界，不会因为过早产品化导致节点爆炸。

## 验收标准

- [ ] 形成首批固定绑定节点候选清单
- [ ] 每个候选节点都说明默认 skill、目标场景和最小输入输出
- [ ] 明确哪些能力继续保留在 Universal Agent，不单独拆节点
- [ ] 节点数量控制策略与命名策略有书面结论
- [ ] 该结论获得人工确认后再进入实现

## 被阻塞于

- `.scratch/acp-runtime-foundation/issues/04-universal-agent-minimum-loop.md`

## 评论

### 2026-07-08 决策草案

已基于当前仓库现状生成固定绑定节点选型草案：

` .scratch/acp-runtime-foundation/fixed-agent-node-selection.md `

当前建议：

- 第一批固定节点控制在 2 个以内
- 推荐：
  - `Ryan Video Prompt Agent`
  - `Ryan Image Analyze Agent`
- 暂时继续保留在 `Ryan ACP Universal Agent`：
  - `Ryan Storyboard Agent`
  - `Ryan Character Design Agent`
  - `Ryan File Generator Agent`

等待人工确认后，再进入固定节点实现阶段。
