# Workflow Agent 内容合同实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变 Ryan Workflow Agent 原有 ComfyUI DAG、Chat、Commit、Queue 和旧 Workflow 兼容性的前提下，将六类视频创作 Agent 收敛为高专业密度的中文 Canonical 文档，并只暴露真正需要连接生成节点的对象级 Prompt。

**Architecture:** 保留 `response_text` 作为唯一用户可见的中文 Canonical 文档；每次提交最多附带一个 `ryan-artifact` Bundle。Bundle 的 `content.summary/handoff/locks` 用于精简下游 Context，`outputs` 只索引可连接 Prompt。旧 Bundle、旧 shots 和旧字段继续读取归一化，新提交只写 V2 规范字段。

**Tech Stack:** Python 3、dataclasses、JSON Skill Contract、ComfyUI Node API、现有 Vanilla JavaScript 节点扩展、pytest/unittest。

---

## 文件边界

### Skill 与合同

- 修改：`ryan_comfy_utils/acp/fixtures/skills/creative-story-planner/SKILL.md`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/creative-story-planner/agent-contract.json`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/production-designer/SKILL.md`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/production-designer/agent-contract.json`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/script-director/SKILL.md`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/script-director/agent-contract.json`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/storyboard-director/SKILL.md`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/storyboard-director/agent-contract.json`
- 新增：`ryan_comfy_utils/acp/fixtures/skills/audio-director/SKILL.md`
- 新增：`ryan_comfy_utils/acp/fixtures/skills/audio-director/agent-contract.json`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/video-prompt-director/SKILL.md`
- 修改：`ryan_comfy_utils/acp/fixtures/skills/video-prompt-director/agent-contract.json`

每个 Skill 只描述该阶段必须落地的中文文档和按需 Prompt，不要求模型输出思考过程、英文版本、Review 文件或独立 Handoff 文件。

### Runtime

- 修改：`ryan_comfy_utils/workflow_agent/artifacts.py`：Artifact Bundle V2、Prompt 元数据、旧字段读取归一化。
- 修改：`ryan_comfy_utils/workflow_agent/context_select.py`：默认只渲染 `summary/handoff/locks`，选中时才渲染完整 Prompt。
- 修改：`ryan_comfy_utils/workflow_agent/commit_service.py`：向模型注入统一中文产物规则和 V2 Bundle 合同；保持旧提交读取兼容。
- 修改：`ryan_comfy_utils/workflow_agent/skill_contract.py`：允许无 Prompt 的 `script_direction` Bundle 和新 `audio.design` 合同。
- 修改：`ryan_comfy_utils/nodes/artifact_selector_node.py`：增加按 `purpose`、对象标签和 Segment 的确定性选择，保留旧 kind 别名。
- 修改：`ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`：显示中文 Agent 名称、Prompt 用途、对象/Segment；不显示内部 ID 文本框。
- 按需修改：`ryan_comfy_utils/nodes/workflow_agent_node.py`：若节点输出索引需要新增 Audio/Bundle 字段，只追加，不重排现有输出。

### 测试

- 修改：`tests/workflow_agent/test_artifacts.py`
- 修改：`tests/workflow_agent/test_context_view.py`
- 修改：`tests/workflow_agent/test_chat_commit.py`
- 修改：`tests/workflow_agent/test_context.py`
- 修改：`tests/nodes/test_artifact_selector_node.py`
- 修改：`tests/nodes/test_workflow_agent_node.py`
- 新增或修改：`tests/workflow_agent/test_skill_contracts.py`（若现有合同测试位置不同，以现有测试结构为准）

---

### Task 1: 固化六类 Skill 的最小中文输出

**Files:** 见“Skill 与合同”列表。

- [ ] **Step 1: 更新六份 agent-contract.json**

写入以下稳定映射：

```json
{
  "schema_version": 2,
  "display_name": "阶段中文名称",
  "produces_context_kind": "阶段 kind",
  "artifact_type": "阶段 artifact type",
  "artifact_output_kinds": ["仅允许的 Prompt kind"],
  "language": "zh-CN",
  "canonical_document_only": true
}
```

具体映射：

