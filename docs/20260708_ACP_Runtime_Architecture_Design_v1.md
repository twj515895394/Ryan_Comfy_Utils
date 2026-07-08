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
Skill Adapter Node
        |
        v
Node Manifest
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
Skill
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

### Node Manifest

负责 ComfyUI 适配契约。

负责：

- 绑定 Skill ID
- 定义 ComfyUI 输入
- 定义 Context Template
- 定义输出 Contract
- 定义结果映射

### Context Template

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
```

### ACP Runtime

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

1. Node 接收 ComfyUI 输入。
2. 创建 ACP Session。
3. 保存图片/文件资源。
4. 加载 Skill 目录。
5. 加载 Context Template。
6. 生成 Agent Context。
7. 调用 Claude/Codex CLI。
8. 根据 Node Output Contract 解析结果。
9. 输出 ComfyUI 类型。

## 7. 后续待设计

- Node Manifest Schema
- Dynamic Node Engine
- Context Template Engine
- Output Parser
- ACP Profile Schema
- Claude/Codex CLI 参数适配
- Skill Registry
