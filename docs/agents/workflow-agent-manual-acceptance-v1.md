# Ryan Workflow Agent V1 浏览器人工验收说明

> 目的：验证 Generic Workflow Agent 的节点身份、Skill 语义、动态输入和 ComfyUI Canvas 兼容性。
> 适用版本：2026-08-10 之后的 V1 实现。
> 自动化测试不能替代本说明中的浏览器手测；浏览器验收由运行 ComfyUI 的使用者执行。

## 1. 测试前提

1. 从项目根目录启动 ComfyUI。
2. 确认 `Ryan Workflow Agent` 出现在 `Ryan Utils / Agent` 分类。
3. 修改前端文件后重启 ComfyUI，或使用浏览器强制刷新，确保加载最新 `node_extension.js`。
4. 新建空白 Workflow，避免旧节点实例的前端状态干扰结果。

## 2. 新建节点与身份

### 操作

1. 新增一个 `Ryan Workflow Agent` 节点。
2. 观察节点控件和底部状态文字。
3. 再新增第二个同类节点。
4. 分别点击两个节点的 `Open Chat`。
5. 关闭并重新打开 Workflow。

### 预期

- 节点可创建，不抛出浏览器异常。
- 节点包含 `Skill`、`Agent Name`、`Context Slots`、`Image Slots`、`Update Inputs`、`Open Chat`。
- `workflow_id`、`agent_uid` 不作为普通用户配置项显示。
- 同一 Workflow 的两个节点拥有相同 `workflow_id`，但 `agent_uid` 不同。
- 两个节点的 Chat Workspace 身份不串线。
- 重开 Workflow 后身份保持不变，Session 仍按 `workflow_id + agent_uid` 隔离。
- 节点初始状态显示 `Not started` 或中文等价状态。

## 3. Skill 与 Agent Name

### 操作

1. 新节点保持默认 Skill，记录 Agent Name。
2. 将 Skill 切换为 `production-designer`。
3. 将 Agent Name 手工改为 `我的资产 Agent`。
4. 再切换 Skill 为 `script-director`。

### 预期

- 默认 Skill 对应默认名称，例如 `creative-story-planner` 显示 `创意策划`。
- 切换 Skill 且 Agent Name 尚未手工修改时，名称同步为新 Skill 的推荐名称。
- 手工改名后，后续切换 Skill 不覆盖 `我的资产 Agent`。
- 节点与右侧 Workspace 使用同一个 Agent Name。

## 4. Context / Image 动态输入

### 操作

1. 将 `Context Slots` 设为 `3`，点击 `Update Inputs`。
2. 将 `Image Slots` 设为 `2`，点击 `Update Inputs`。
3. 将两个数量都设为 `0`，点击 `Update Inputs`。
4. 新建一个上游 Agent，并把它连接到下游节点的 `context_08`。
5. 将下游 `Context Slots` 设为 `1`，点击 `Update Inputs`。
6. 保存并重新打开 Workflow，检查连线。

### 预期

- 数量为 `3` 时，未连接的 `context_01`~`context_03` 可见，高位未连接槽隐藏。
- 数量为 `2` 时，未连接的 `image_01`~`image_02` 可见，高位未连接槽隐藏。
- 数量为 `0` 时，未连接的 Context / Image 槽可隐藏，但节点仍可正常使用。
- 已连接的 `context_08` 即使数量设置为 `1` 也保持可见，连线不丢失。
- 保存、重开后 `context_08` 连线仍存在。
- `Update Inputs` 不重建 Socket，不造成其他连线迁移或丢失。

## 5. Workspace 与 Canvas 兼容

### 操作

1. 在 Canvas 上拖动节点、平移画布、缩放画布。
2. 连接和断开 Context 连线。
3. 点击节点 `Open Chat` 或双击节点。
4. 调整右侧 Workspace 宽度，关闭，再通过节点重新打开。
5. 放置 5 个 Agent 节点并在它们之间建立串行或 fan-in 连线。

### 预期

- 节点仍可拖动、连线、框选，Canvas 缩放和平移不被 Panel 截断。
- 打开 Workspace 不触发全局 Queue。
- Panel 可打开、关闭、恢复；关闭后 Canvas 不残留浮层。
- Panel 调整宽度后刷新仍使用保存的宽度。
- 多 Agent 切换时 Draft 不串到其他 Agent。
- fan-in 显示实际来源 Agent 名称，不只显示 `context_01`。

## 6. Commit / 状态同步

如果本地 Pi Provider 已配置，继续执行以下验证：

1. 在 Workspace 发送一条普通消息。
2. 确认消息只进入当前 Agent Private Chat。
3. 修改 Draft 后点击 `确认并提交`。
4. 观察节点 revision、Workspace Commit 状态和下游 Context。
5. 修改上游 Agent 并再次 Commit。

预期：

- 普通发送不触发 ComfyUI 全局 Queue。
- Commit 前，下游看不到当前 Draft。
- Commit 成功后 revision 增加，节点和 Workspace 同步显示。
- 上游产生新 Commit 后，下游显示 `上游已更新`，但不自动覆盖现有 Draft / Commit。
- Stop 只停止当前 Agent 的生成请求。

## 7. Save As / 复制隔离

### 操作

1. 在 Workflow A 创建两个 Agent 并打开过各自 Workspace。
2. 使用 ComfyUI `Save As` 保存为 Workflow B。
3. 在 Workflow B 修改其中一个 Agent 的 Skill 或发送消息。
4. 返回 Workflow A 检查状态。
5. 在同一 Workflow 内复制一个 Agent 节点。

### 预期

- Workflow B 生成新的 `workflow_id`，不继续写入 Workflow A 的 Session / Commit。
- Workflow B 的 Agent 状态不会覆盖 Workflow A。
- 同一 Workflow 内复制节点获得新的 `agent_uid`，不会复用原节点 Session。

## 8. 问题回报格式

请提供：

```text
环境：ComfyUI 地址 / 浏览器 / 窗口宽度 / 缩放比例
Workflow：新建、加载、Save As 或复制
步骤：1. ... 2. ... 3. ...
实际结果：
预期结果：
浏览器 Console 错误：完整文本或截图
节点截图：包含输入槽、连线和右侧 Panel
```

优先回报以下阻断问题：

- 节点无法创建或 `Open Chat` 无反应；
- 两个节点的 `workflow_id` / `agent_uid` 串线；
- 动态输入导致已有连线丢失；
- Save As 后两个 Workflow 共享 Session；
- Panel 破坏拖动、连线、缩放或键盘操作。
