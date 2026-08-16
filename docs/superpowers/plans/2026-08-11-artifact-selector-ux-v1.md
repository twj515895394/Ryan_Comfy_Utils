# Artifact Selector UX V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `Ryan Artifact Selector` 改为“默认自动取上游最新产物 + 可选精确选择”的低认知负担界面，让用户无需理解 UID、Artifact Bundle schema 或 `kind` 即可完成选择。

**Architecture:** 保留 Python 节点的确定性 Artifact Bundle 查询逻辑，并继续接受旧的精确字段。前端始终隐藏内部字段，普通模式提供语义选择，精确模式提供仅显示名称/标签/“第 N 版”的动态下拉；无 Context、未 Queue、未 Commit 和无结构化产物时显示下一步提示。Workflow Agent 的 Queue/Context 合同不改动。

**Tech Stack:** Python `unittest`、ComfyUI node `INPUT_TYPES` / `widgets_values`、LiteGraph node widgets、原生 JavaScript、现有 `RYAN_CONTEXT` 和 Artifact Bundle 模型。

---

## 文件边界

- Modify: `ryan_comfy_utils/nodes/artifact_selector_node.py`
  - 增加普通模式语义参数和确定性语义到内部过滤条件的映射。
  - 保留旧字段的读取能力；不修改 Artifact Bundle 合同。
- Modify: `tests/nodes/test_artifact_selector_node.py`
  - 覆盖语义映射、空状态、无匹配和旧字段兼容。
- Create: `ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`
  - 只负责 Artifact Selector 的节点 UI、普通/高级模式和动态选项。
- Modify: `ryan_comfy_utils/web/workflow_agent/index.js:1-7`
  - 导入新的节点扩展，确保 ComfyUI 加载它。
- Modify: `ryan_comfy_utils/web/workflow_agent/node_extension.js:303-312`
  - 在已有 Context 事件中加入来源节点 ID，避免多个 Selector 在同一 Workflow 中互相刷新。
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js:67-88`
  - 增加高级切换、空状态和无匹配状态的紧凑样式。
- Modify: `.planning/tasks/artifact-selector-ux-v1/task_plan.md`
  - 记录阶段状态和验证结果。
- Modify: `.planning/tasks/artifact-selector-ux-v1/progress.md`
  - 记录实现过程和测试结果。

## 数据合同

保留当前六个兼容字段：

```text
source_agent_uid, artifact_type, output_id, shot_id, kind, revision
```

新增四个用户级字段，追加在旧字段之后，避免旧 Workflow 的 `widgets_values` 按位置错位：

```text
selection, source_agent, shot_scope, shot
```

Python 节点的 `run()` 同时接收新旧字段。前端把用户可读选项映射回旧字段；如果前端没有可用映射，Python 仍按旧字段执行。

语义值固定为：

```text
selection: auto | image_prompt | storyboard_prompt | video_prompt | first_output | shot_prompt
source_agent: auto 或 Context 中来源 Agent 的显示值
shot_scope: all | selected
shot: auto 或 Context 中 shot 的显示值
```

前端显示中文标签，内部保存稳定语义值或映射后的内部 ID；禁止依赖用户手输 ID。

---

### Task 1: 增加 Python 语义选择合同

**Files:**
- Modify: `ryan_comfy_utils/nodes/artifact_selector_node.py:15-114`
- Test: `tests/nodes/test_artifact_selector_node.py:35-50`

- [ ] **Step 1: 写失败测试，锁定语义选择行为**

在 `TestArtifactSelectorNode` 增加以下行为测试：

```python
def test_selects_image_prompt_by_semantic_selection(self):
    result = RyanArtifactSelector().run(
        context=self._context(), selection="image_prompt"
    )
    self.assertEqual(result, ("IMAGE",))

def test_selects_selected_shot_by_semantic_selection(self):
    result = RyanArtifactSelector().run(
        context=self._context(), selection="shot_prompt", shot_id="shot_01"
    )
    self.assertEqual(result, ("SHOT",))

def test_semantic_selection_never_falls_back_to_entry_body(self):
    result = RyanArtifactSelector().run(
        context=self._context(), selection="video_prompt"
    )
    self.assertEqual(result, ("",))

def test_legacy_internal_fields_still_select_output(self):
    result = RyanArtifactSelector().run(
        context=self._context(), artifact_type="production_design", output_id="image_01"
    )
    self.assertEqual(result, ("IMAGE",))
