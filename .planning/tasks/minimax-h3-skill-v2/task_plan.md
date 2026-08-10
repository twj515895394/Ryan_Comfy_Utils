# MiniMax H3 Skill v2 Implementation Plan

**Goal:** 将当前中文 MiniMax H3 提示词 skill 与官方 h3-prompt-writing 及八种官方风格能力整合为统一、可扩展、可回归验证的 skill。

**Architecture:** 保留当前用户友好的中文编排层，新增官方 H3 模式、字段和引用协议作为内部规范；风格能力通过独立路由和配置注入，不污染通用模式核心。

**Tech Stack:** Markdown skill documents, reference templates, checklist and fixture-based scenario review.

---

### Phase 1: Design contract
**Status:** complete

- [x] 完成模式、素材、输出和语言策略设计
- [x] 完成官方八种风格路由边界设计
- [x] 记录兼容策略与非目标

### Phase 2: Issue decomposition
**Status:** complete

- [x] 将已确认设计拆为垂直切片 issues
- [x] 获得用户对切片粒度和依赖关系的确认
- [x] 按依赖顺序发布 issues

### Phase 3: Skill implementation
**Status:** complete

- [x] 更新主 skill 工作流和模式矩阵
- [x] 更新 H3 规则、模板和引用协议
- [x] 增加八种官方风格路由配置
- [x] 更新质量检查和回归场景

### Phase 4: Verification
**Status:** complete

- [x] 执行代表性场景检查
- [x] 检查官方字段、标签和时间规则一致性
- [x] 记录剩余风险与后续风格扩展方式

### Phase 5: ACP H3 agent synchronization
**Status:** complete

- [x] 同步 H3 Agent manifest 输入合同和 context 指令
- [x] 传递图片、抽帧、视频和音频资产到 ACP
- [x] 同步官方模式、角色映射字段和风格路由
- [x] 更新节点测试并执行模块级验证

### Phase 6: ACP widget compatibility regression
**Status:** complete

- [x] 恢复旧 widget 顺序并保留旧模式值
- [x] 无视频时忽略 video_start_frame 和 video_frame_count
- [x] 增加旧工作流兼容和无视频回归测试
- [x] 执行 ACP 全量回归和语法检查

## Errors Encountered

| Error | Attempt | Resolution |
|---|---:|---|
| 根目录 CONTEXT.md 未在预期相对路径找到 | 1 | 继续依据已加载 AGENTS.md、当前 skill 文件和官方仓库资料，未虚构项目上下文 |
