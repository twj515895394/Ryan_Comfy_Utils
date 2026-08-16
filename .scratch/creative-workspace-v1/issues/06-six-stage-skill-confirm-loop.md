Status: ready-for-agent

# 06 六 Stage Skill 切换与确认闭环（后端）

## 父问题

- `.scratch/creative-workspace-v1/PRD.md`

## 必读索引

- 架构文档 §7–11、§20–21、§45
- 现有 skills：`creative-story-planner` 等六目录
- PRD Grill 裁定 7–8、10；Utility 不进 Canon

## 要构建什么

后端闭合六 Stage 创作环：

- Stage ↔ 默认 Skill 映射与切换（含 slash 元数据 API）  
- Context Compiler 最小版：按 Stage 合同注入上游 **Canon**（非 Chat 全量）  
- Stage Skill 讨论/确认全路径；Utility Skill 标记 `promote_result=false`，确认不会把其单轮结果当 Canon，除非进入 Stage 主结果  
- `SHOT_xxx` 对齐规则在 video_prompt 确认校验中的最小落实（允许子集，禁止随意改名导致无法对应时的明确错误/警告策略按 PRD 推荐）

## 验收标准

- [ ] 六 Stage 均可绑定正确 Skill 完成 discuss→confirm→落盘
- [ ] 上游 canon 变更后下游 STALE，再确认可解除自身 STALE
- [ ] Utility 单轮结果不能直接充当 Stage Canon
- [ ] storyboard/video 主 items 使用对齐的 shot id 约定
- [ ] 单测覆盖切换 Skill、确认闭环、Utility 边界

## 被阻塞于

- `04-confirm-stage-and-reopen`
- `05-creative-chat-thread-discuss`

## 评论