```

Run:

```bash
rtk python -m unittest tests.nodes.test_artifact_selector_node.TestArtifactSelectorNode -v
```

Expected: the new semantic tests fail before implementation; the four existing tests remain the compatibility baseline.

- [ ] **Step 2: 实现最小语义解析层**

在 `RyanArtifactSelector` 中增加固定映射和解析函数：

```python
_SELECTION_KINDS = {
    "image_prompt": ("image_prompt",),
    "storyboard_prompt": ("storyboard_sheet_prompt", "shot_prompt"),
    "video_prompt": ("video_prompt",),
}

@classmethod
def _select_semantic_text(cls, context, *, selection, source_agent_uid, shot_id, revision):
    if selection == "shot_prompt":
        return cls._select_text(
            context, source_agent_uid=source_agent_uid, artifact_type="",
            output_id="", shot_id=shot_id, kind="shot_prompt", revision=revision,
        )
    for kind in _SELECTION_KINDS.get(selection, ()):
        text = cls._select_text(
            context, source_agent_uid=source_agent_uid, artifact_type="",
            output_id="", shot_id="", kind=kind, revision=revision,
        )
        if text:
            return text
    return ""
```

将 `selection`, `source_agent`, `shot_scope`, `shot` 加入 `run()` 参数。旧的 `output_id` / `shot_id` / `kind` 非空时优先，保证旧 Workflow 的精确选择不被语义默认值覆盖；新语义只在没有旧精确字段时生效。`storyboard_prompt` 必须按 `storyboard_sheet_prompt` 后 `shot_prompt` 的顺序尝试；`shot_scope == "selected"` 时使用 `shot` 映射出的 `shot_id`。

- [ ] **Step 3: 运行节点测试并确认兼容性**

Run:

```bash
rtk python -m unittest tests.nodes.test_artifact_selector_node -v
```

Expected: all existing and new tests pass；无 Context、无 Bundle 和无匹配仍返回 `("",)`。

---

### Task 2: 增加序列化输入并保持旧 Workflow 位置

**Files:**
- Modify: `ryan_comfy_utils/nodes/artifact_selector_node.py:15-27`
- Test: `tests/nodes/test_artifact_selector_node.py:35-60`

- [ ] **Step 1: 固定 INPUT_TYPES 顺序**

保留旧六个字段的顺序，把四个用户字段追加在末尾：

```python
"required": {
    "source_agent_uid": ("STRING", {"default": ""}),
    "artifact_type": ("STRING", {"default": ""}),
    "output_id": ("STRING", {"default": ""}),
    "shot_id": ("STRING", {"default": ""}),
    "kind": ("STRING", {"default": ""}),
    "revision": ("INT", {"default": 0, "min": 0}),
    "selection": ("STRING", {"default": "auto"}),
    "source_agent": ("STRING", {"default": "auto"}),
    "shot_scope": ("STRING", {"default": "all"}),
    "shot": ("STRING", {"default": "auto"}),
},
```

不要在 Python schema 中使用 `hidden=True` 删除旧 widget；前端通过 `widget.hidden` 隐藏它们，确保旧 `widgets_values` 能够被读取，并可在高级模式复用。

- [ ] **Step 2: 增加输入声明回归测试**

```python
def test_declares_semantic_inputs_after_legacy_inputs(self):
    names = list(RyanArtifactSelector.INPUT_TYPES()["required"])
    self.assertEqual(
        names[:6],
        ["source_agent_uid", "artifact_type", "output_id", "shot_id", "kind", "revision"],
    )
    self.assertEqual(names[6:], ["selection", "source_agent", "shot_scope", "shot"])
```

Run:

```bash
rtk python -m unittest tests.nodes.test_artifact_selector_node -v
```

Expected: schema 顺序和旧字段兼容测试通过。

---

### Task 3: 实现 Artifact Selector 前端两层模式

**Files:**
- Create: `ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`
- Modify: `ryan_comfy_utils/web/workflow_agent/index.js:1-7`
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js:67-88`

- [ ] **Step 1: 建立稳定的节点扩展入口**

新文件导入 `app` 并注册单独扩展，只匹配 `Ryan Artifact Selector`：