```text
creative-story-planner → creative.story / creative_story / concept_image_prompt
production-designer    → production.design / production_design / image_prompt
script-director       → script.direction / script_direction / []
storyboard-director   → storyboard.plan / storyboard_plan / storyboard_prompt,keyframe_prompt
audio-director        → audio.design / audio_design / audio_prompt
video-prompt-director→ video.prompts / video_prompts / video_prompt
```

`script-direction` 的 Bundle 允许 `outputs: []`；`audio-director` 是新增的第六类 Agent，不改变旧五类节点的顺序。

- [ ] **Step 2: 重写每个 SKILL.md 的输出规则**

每个 Skill 的末尾必须明确：

```text
只输出一份中文 Canonical Markdown 文档。
不输出思考过程、候选淘汰、工具调用、英文版本、独立 Review 或独立 Handoff 文件。
如确实需要连接生成节点，只在同一个回复末尾追加一个 ryan-artifact JSON block。
没有可连接 Prompt 时使用 outputs: []、shots: []。
```

分别固定六类文档章节：

```text
创意：项目意图、故事核心、角色功能、Story Beats、节奏、必须保留/避免、视觉方向、下游交接
美术：统一视觉语言、角色锁、场景锁、道具锁、资产复用、Continuity、下游交接
剧本：Beat→Scene、场次目标、冲突、对白、可见动作、Blocking、表演、连续性、下游交接
分镜：Scene→Shot→Segment、镜头语言、Blocking、首尾状态、故事板/关键帧需求、下游交接
音频：对白/声音表演、音乐、拟音、环境音、静默点、Segment 音频计划、下游交接
视频：全局执行规则、Segment 时序、表演、镜头、环境、首尾状态、声音执行、避免项、下游交接
```

每份 Skill 都明确“依据类内容不得写成 Prompt”。

- [ ] **Step 3: 为六份 Skill 各写一个最小可执行输出示例**

示例必须是中文，且只展示 Canonical 文档和必要的单个 Bundle；不得展示内部推理。示例中的实体 ID 统一使用 `CHAR_001`、`SCENE_001`、`SHOT_001`、`SEG_001`。

- [ ] **Step 4: 运行合同 JSON 解析测试**

Run: `rtk python -m pytest tests/workflow_agent/test_skill_contracts.py -q`

Expected: 六个合同可加载；剧本允许空 Prompt 列表；音频合同可通过解析。

---

### Task 2: 实现 Artifact Bundle V2 的最小字段

**Files:** `ryan_comfy_utils/workflow_agent/artifacts.py`, `tests/workflow_agent/test_artifacts.py`

- [ ] **Step 1: 写失败测试覆盖 V2 Prompt 元数据**

```python
def test_v2_output_keeps_purpose_target_ids_and_prompt_metadata():
    parsed = parse_artifact_markdown("""正文
```ryan-artifact
{"schema_version":2,"artifact_type":"production_design","content":{"summary":"角色锁","handoff":"交给分镜","locks":["CHAR_001"]},"outputs":[{"output_id":"CHAR_001_REFERENCE","kind":"image_prompt","label":"CHAR_001 · 角色说明书板","purpose":"character_sheet","target_ids":["CHAR_001"],"text":"中文角色参考图 Prompt","negative_constraints":["不要海报构图"],"aspect_ratio":"4:3","priority":50}],"shots":[]}
```""")
    assert parsed.status == "valid"
    output = parsed.bundle.outputs[0]
    assert output.purpose == "character_sheet"
    assert output.target_ids == ["CHAR_001"]
    assert output.text == "中文角色参考图 Prompt"
```

同时写入失败用例：缺 `purpose`、缺 `target_ids`、出现 `prompt_en`、重复 `output_id`、脚本空 outputs 合法。

- [ ] **Step 2: 扩展 RyanArtifactOutput 的最小字段**

新增字段：

```python
purpose: str
target_ids: list[str]
reference_roles: dict[str, list[str]]
negative_constraints: list[str]
aspect_ratio: str
```

字段默认值只能是空值；`text` 仍是唯一 Prompt 正文。所有 ID 通过现有 `validate_id` 校验，列表内容必须可 JSON 序列化。

- [ ] **Step 3: 扩展 RyanArtifactBundle 到 schema_version 2**

允许 `schema_version in {1, 2}`；V1 读取时将 `id → output_id`、`prompt/constraint → text`，并为缺失的 V2 元数据填充兼容默认值。V2 新写出时始终包含 `content.summary`、`content.handoff`、`content.locks`、`outputs`、`shots`。

