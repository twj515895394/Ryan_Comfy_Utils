Status: ready-for-agent

# Commit 产物兼容与 Selector 展示

## 目标

修正 Ryan Workflow Agent 的 Commit 产物与 Artifact Selector 之间的结构化数据合同，使已有旧格式产物和新 Commit 产物都能稳定提供图像、分镜、视频和镜头提示词。

## 背景

当前真实 Workflow 的 Commit 产物出现两类问题：

- 使用 `id`、`prompt`、`constraint` 等旧字段，解析时被判定为 `invalid`。
- 部分 Agent 没有 `ryan-artifact` 区块，被判定为 `absent`。

Selector 需要规范化的 `output_id`、`kind`、`label`、`text`，以及镜头用 `shot_id`、`kind`、`label`、`prompt`。

## 用户故事

1. 用户不需要重建整个 Agent Workflow，已有 Commit 产物可以继续被 Selector 使用。
2. 用户点击 Commit 后，新产物不再因为字段名称不一致而 invalid。
3. 用户只通过语义选项筛选图像、分镜、视频和指定镜头提示词。
4. 没有结构化产物时，Selector 自动模式仍能展示最新正文，并明确提示原因。

## 非目标

- 不改变 Agent Chat、Commit、Context 的基本交互。
- 不引入新的数据库或外部服务。
- 不要求用户理解 UID、Bundle schema、kind 或 revision。
