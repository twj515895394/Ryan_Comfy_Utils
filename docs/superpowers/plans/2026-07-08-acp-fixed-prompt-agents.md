# ACP 固定 Prompt Agent 实施计划

> **For agentic workers:** 按 issue 顺序领取：`.scratch/acp-runtime-foundation/issues/07-*.md` → `08` → `09`。实现时遵循 `custom/karpathy-guidelines`，测试用 `unittest` + fake CLI（与 Foundation 一致）。

**Goal:** 在 ACP Runtime Foundation 之上，落地首批 2 个固定绑定节点：`Ryan Image Prompt Agent`、`Ryan Video Prompt Agent`，端到端打通 manifest → skill → session → ComfyUI 文本输出。

**Architecture:** 固定节点 `mode: fixed`，`skill_id` 写在 manifest 中；ComfyUI 层复用 `execute_text_session` 与 `map_result_fields`；v1 参考图通过 `image_paths`（多行文件路径字符串）注入 runtime，不引入 ComfyUI `IMAGE` tensor 落盘（后续可增量）。

**Tech Stack:** Python 3.10+, 现有 `ryan_comfy_utils/acp/*`, ComfyUI node API, stdlib `unittest`

**父文档:**

- [选型结论](../../.scratch/acp-runtime-foundation/fixed-agent-node-selection.md)
- [交接说明](../../.handoff/handoff-20260708-170042.md)
- [Foundation 计划](2026-07-08-acp-runtime-foundation.md)

**实现决策（闭合 issue 06 待确认项，可再改）:**

| 决策 | 选择 |
|------|------|
| 首批固定节点 | 仅 Image Prompt + Video Prompt |
| Image 可选字段 | v1 暴露可选 `style` / `subject` / `scene` / `extra_prompt`，写入 context 模板，不单独扩 protocol |
| Video 输入 | `image_paths` 可选；允许纯 `user_text` 驱动 |
| Skill 切分 | 两个独立 skill：`image_prompt_generator`、`video_prompt_generator` |
| Skill 落库 | 仓库内 `ryan_comfy_utils/acp/fixtures/skills/<id>/SKILL.md`，测试与默认可不依赖外部 `skill_root` |
| Analyze / Storyboard / Character / File Generator | 继续仅通过 Universal Agent |

---

## Issue 映射

| Issue | 切片 |
|-------|------|
| 07 | 共享资产 + 固定节点运行辅助 + 双 manifest |
| 08 | `Ryan Image Prompt Agent` ComfyUI 节点 |
| 09 | `Ryan Video Prompt Agent` ComfyUI 节点 |

---

## File Structure（全阶段）

**Issue 07 — Create:**

- `docs/agents/acp-fixed-prompt-agent-contracts.md` — 最小 I/O 说明（面向节点作者）
- `ryan_comfy_utils/acp/fixtures/skills/image_prompt_generator/SKILL.md`
- `ryan_comfy_utils/acp/fixtures/skills/video_prompt_generator/SKILL.md`
- `ryan_comfy_utils/acp/fixtures/manifests/image_prompt_agent.json`
- `ryan_comfy_utils/acp/fixtures/manifests/video_prompt_agent.json`
- `tests/acp/test_fixed_prompt_manifests.py`

**Issue 07 — Modify:**

- `ryan_comfy_utils/nodes/acp_nodes.py` — 抽取 `run_fixed_acp_agent(...)`（manifest 固定 skill、支持 `image_paths` / `file_paths` 解析为多行路径列表）
- `ryan_comfy_utils/acp/skill_loader.py` 或 nodes 层 — 当 `skill_root` 为空时，回退到包内 `fixtures/skills`（仅用于默认可运行与测试）

**Issue 08 — Create:**

- `tests/nodes/test_acp_image_prompt_node.py`

**Issue 08 — Modify:**

- `ryan_comfy_utils/nodes/acp_nodes.py` — `RyanACPImagePromptAgent`
- `__init__.py` — 节点注册
- `README.md` — Image Prompt 节点小节

**Issue 09 — Create:**

- `tests/nodes/test_acp_video_prompt_node.py`

**Issue 09 — Modify:**

