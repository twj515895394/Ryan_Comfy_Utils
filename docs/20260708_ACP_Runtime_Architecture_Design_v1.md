# ACP Runtime Architecture Design v1

## 1. 定位

ACP 在 Ryan_Comfy_Utils 中不是业务 Skill 本身，而是连接本地 Agent Runtime 的执行层。

支持：

- Claude CLI
- Codex CLI

执行模式：

- 同步 blocking
- 单次调用单 Session
- 不支持异步 callback / websocket / polling

## 2. 总体架构

```
ComfyUI Workflow
        |
        v
Agent Adapter Node
        |
        v
Skill Resolver
        |
        v
Context Builder
        |
        v
ACP Runtime
        |
        +---- Claude CLI
        |
        +---- Codex CLI
        |
        v
Skill Repository
```

## 3. 核心职责划分

### Skill

独立 Agent 能力资产。

负责：

- 能力定义
- instructions
- 专业规则
- Agent 行为约束
- 示例和参考资料

不负责：

- ComfyUI 输入输出
- IMAGE / STRING 类型
- Node 定义

### Agent Adapter Node

ComfyUI 层固定节点。

负责：

- 接收 ComfyUI 输入
- 提供用户交互入口
- 定义输入输出 Contract
- 将结果映射为 ComfyUI 类型

节点不会由 Skill 动态生成。

## Skill Resolver

负责 Node 与 Skill 的绑定关系。

支持两种模式：

### Fixed Skill Binding

适合普通用户和高频能力。

例如：

```
Ryan Video Prompt Agent
        |
        v
video_prompt_generator
```

用户无需选择 Skill。

### User Selectable Skill

适合高级用户。

例如：

```
Ryan ACP Universal Agent
        |
        v
用户选择 Skill:
- video_prompt_generator
- storyboard_director
- image_analyzer
```

两种模式共用同一个 Runtime，不存在两套执行链。

## Node Manifest

负责描述固定节点如何调用 Skill。

负责：

- 绑定默认 Skill ID
- 定义是否允许用户选择 Skill
- 定义 ComfyUI 输入
- 定义 Context Template
- 定义输出 Contract
- 定义结果映射

不负责生成 ComfyUI Node。

## Context Template

只负责输入上下文封装。

不负责：

- Skill 专业规则
- 系统 Prompt
- Agent 行为

示例：

```
读取 Skill:
{skill_directory}

用户输入:
{input.text}

参考文件:
{input.images}

请执行当前 Skill。

输出必须符合当前 Node Output Contract。
```

## ACP Runtime

负责：

- Session 创建
- Workspace 管理
- CLI 调用
- stdout/stderr 收集
- 结果解析

## 4. Session 设计

默认永久保留。

目录：

```
output/acp_workspace/
  sessions/
    session_xxx/
      input/
      output/
      logs/
      metadata.json
      context.json
```

## 5. 文件传递

ComfyUI IMAGE / IMAGE Batch 不直接传给 Agent。

流程：

```
IMAGE Tensor
   |
   v
workspace/input
   |
   v
文件路径
   |
   v
Claude/Codex
```

## 6. Skill 调用流程

1. Agent Adapter Node 接收 ComfyUI 输入。
2. Skill Resolver 确定 Skill（固定绑定或用户选择）。
3. 创建 ACP Session。
4. 保存图片/文件资源。
5. 加载 Skill 目录。
6. 加载 Context Template。
7. 生成 Agent Context。
8. 调用 Claude/Codex CLI。
9. 根据 Node Output Contract 解析结果。
10. 输出 ComfyUI 类型。

## 7. 后续待设计

- Node Manifest Schema
- Skill Binding Runtime
- Context Template Engine
- Output Parser
- ACP Profile Schema
- Claude/Codex CLI 参数适配
- Skill Registry
