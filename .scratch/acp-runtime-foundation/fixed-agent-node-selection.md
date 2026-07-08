Status: draft

# ACP 首批固定绑定节点选型结论草案

更新时间：2026-07-08

## 1. 结论摘要

建议第一批固定绑定节点只落 **2 个以内**，并采用：

1. `Ryan Video Prompt Agent`
2. `Ryan Image Analyze Agent`

其余候选能力暂时继续保留在 `Ryan ACP Universal Agent` 中，不单独拆节点。

这样做的原因是：当前仓库已经稳定的优势集中在视频关键帧与通用视觉分析，而 storyboard、character design、file generator 仍然更像“开放式 agent 工作流”，现在固定为独立节点会过早锁死产品边界。

## 2. 推荐固定节点

### 2.1 Ryan Video Prompt Agent

**默认 Skill：**
`video_prompt_generator`

**目标用户：**
- 以视频生成为主的 ComfyUI 用户
- 已经在工作流里使用 `Ryan Batch Video Loader` 和 `Ryan Video Frame Sampler` 的用户
- 需要把关键帧分析、镜头总结、提示词生成做成固定工作流入口的用户

**为什么优先：**
- 与当前仓库最强能力方向一致
- 已有视频加载、抽帧、模板基础
- 用户心智明确，固定绑定比 Universal Agent 更省操作

**最小输入 contract：**
- `images` 或 `image_paths`
- `user_text`
- 可选 `task` / `extra_prompt`

**最小输出 contract：**
- `response_text`
- `session_dir`
- `raw_result_json`

### 2.2 Ryan Image Analyze Agent

**默认 Skill：**
`image_analyzer`

**目标用户：**
- 需要对单图或少量图像做说明、检查、比对的用户
- 想要从 Universal Agent 中剥离一个更直接的视觉分析入口的用户

**为什么作为第二优先：**
- 输入输出边界简单
- 与已有 Vision / ACP 能力兼容
- 可以验证“固定绑定节点是否比 Universal Agent 更高频、更省心”

**最小输入 contract：**
- `images` 或 `image_paths`
- `user_text`

**最小输出 contract：**
- `response_text`
- `session_dir`
- `raw_result_json`

## 3. 暂时保留在 Universal Agent 的能力

以下能力当前不建议先拆成固定节点：

### 3.1 Storyboard

**建议保留原因：**
- 目标输出容易从文本扩展到多段结构化内容
- 更适合等 output contract 再成熟一些后再固定

### 3.2 Character Design

**建议保留原因：**
- 角色设定往往带更强的风格约束和多轮交互
- 当前 runtime 还没有专门的角色设计输入输出协议

### 3.3 File Generator

**建议保留原因：**
- 文件生成天然会涉及写文件、副产物路径、格式约束
- 当前虽然已有资产输入，但还没有稳定的“生成文件并回传文件资产”产品心智

## 4. 节点数量控制策略

第一批固定节点遵循以下规则：

1. 固定节点总数控制在 **2 个以内**
2. 只有满足以下条件的能力才允许升级为固定节点：
- 高复用、高频使用
- 输入输出 contract 简单稳定
- 用户目标明确，不依赖大量开放式配置
- 与当前仓库已有基础节点形成明显组合价值
3. 新候选能力必须先在 `Ryan ACP Universal Agent` 中验证，再决定是否单独拆出

## 5. 命名策略

采用统一格式：

`Ryan <场景名> Agent`

规则：

1. 名称描述用户任务，不描述底层模型或 provider
2. 名称优先贴近仓库已形成的场景语言，例如 `Video Prompt`、`Image Analyze`
3. 避免过早引入更强业务承诺的名字，例如 `Director`、`Designer`，除非该节点已经有稳定的专用 contract

## 6. 建议执行顺序

如果结论确认通过，推荐顺序：

1. 先实现 `Ryan Video Prompt Agent`
2. 再实现 `Ryan Image Analyze Agent`
3. 保持 `Ryan ACP Universal Agent` 继续作为探索型入口

## 7. 待确认项

以下内容需要人工确认后才进入实现：

1. 第一批是否就是这 2 个固定节点
2. `Ryan Image Analyze Agent` 是否值得进入第一批，还是只先做 `Ryan Video Prompt Agent`
3. `Storyboard / Character Design / File Generator` 是否统一继续保留在 Universal Agent