```javascript
import { app } from "../../../../scripts/app.js";

const NODE_NAME = "Ryan Artifact Selector";
const LEGACY_FIELDS = ["source_agent_uid", "artifact_type", "output_id", "shot_id", "kind", "revision"];
const BASIC_FIELDS = ["selection", "source_agent", "shot_scope", "shot"];

function findWidget(node, name) {
  return node.widgets?.find((widget) => widget.name === name);
}

app.registerExtension({
  name: "RyanComfyUtils.ArtifactSelector",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;
    nodeType.prototype.onNodeCreated = function () {
      setupSelectorUI(this);
    };
  },
});
```

追加 `index.js` 导入：

```javascript
import "./artifact_selector_extension.js";
```

- [ ] **Step 2: 实现普通模式控件**

将 `selection`、`source_agent`、`shot_scope`、`shot` 的 widget 转为 combo 控件，显示中文语义值：

```javascript
const SELECTION_OPTIONS = [
  "自动选择",
  "图像提示词",
  "分镜提示词",
  "视频提示词",
  "首个结构化产物",
  "指定镜头提示词",
];
const SHOT_SCOPE_OPTIONS = ["全部镜头", "指定镜头"];
```

控件值变化时：

- 将显示值映射到 Python 的稳定语义值；
- 同步内部旧字段 widget；
- 选择非 `指定镜头提示词` 时隐藏或禁用 `shot_scope` / `shot`；
- 每次修改调用 `node.graph?.change?.()` 并重算节点尺寸。

普通模式只显示四个用户字段和 `context` 插槽；六个旧字段默认 `widget.hidden = true`。

- [ ] **Step 3: 实现动态来源与镜头选项**

从 `RYAN_CONTEXT` 构造前端选项：

```javascript
function contextChoices(context) {
  const entries = Array.isArray(context?.entries) ? context.entries : [];
  const sources = [...new Map(entries.map((entry) => [
    entry.source_agent_uid,
    { value: entry.source_agent_uid, label: entry.source_agent_name || entry.source_agent_uid },
  ])).values()];
  const shots = entries.flatMap((entry) => {
    const bundle = entry?.metadata?.artifact_bundle;
    return Array.isArray(bundle?.shots) ? bundle.shots.map((shot) => ({
      value: shot.shot_id,
      label: `${shot.label || shot.shot_id} · ${shot.kind || "shot"}`,
    })) : [];
  });
  return { sources, shots };
}
```

下拉显示 `label`，选中后把对应 `value` 写入 `source_agent_uid` 或 `shot_id`。如果 Context 不存在，显示单个禁用语义项 `首次运行后可选择上游产物`，不阻塞普通模式。

- [ ] **Step 4: 实现精确模式**

增加一个“精确选择” button。点击后：

- 仍隐藏六个 legacy widget，不把内部字段名称暴露给用户；
- 增加/复用仅显示用户可读标签的动态下拉：来源 Agent、产物类型、输出、镜头、类型过滤、版本；
- 选项显示 Agent 名称、产物 label、`label · 类型` 和“第 N 版”，内部 widget value 保存稳定 ID；
- 精确模式启用时，普通语义字段不覆盖精确字段；
- 再次点击收起精确控件，不清空已选值；
- Context 更新导致当前值失效时回到“自动选择”，并显示“上游产物已更新，已恢复自动选择”。

- [ ] **Step 5: 增加 Context 来源节点匹配**

修改 `node_extension.js` 的 Context 事件 detail：

```javascript
detail: {
  nodeId: node.id,
  workflowId: ...,
  agentUid: ...,
  context: this._ryanContext,
}
```

Artifact Selector 监听 `ryan-workflow-agent-context`，只处理 `context` 输入连线的 origin node ID 等于 `detail.nodeId` 的事件；这样同一 Workflow 中多个 Selector 不会互相刷新。

- [ ] **Step 6: 增加空状态和无匹配状态样式**

在 `styles.js` 增加：

```css
.ryan-artifact-selector__advanced { margin-top: 6px; }
.ryan-artifact-selector__empty { color: var(--ryan-text-secondary); font-size: 10px; }
.ryan-artifact-selector__error { color: var(--ryan-error); font-size: 10px; }
```

节点 UI 状态只使用已有颜色变量，不引入新依赖或大面积节点重绘。

---

### Task 4: 补齐选择语义和兼容回归

**Files:**
- Modify: `tests/nodes/test_artifact_selector_node.py:1-70`
- Modify: `ryan_comfy_utils/nodes/artifact_selector_node.py:35-114`