- `ryan_comfy_utils/nodes/acp_nodes.py` — `RyanACPVideoPromptAgent`
- `__init__.py` — 节点注册
- `README.md` — Video Prompt 节点小节

---

## Issue 07 Tasks

### Task 7.1: Contract 文档

- [ ] 写入 `docs/agents/acp-fixed-prompt-agent-contracts.md`
- [ ] 与 `fixed-agent-node-selection.md` 中 2.1 / 2.2 字段一致

### Task 7.2: Skill 最小资产

- [ ] 两个 `SKILL.md`：说明职责为「创作生成用 prompt」，非分析/质检
- [ ] 含 frontmatter 或首段：`name` / 适用场景 / 输出格式期望（纯文本 prompt）

### Task 7.3: Manifest fixtures

- [ ] `image_prompt_agent.json`：`node_id` `ryan.acp.image_prompt_agent`，`mode` `fixed`，`skill_id` `image_prompt_generator`，`input_contract` 含 text + images
- [ ] `video_prompt_agent.json`：对称，`video_prompt_generator`
- [ ] `context_template` 引用 `{input.text}`、`{input.images}` 及可选字段占位（通过 nodes 层拼入 `user_text` 或扩展 template_engine 占位 — 优先 nodes 层拼接以降低 template_engine 变更面）

### Task 7.4: 固定节点运行辅助 + skill_root 回退

- [ ] `run_fixed_acp_agent`：加载 manifest、`skill_id` 来自 manifest、解析多行 `image_paths`/`file_paths`
- [ ] `skill_root` 空 → `PACKAGE_ROOT / "acp" / "fixtures" / "skills"`
- [ ] 测试：manifest 加载、`resolve_skill_directory` 回退路径存在

**Verify:**

```bash
python3 -m unittest tests.acp.test_fixed_prompt_manifests -v
```

---

## Issue 08 Tasks

### Task 8.1: 节点 INPUT_TYPES / RETURN_TYPES

- [ ] `CATEGORY`：`Ryan Utils / ACP`
- [ ] Required：`user_text`（multiline）
- [ ] Optional：`image_paths`（multiline）、`style`、`subject`、`scene`、`extra_prompt`；运行参数 `profile_path`、`workspace_root`、`session_id`、`skill_root`（可默认空）
- [ ] `RETURN_TYPES` / `RETURN_NAMES` 与 Universal 一致：`(response_text, session_dir, raw_result_json)`

### Task 8.2: run() 行为

- [ ] 默认 `manifest_path` 指向 `image_prompt_agent.json`
- [ ] 将可选字段合并进传给 runtime 的文本或模板上下文
- [ ] `image_paths` 非空时传入 `execute_text_session(..., image_inputs=...)`

### Task 8.3: 测试

- [ ] Mock `execute_text_session`，断言 `skill_id`、`image_inputs`、manifest 路径
- [ ] Contract 测试：`INPUT_TYPES` 键、`RETURN_NAMES`

**Verify:**

```bash
python3 -m unittest tests.nodes.test_acp_image_prompt_node tests.nodes.test_acp_nodes -v
```

---

## Issue 09 Tasks

### Task 9.1–9.3

- [ ] 与 Issue 08 对称，`video_prompt_agent.json`，可选 `task` / `extra_prompt`，无 `style/subject/scene` 或保留 `extra_prompt` only（与 contract 文档一致）
- [ ] 测试文件 `test_acp_video_prompt_node.py`
- [ ] README 补充与 Video Loader / Frame Sampler 组合说明（一句即可）

**Verify:**

```bash
python3 -m unittest tests.nodes.test_acp_video_prompt_node tests.nodes.test_acp_nodes -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

---

## 超出本计划范围

- ComfyUI `IMAGE` 批量接入 ACP（tensor → session 落盘）
- 真实 Claude/Codex CLI 联调与 Skill 外链仓库
- Image Analyze / Storyboard / Character Design / File Generator 固定节点
- Universal Agent 默认开启 images 输入

---

## 建议提交粒度

1. `feat: add acp fixed prompt shared assets`（issue 07）
2. `feat: add ryan image prompt agent node`（issue 08）
3. `feat: add ryan video prompt agent node`（issue 09）