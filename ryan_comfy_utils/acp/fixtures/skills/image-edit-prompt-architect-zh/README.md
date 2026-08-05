# image-edit-prompt-architect-zh

图片编辑提示词架构师中文版。这是一个只负责分析参考图与用户需求，并生成图片编辑提示词的 Codex / Agent Skill。

## 能做什么

- 分析一张或多张参考图片的用途。
- 自动区分“原图锁脸编辑”和“参考人物身份生成新图”。
- 为换装、换背景、换物体、动作参考、发型、风格、文字替换、商品一致性、修复增强和系列图生成优化提示词。
- 隔离多张参考图的人物身份、服装、姿势、场景、风格和物体职责。
- 修复容易导致换脸、过度编辑、参考图串脸、文字错误和构图漂移的旧提示词。
- 根据 GPT Image、Nano Banana / Gemini 和通用多模态图片编辑器调整提示词结构。

## 明确不做

- 不生成图片。
- 不编辑图片。
- 不调用任何图片生成或图片编辑工具。
- 不声称图片已经生成或修改完成。

## 目录结构

```text
image-edit-prompt-architect-zh/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── identity-consistency.md
│   ├── model-adapters.md
│   ├── quality-checklist.md
│   └── task-patterns.md
└── examples/
    └── examples.md
```

## 安装位置

仓库级：

```text
<项目目录>/.agents/skills/image-edit-prompt-architect-zh/
```

用户级：

```text
$HOME/.agents/skills/image-edit-prompt-architect-zh/
```

## 调用示例

```text
使用 $image-edit-prompt-architect-zh 分析我上传的三张图片：
图片1作为唯一人物身份参考，图片2只参考服装，图片3只参考姿势。
为 GPT Image 生成一条优化后的最终编辑提示词，只输出提示词，不生成图片。
```

```text
使用 $image-edit-prompt-architect-zh 优化下面这条提示词。
当前问题是人物换装以后脸型和五官发生变化，请修复提示词，只输出修复后的版本。
```