- [ ] **Step 4: 拒绝双语 Prompt 字段而不拒绝中文中的专业英文词**

如果 output 包含 `prompt_en` 或 `text_en`，返回 `ArtifactParseResult(status="invalid")`；不扫描或禁止 `Shot`、`Segment`、`Blocking` 等专业词。

- [ ] **Step 5: 运行 Artifact 测试**

Run: `rtk python -m pytest tests/workflow_agent/test_artifacts.py -q`

Expected: V1 兼容测试和 V2 元数据测试全部 PASS。

---

### Task 3: 收敛下游 Context，按需传递 Prompt

**Files:** `ryan_comfy_utils/workflow_agent/context_select.py`, `tests/workflow_agent/test_context_view.py`, `tests/workflow_agent/test_context.py`

- [ ] **Step 1: 写失败测试验证默认摘要不包含 Prompt 正文**

```python
def test_summary_view_contains_handoff_and_locks_but_not_unselected_prompt():
    view = render_context_view(context, ["production.design"], mode="summary")
    assert "角色锁" in view
    assert "交给分镜" in view
    assert "中文角色参考图 Prompt" not in view
```

- [ ] **Step 2: 修改 artifact_summary**

Bundle 有效时，只按固定顺序拼接：

```text
摘要：{content.summary}
下游交接：{content.handoff}
已确认锁：{content.locks}
```

对每段应用现有 `summary_limit`；Bundle 无效时保留旧 Entry summary/content 回退，不伪造结构化字段。

- [ ] **Step 3: 保留 selected 模式的精确 Prompt 输出**

当 `selected_output_ids` 命中时，渲染 `label / kind / purpose / target_ids / text`；未选中的 output 不得进入输出。旧 shots 选择逻辑保持不变。

- [ ] **Step 4: 运行上下文测试**

Run: `rtk python -m pytest tests/workflow_agent/test_context_view.py tests/workflow_agent/test_context.py -q`

Expected: 默认摘要不膨胀，精确选择仍可取得 Prompt，旧无 Bundle 回退不变。

---

### Task 4: 统一 Commit Prompt 与阶段合同

**Files:** `ryan_comfy_utils/workflow_agent/commit_service.py`, `ryan_comfy_utils/workflow_agent/skill_contract.py`, `tests/workflow_agent/test_chat_commit.py`

- [ ] **Step 1: 写失败测试验证 Commit 指令只允许一个中文 Canonical 文档**

测试 `_prompt()` 包含：

```text
只输出一份中文 Canonical Markdown 文档
不输出内部思考、工具调用、英文版本、独立 Review、独立 Handoff
依据类内容不要生成 Prompt
最多追加一个 ryan-artifact block
```

并验证剧本合同包含 `outputs: []` 规则。

- [ ] **Step 2: 替换旧 V1 示例 JSON**

`commit_service._prompt()` 的 Artifact 规则改为 V2 最小形式：`content.summary/handoff/locks`、`outputs`、`shots`。Prompt output 必须使用 `text`、`purpose`、`target_ids`；不得使用 `prompt_en`。

- [ ] **Step 3: 保持 Commit 读取兼容，不把无效 Bundle 伪造成有效 Bundle**

V1/V2 解析有效时写入 `metadata.artifact_bundle`；无效时保留 Canonical 文本并记录 `artifact_status=invalid` 与错误。只有有效 Bundle 才进入 Selector。

- [ ] **Step 4: 添加 Audio 合同加载**

`load_skill_contract("audio-director", ...)` 返回 `audio.design` 和 `audio_prompt` 允许值；不存在的 Skill 目录报现有类型错误，不增加隐式回退。

- [ ] **Step 5: 运行 Commit 测试**

Run: `rtk python -m pytest tests/workflow_agent/test_chat_commit.py -q`

Expected: Commit Prompt 新合同断言通过，旧 Commit 读取和无效 Bundle 行为不回归。

---

### Task 5: 改造 Selector 的语义映射

**Files:** `ryan_comfy_utils/nodes/artifact_selector_node.py`, `ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`, `tests/nodes/test_artifact_selector_node.py`

- [ ] **Step 1: 写失败测试覆盖六类 Prompt 选择**

