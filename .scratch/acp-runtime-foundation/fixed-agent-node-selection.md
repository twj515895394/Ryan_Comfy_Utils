Status: confirmed

# ACP 首批固定绑定节点选型结论草案

更新时间：2026-07-08

## 1. 结论摘要

建议第一批固定绑定节点只落 **2 个以内**，并采用：

1. `Ryan Image Prompt Agent`
2. `Ryan Video Prompt Agent`

其余候选能力暂时继续保留在 `Ryan ACP Universal Agent` 中，不单独拆节点。

这样做的原因是：当前仓库下一阶段的重点不是“分析 agent”，而是“提示词创作 agent”。`Image Prompt` 和 `Video Prompt` 都可以围绕“任意风格、题材、场景的提示词生成”建立清晰心智，而 storyboard、character design、file generator 仍然更像“开放式 agent 工作流”，现在固定为独立节点会过早锁死产品边界。

## 2. 推荐固定节点

### 2.1 Ryan Image Prompt Agent

**默认 Skill：**
`image_prompt_generator`

**目标用户：**
- 需要为任意风格、题材、场景生成图像提示词的 ComfyUI 用户
- 希望基于单图、参考图、题材描述或意图描述快速得到高质量图像 prompt 的用户
- 希望把“图像提示词创作”从 `Ryan ACP Universal Agent` 中剥离成固定高频入口的用户

**为什么优先：**
- 这是当前用户明确提出的最高优先级方向之一
- “图像提示词生成”比“图像分析”更符合下一阶段产品目标
- 用户心智明确，固定绑定比 Universal Agent 更省操作

**最小输入 contract：**
- `images` 或 `image_paths`
- `user_text`
- 可选 `style` / `subject` / `scene` / `extra_prompt`

**最小输出 contract：**
- `response_text`
- `session_dir`
- `raw_result_json`

**核心目标：**
- 能创作任意风格、题材、场景的图像生成提示词
- 允许参考图参与，但输出目标是“创作 prompt”，不是“分析图片”

### 2.2 Ryan Video Prompt Agent

**默认 Skill：**
`video_prompt_generator`

**目标用户：**
- 以视频生成为主的 ComfyUI 用户
- 已经在工作流里使用 `Ryan Batch Video Loader` 和 `Ryan Video Frame Sampler` 的用户
- 希望基于关键帧、镜头意图、风格要求生成视频 prompt 的用户

**为什么作为第二优先：**
- 这是当前用户明确提出的最高优先级方向之一
- 与现有视频加载、抽帧、内置 prompt 基础最贴近
- 比 storyboard 这类更开放的能力更容易形成清晰固定入口

**最小输入 contract：**
- `images` 或 `image_paths`
- `user_text`
- 可选 `task` / `extra_prompt`

**最小输出 contract：**
- `response_text`
- `session_dir`
- `raw_result_json`

**核心目标：**
- 能创作任意风格、题材、场景的视频生成提示词
- 输入可以来自关键帧或镜头描述，但输出目标是“创作 prompt”，不是“做内容分析或质检”

## 3. 暂时保留在 Universal Agent 的能力

以下能力当前不建议先拆成固定节点：

### 3.1 Image Analyze

**第二批已确认升级为固定节点（issue 10）：**
- 产品定义为**图像反推提示词**（参考图 → 可复用绘图 prompt），与 Image Prompt「从意图创作」分工
- Skill 内收敛 7 类反推模板 + `category` / `output_language` 节点输入

**此前暂缓原因（首批）：**
- 首批优先「提示词创作」而非分析；首批名额已满

### 3.2 Storyboard

**建议保留原因：**
- 目标输出容易从文本扩展到多段结构化内容
- 更适合等 output contract 再成熟一些后再固定

### 3.3 Character Design

**建议保留原因：**
- 角色设定往往带更强的风格约束和多轮交互
- 当前 runtime 还没有专门的角色设计输入输出协议

### 3.4 File Generator

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
2. 名称优先贴近用户任务语言，例如 `Image Prompt`、`Video Prompt`
3. 避免过早引入更强业务承诺的名字，例如 `Director`、`Designer`，除非该节点已经有稳定的专用 contract

## 6. 建议执行顺序

如果结论确认通过，推荐顺序：

1. 先实现 `Ryan Image Prompt Agent`
2. 再实现 `Ryan Video Prompt Agent`
3. 保持 `Ryan ACP Universal Agent` 继续作为探索型入口

## 7. 待确认项

以下内容需要人工确认后才进入实现：

1. 第一批是否就是这 2 个固定节点
2. 是否接受“提示词创作优先于分析能力”的排序
3. `Image Analyze / Storyboard / Character Design / File Generator` 是否统一继续保留在 Universal Agent