- [ ] **Step 1: 覆盖全部普通语义**

使用带 `image_prompt`、`storyboard_sheet_prompt`、`video_prompt` 和 shots 的 Context，断言：

```python
selection="image_prompt"      -> image output text
selection="storyboard_prompt" -> storyboard output text
selection="video_prompt"      -> video output text
selection="first_output"      -> lowest priority output/shot
selection="shot_prompt"       -> selected shot text
selection="auto"              -> existing deterministic first candidate
```

- [ ] **Step 2: 覆盖边界和异常**

测试以下可观察合同：

```python
RyanArtifactSelector().run()                                      == ("",)
run(context_without_bundle, selection="image_prompt")            == ("",)
run(context_with_bundle, selection="video_prompt")               == ("",)  # no video output
run(context_with_bundle, shot_scope="selected", shot="missing") == ("",)
run(context_with_bundle, output_id="image_01")                   == ("IMAGE",)  # legacy precedence
```

- [ ] **Step 3: 运行节点测试**

Run:

```bash
rtk python -m unittest tests.nodes.test_artifact_selector_node -v
```

Expected: all semantic, empty-state, no-fallback and legacy compatibility tests pass。

---

### Task 5: 前端静态验证与任务文档

**Files:**
- Modify: `ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`
- Modify: `ryan_comfy_utils/web/workflow_agent/index.js`
- Modify: `ryan_comfy_utils/web/workflow_agent/node_extension.js`
- Modify: `ryan_comfy_utils/web/workflow_agent/styles.js`
- Modify: `.planning/tasks/artifact-selector-ux-v1/task_plan.md`
- Modify: `.planning/tasks/artifact-selector-ux-v1/progress.md`

- [ ] **Step 1: 运行所有受影响前端语法检查**

Run:

```bash
rtk node --check ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js && rtk node --check ryan_comfy_utils/web/workflow_agent/index.js && rtk node --check ryan_comfy_utils/web/workflow_agent/node_extension.js && rtk node --check ryan_comfy_utils/web/workflow_agent/styles.js
```

Expected: all commands exit with code 0。

- [ ] **Step 2: 运行 Python 节点回归和语法检查**

Run:

```bash
rtk python -m unittest tests.nodes.test_artifact_selector_node tests.nodes.test_workflow_agent_node -q
rtk python -m py_compile ryan_comfy_utils/nodes/artifact_selector_node.py
```

Expected: all tests pass and `py_compile` exits with code 0。

- [ ] **Step 3: 更新规划文件**

在 `task_plan.md` 将实现计划阶段标为 complete，并记录测试命令；在 `progress.md` 记录新增文件、兼容策略和静态验证结果。若完整 ComfyUI UI 未启动，明确记录这是人工验收剩余项，不标记为已验证。

---

## 验收顺序

1. 加载旧 Workflow，确认旧字段仍能执行。
2. 新建 Artifact Selector，确认普通视图只出现 `来源 Agent / 产物类型 / 镜头范围 / 镜头`。
3. 先不 Queue 上游，确认普通模式显示首次运行提示但不阻塞。
4. Queue 一个 Workflow Agent，确认连接的 Selector 动态出现来源和 shots 下拉。
5. 选择图像、分镜、视频语义，确认下游分别收到对应文本。
6. 选择指定镜头，确认下游只收到目标 shot prompt。
7. 展开高级模式，确认任意有效 output/shot 可选且显示 label，不出现手工文本框。
8. 选择不存在或已失效的产物，确认输出空字符串并显示明确状态。
9. 运行 Python 回归和所有受影响 JS `node --check`。

## 不执行的操作

- 不自动启动浏览器或 ComfyUI；项目 AGENTS 规则要求 UI 验收需用户明确要求。
- 不执行 Git commit；当前用户确认了设计和规格，但未授权提交代码。
- 不改动 Artifact Bundle schema、Workflow Agent Chat/Commit API 或其它节点。


## 2026-08-12 实施结果

- A+B 方案已落地：默认 `auto` 优先结构化产物，无 Bundle 时读取最新 active Entry 正文；精确模式只显示可读标签。
- 新增 Queue → Context → Selector 默认正文流转回归测试。
- 通过 35 个受影响 Python 测试、Python `py_compile` 和 4 个受影响前端文件的 `node --check`。
- 未启动 ComfyUI/浏览器，需用户在实际画布重载工作流后完成视觉验收。