覆盖：

```text
concept_image_prompt → 创意概念图
image_prompt + purpose → 角色/场景/道具/空间参考图
storyboard_prompt → 控制/风格故事板
keyframe_prompt → start_frame/end_frame/reference_frame
 audio_prompt → music/voice/foley/ambience
video_prompt + target_ids=[SEG_001] → SEG_001 视频 Prompt
script_direction → 无可选 Prompt，不发生正文伪造
```

- [ ] **Step 2: 增加 purpose/target_ids 过滤**

普通模式使用用户语义选择；精确模式可按来源 Agent、Prompt 用途、对象/Segment 和版本选择。内部字段继续支持旧 Widget 输入，但不新增可见 ID 输入。

- [ ] **Step 3: 保持旧 kind 别名**

读取时将 `storyboard_sheet_prompt`、`shot_prompt`、`shot_video_prompt` 映射到兼容候选；新 V2 Prompt 优先级更高。没有匹配时返回空字符串和已有状态提示。

- [ ] **Step 4: 更新前端可读选项**

显示中文：

```text
来源 Agent · Prompt 类型 · 对象/Segment · 用途
```

不显示 `source_agent_uid`、`output_id`、`shot_id`、裸 `kind` 或 revision 文本框。

- [ ] **Step 5: 运行 Selector 测试和语法检查**

Run: `rtk python -m pytest tests/nodes/test_artifact_selector_node.py -q`

Run: `rtk node --check ryan_comfy_utils/web/workflow_agent/artifact_selector_extension.js`

Expected: 语义选择、无匹配、旧字段兼容全部 PASS；JavaScript 语法检查通过。

---

### Task 6: 固定跨 Agent 回归 Fixture 并执行链路 Smoke

**Files:** `tests/workflow_agent/fixtures/`（若现有 Fixture 目录不存在则放入对应现有测试文件的常量）、`tests/workflow_agent/test_context_view.py`, `tests/workflow_agent/test_chat_commit.py`, `tests/nodes/test_workflow_agent_node.py`

- [ ] **Step 1: 建立一个六阶段最小 Fixture**

Fixture 只包含：

```text
creative.story → production.design → script.direction → storyboard.plan → audio.design → video.prompts
```

每阶段一份 Canonical 文档、一个 summary/handoff/locks 元数据；只给美术一个角色 Prompt、分镜一个关键帧 Prompt、视频一个 `SEG_001` Prompt。不要把全部 Prompt 拼到上下文。

- [ ] **Step 2: 写跨阶段断言**

断言：

```text
默认下游 Context 包含上游锁和交接，不包含未选 Prompt
Selector 能取 CHAR_001、SHOT_001、SEG_001 对应 Prompt
剧本 Agent 无 Prompt 候选
所有正文为中文，可包含 Blocking/Shot/Segment 等专业词
```

- [ ] **Step 3: 运行模块回归测试**

Run: `rtk python -m pytest tests/workflow_agent tests/nodes/test_artifact_selector_node.py tests/nodes/test_workflow_agent_node.py -q`

Expected: 现有测试和新增合同测试全部 PASS。

- [ ] **Step 4: 运行语法与导入检查**

Run: `rtk python -m compileall -q ryan_comfy_utils`

Expected: 无 Python 语法或导入编译错误。

- [ ] **Step 5: 运行最小 Queue/Selector Smoke**

使用测试中的内存 Repository 和固定 Context，执行：

```text
Commit 六阶段 Fixture
→ 生成 RYAN_CONTEXT
→ 默认 Context View
→ Selector 选择 SEG_001
→ 断言输出只等于 SEG_001 视频 Prompt
```

Expected：Selector 不返回整篇 Canon、不返回其它 Segment、不返回内部思考文本。

---

## 完成检查

- [ ] 六类 Skill 合同与输出规则一致。
- [ ] 每个 Agent 只有一份中文 Canonical 文档。
- [ ] Prompt 只存在于必要的对象级 Bundle output。
- [ ] 默认上下文不传递全部 Prompt 和全文。
- [ ] Selector 能按用途和对象精确取 Prompt。
- [ ] V1 Bundle、旧 shots、旧字段和旧 Workflow 兼容。
- [ ] 测试、编译和 Queue/Selector Smoke 全部通过。
