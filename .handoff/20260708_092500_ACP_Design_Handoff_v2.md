# Ryan_Comfy_Utils ACP Design Handoff v2

更新时间：2026-07-08

## 1. 当前项目目标

Ryan_Comfy_Utils 是 ComfyUI 通用增强节点集合，目标不是简单增加节点，而是建立 ComfyUI 与 Agent 能力之间的桥接层。

核心方向：

- ComfyUI 负责工作流编排和用户交互。
- Skill 负责 Agent 能力资产。
- ACP 负责连接本地 Claude CLI / Codex CLI。

---

# 2. 已确认架构原则

## 2.1 Skill 与 ComfyUI Node 解耦

Skill 是独立 Agent 能力资产。

负责：

- instructions
- 专业规则
- Agent 行为约束
- 示例和参考资料

不负责：

- ComfyUI 输入输出
- IMAGE / STRING 类型
- 节点定义

---

## 2.2 ACP Runtime 定位

ACP 不是 Skill。

ACP 是 Agent Runtime 执行层。

负责：

- Claude CLI 调用
- Codex CLI 调用
- Session 管理
- Workspace 管理
- 输入文件传递
- stdout/stderr 收集
- 结果解析

---

# 3. 最终调用链

```
ComfyUI Agent Node
        |
        v
Skill Resolver
        |
        v
Context Builder
        |
        v
ACP Session
        |
        v
Claude CLI / Codex CLI
        |
        v
Skill Repository
        |
        v
Result Parser
        |
        v
ComfyUI Output
```

---

# 4. Node 设计

## Node 不动态生成

明确不采用：

```
Skill -> 自动生成 ComfyUI Node
```

原因：

- Workflow 需要稳定节点结构。
- Skill 数量增长不应该导致节点爆炸。
- Node 和 Skill 生命周期不同。

---

## Node 模式

支持两种模式。

## 4.1 Fixed Skill Binding

普通用户使用。

例如：

```
Ryan Video Prompt Agent
        |
        v
video_prompt_generator
```

用户无需选择 Skill。

---

## 4.2 User Selectable Skill

高级用户使用。

例如：

```
Ryan ACP Universal Agent

Skill Selector:
- video_prompt_generator
- storyboard_director
- image_analyzer
```

两者共用同一个 Runtime，不存在两套执行链。

---

# 5. Context Template 设计

Context Template 只负责上下文封装。

负责：

- 输入参数注入
- 文件路径引用
- 简单上下文组织

不负责：

- 系统 Prompt
- 专业规则
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

---

# 6. Skill 调用方式

执行时：

1. Node 确定 Skill（固定绑定或用户选择）。
2. 创建 ACP Session。
3. 创建 workspace。
4. IMAGE / Video Frame 等资源保存到 session/input。
5. 加载 Skill Directory。
6. 加载 Context Template。
7. 构建 Agent Context。
8. 调用 Claude/Codex CLI。
9. 按 Output Contract 解析结果。
10. 返回 ComfyUI 输出。

---

# 7. ACP Session

设计：

一次节点执行：

```
一次 ComfyUI Node 执行
=
一次 ACP Session
=
一次 CLI 调用
```

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

默认永久保留。

未来支持 cleanup 配置。

---

# 8. 当前已完成

## 文档

- ACP Runtime Architecture Design v1
- ACP Architecture Decision Record
- ACP 流程设计图

## 第一版节点

已完成方向：

- ComfyUI 通用工具节点
- 视频批量加载增强设计
- Video Frame Sampler 设计
- OpenAI Compatible LLM 节点设计

## ACP 架构

已完成：

- Runtime 定位
- Session 隔离方案
- Skill 解耦方案
- Node Binding 模型

---

# 9. 待设计任务

## P0 架构协议

### Node Manifest Schema

需要定义：

- Node ID
- Skill ID
- Fixed / Selectable 模式
- Context Template
- Input Contract
- Output Contract
- Result Mapping

---

### ACP Profile Schema

需要定义：

Claude CLI / Codex CLI：

- command
- workspace
- timeout
- environment

---

### ACP Context 协议

定义：

- text 输入
- image 输入
- file 输入
- workspace 信息
- skill 信息

---

## P1 Runtime 开发

- Skill Loader
- Skill Registry
- Context Builder
- Context Template Engine
- Result Parser
- Session Manager
- Workspace Manager

---

## P2 节点扩展

固定 Agent Node：

- Ryan ACP Universal Agent
- Ryan Video Prompt Agent
- Ryan Storyboard Agent
- Ryan Image Analyze Agent
- Ryan Character Design Agent
- Ryan File Generator Agent

---

# 10. 下一步建议

优先继续设计：

1. Node Manifest Schema
2. ACP Context 数据结构
3. Result Parser 协议
4. ACP Profile Schema

确定协议后再进入代码实现。
