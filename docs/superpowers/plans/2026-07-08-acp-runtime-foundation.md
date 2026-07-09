# ACP Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Ryan_Comfy_Utils 建立 ACP Foundation：先定义稳定协议，再实现最小可用 runtime，最后接入 `Ryan ACP Universal Agent` 形成字符串输入输出闭环。

**Architecture:** 在 `ryan_comfy_utils/acp/` 下新增一个独立 runtime 包，将协议、session/workspace、skill/context、CLI 执行与结果解析分层组织。ComfyUI 节点只做输入输出适配，不内嵌协议判断和运行时细节。

**Tech Stack:** Python 3.10+, stdlib `json` / `subprocess` / `pathlib` / `tempfile` / `unittest`, ComfyUI node API

---

## File Structure

- Create: `ryan_comfy_utils/acp/__init__.py`
- Create: `ryan_comfy_utils/acp/contracts.py`
- Create: `ryan_comfy_utils/acp/session.py`
- Create: `ryan_comfy_utils/acp/workspace.py`
- Create: `ryan_comfy_utils/acp/skill_loader.py`
- Create: `ryan_comfy_utils/acp/context_builder.py`
- Create: `ryan_comfy_utils/acp/template_engine.py`
- Create: `ryan_comfy_utils/acp/cli_runner.py`
- Create: `ryan_comfy_utils/acp/result_parser.py`
- Create: `ryan_comfy_utils/acp/runtime.py`
- Create: `ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json`
- Create: `ryan_comfy_utils/acp/fixtures/profiles/local_codex.json`
- Create: `ryan_comfy_utils/acp/fixtures/results/text_success.json`
- Create: `ryan_comfy_utils/nodes/acp_nodes.py`
- Modify: `__init__.py`
- Modify: `README.md`
- Create: `tests/acp/test_contracts.py`
- Create: `tests/acp/test_session_workspace.py`
- Create: `tests/acp/test_context_builder.py`
- Create: `tests/acp/test_cli_runner.py`
- Create: `tests/acp/test_runtime.py`
- Create: `tests/nodes/test_acp_nodes.py`

### Task 1: Define ACP Contracts And Fixtures

**Files:**
- Create: `ryan_comfy_utils/acp/__init__.py`
- Create: `ryan_comfy_utils/acp/contracts.py`
- Create: `ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json`
- Create: `ryan_comfy_utils/acp/fixtures/profiles/local_codex.json`
- Create: `ryan_comfy_utils/acp/fixtures/results/text_success.json`
- Test: `tests/acp/test_contracts.py`

- [ ] **Step 1: Write the failing contract tests**

```python
import json
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.contracts import (
    load_manifest,
    load_profile,
    validate_result_payload,
)


class TestACPContracts(unittest.TestCase):
    def test_load_manifest_reads_required_fields(self):
        manifest = load_manifest(
            Path("ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json")
        )
        self.assertEqual(manifest["node_id"], "ryan.acp.universal_agent")
        self.assertEqual(manifest["mode"], "selectable")
        self.assertEqual(manifest["output_contract"]["type"], "text")

    def test_load_profile_reads_command_and_timeout(self):
        profile = load_profile(
            Path("ryan_comfy_utils/acp/fixtures/profiles/local_codex.json")
        )
        self.assertEqual(profile["runner"], "codex_cli")
        self.assertGreater(profile["timeout_seconds"], 0)

    def test_validate_result_payload_requires_status_and_outputs(self):
        payload = json.loads(
            Path("ryan_comfy_utils/acp/fixtures/results/text_success.json").read_text(
                encoding="utf-8"
            )
        )
        validated = validate_result_payload(payload)
        self.assertEqual(validated["status"], "ok")
        self.assertIn("response_text", validated["outputs"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.acp.test_contracts -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ryan_comfy_utils.acp'`

- [ ] **Step 3: Write the minimal contract implementation**

```python
from __future__ import annotations

import json
from pathlib import Path


REQUIRED_MANIFEST_KEYS = {
    "node_id",
    "skill_id",
    "mode",
    "context_template",
    "input_contract",
    "output_contract",
    "result_mapping",
}

REQUIRED_PROFILE_KEYS = {
    "runner",
    "command",
    "workspace_root",
    "timeout_seconds",
    "environment",
}


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def load_manifest(path: Path) -> dict:
    data = _load_json(path)
    missing = REQUIRED_MANIFEST_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Manifest missing keys: {sorted(missing)}")
    return data


def load_profile(path: Path) -> dict:
    data = _load_json(path)
    missing = REQUIRED_PROFILE_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Profile missing keys: {sorted(missing)}")
    return data


def validate_result_payload(payload: dict) -> dict:
    if "status" not in payload:
        raise ValueError("Result payload missing status")
    if "outputs" not in payload or not isinstance(payload["outputs"], dict):
        raise ValueError("Result payload missing outputs")
    return payload
```

- [ ] **Step 4: Add the first fixture files**

```json
{
  "node_id": "ryan.acp.universal_agent",
  "skill_id": "",
  "mode": "selectable",
  "context_template": "读取 Skill:\n{skill_directory}\n\n用户输入:\n{input.text}\n",
  "input_contract": {
    "text": true,
    "images": false,
    "files": false
  },
  "output_contract": {
    "type": "text",
    "fields": ["response_text", "raw_result_json"]
  },
  "result_mapping": {
    "response_text": "outputs.response_text",
    "raw_result_json": "raw_result_json"
  }
}
```

```json
{
  "runner": "codex_cli",
  "command": ["codex", "exec"],
  "workspace_root": "output/acp_workspace",
  "timeout_seconds": 300,
  "environment": {}
}
```

```json
{
  "status": "ok",
  "outputs": {
    "response_text": "hello from acp"
  },
  "raw_result_json": {
    "stdout": "hello from acp",
    "stderr": ""
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.acp.test_contracts -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ryan_comfy_utils/acp tests/acp/test_contracts.py
git commit -m "feat: add acp contract fixtures"
```

### Task 2: Build Session And Workspace Management

**Files:**
- Create: `ryan_comfy_utils/acp/session.py`
- Create: `ryan_comfy_utils/acp/workspace.py`
- Test: `tests/acp/test_session_workspace.py`

- [ ] **Step 1: Write the failing session/workspace tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.session import create_session_record
from ryan_comfy_utils.acp.workspace import prepare_workspace


class TestSessionWorkspace(unittest.TestCase):
    def test_prepare_workspace_creates_expected_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = prepare_workspace(Path(tmpdir), "session_001")
            self.assertTrue((workspace / "input").exists())
            self.assertTrue((workspace / "output").exists())
            self.assertTrue((workspace / "logs").exists())

    def test_create_session_record_writes_metadata_and_context_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = prepare_workspace(Path(tmpdir), "session_001")
            record = create_session_record(
                workspace=workspace,
                runner="codex_cli",
                skill_id="video_prompt_generator",
                context_payload={"input": {"text": "hello"}},
            )
            metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(record["skill_id"], "video_prompt_generator")
            self.assertEqual(metadata["runner"], "codex_cli")
            self.assertTrue((workspace / "context.json").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.acp.test_session_workspace -v`
Expected: FAIL with `ImportError` for `session` or `workspace`

- [ ] **Step 3: Write the minimal workspace implementation**

```python
from pathlib import Path


def prepare_workspace(workspace_root: Path, session_id: str) -> Path:
    session_dir = workspace_root / "sessions" / session_id
    for name in ("input", "output", "logs"):
        (session_dir / name).mkdir(parents=True, exist_ok=True)
    return session_dir
```

- [ ] **Step 4: Write the minimal session implementation**

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def create_session_record(
    workspace: Path,
    runner: str,
    skill_id: str,
    context_payload: dict,
) -> dict:
    record = {
        "runner": runner,
        "skill_id": skill_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (workspace / "metadata.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (workspace / "context.json").write_text(
        json.dumps(context_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.acp.test_session_workspace -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ryan_comfy_utils/acp/session.py ryan_comfy_utils/acp/workspace.py tests/acp/test_session_workspace.py
git commit -m "feat: add acp session workspace management"
```

### Task 3: Build Skill Loading And Context Construction

**Files:**
- Create: `ryan_comfy_utils/acp/skill_loader.py`
- Create: `ryan_comfy_utils/acp/context_builder.py`
- Create: `ryan_comfy_utils/acp/template_engine.py`
- Test: `tests/acp/test_context_builder.py`

- [ ] **Step 1: Write the failing context tests**

```python
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.context_builder import build_context_payload
from ryan_comfy_utils.acp.template_engine import render_context_template


class TestContextBuilder(unittest.TestCase):
    def test_build_context_payload_collects_text_and_skill_directory(self):
        payload = build_context_payload(
            skill_id="video_prompt_generator",
            skill_directory=Path("/tmp/skills/video_prompt_generator"),
            user_text="describe this clip",
            image_paths=["input/frame_001.png"],
            file_paths=[],
            workspace_info={"session_dir": "/tmp/session_001"},
        )
        self.assertEqual(payload["skill"]["id"], "video_prompt_generator")
        self.assertEqual(payload["input"]["text"], "describe this clip")
        self.assertEqual(payload["input"]["images"][0], "input/frame_001.png")

    def test_render_context_template_replaces_known_placeholders(self):
        template = "读取 Skill:\\n{skill_directory}\\n用户输入:\\n{input.text}"
        payload = {
            "skill": {"directory": "/tmp/skills/video_prompt_generator"},
            "input": {"text": "describe this clip"},
        }
        rendered = render_context_template(template, payload)
        self.assertIn("/tmp/skills/video_prompt_generator", rendered)
        self.assertIn("describe this clip", rendered)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.acp.test_context_builder -v`
Expected: FAIL with `ImportError` for context builder modules

- [ ] **Step 3: Write the minimal context builder**

```python
from pathlib import Path


def build_context_payload(
    skill_id: str,
    skill_directory: Path,
    user_text: str,
    image_paths: list[str],
    file_paths: list[str],
    workspace_info: dict,
) -> dict:
    return {
        "skill": {
            "id": skill_id,
            "directory": str(skill_directory),
        },
        "input": {
            "text": user_text,
            "images": image_paths,
            "files": file_paths,
        },
        "workspace": workspace_info,
    }
```

- [ ] **Step 4: Write the minimal template renderer**

```python
def render_context_template(template: str, payload: dict) -> str:
    replacements = {
        "{skill_directory}": payload["skill"]["directory"],
        "{input.text}": payload["input"]["text"],
        "{input.images}": "\n".join(payload["input"].get("images", [])),
        "{input.files}": "\n".join(payload["input"].get("files", [])),
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered
```

- [ ] **Step 5: Add the first skill directory resolver**

```python
from pathlib import Path


def resolve_skill_directory(skill_root: Path, skill_id: str) -> Path:
    path = skill_root / skill_id
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m unittest tests.acp.test_context_builder -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add ryan_comfy_utils/acp/skill_loader.py ryan_comfy_utils/acp/context_builder.py ryan_comfy_utils/acp/template_engine.py tests/acp/test_context_builder.py
git commit -m "feat: add acp context builder"
```

### Task 4: Build CLI Runner And Result Parsing

**Files:**
- Create: `ryan_comfy_utils/acp/cli_runner.py`
- Create: `ryan_comfy_utils/acp/result_parser.py`
- Test: `tests/acp/test_cli_runner.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.cli_runner import run_cli_command
from ryan_comfy_utils.acp.result_parser import parse_text_result


class TestCLIRunner(unittest.TestCase):
    def test_run_cli_command_captures_stdout_and_stderr(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli_command(
                command=["python3", "-c", "print('hello from cli')"],
                cwd=Path(tmpdir),
                timeout_seconds=10,
                env_overrides={},
            )
            self.assertEqual(result["returncode"], 0)
            self.assertIn("hello from cli", result["stdout"])

    def test_parse_text_result_prefers_structured_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "result.json"
            output_path.write_text(
                json.dumps({"status": "ok", "outputs": {"response_text": "done"}}),
                encoding="utf-8",
            )
            parsed = parse_text_result(output_path, stdout_fallback="fallback")
            self.assertEqual(parsed["outputs"]["response_text"], "done")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.acp.test_cli_runner -v`
Expected: FAIL with `ImportError` for runner/parser modules

- [ ] **Step 3: Write the minimal CLI runner**

```python
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_cli_command(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    env_overrides: dict,
) -> dict:
    env = os.environ.copy()
    env.update(env_overrides)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
```

- [ ] **Step 4: Write the minimal text result parser**

```python
import json
from pathlib import Path


def parse_text_result(result_json_path: Path, stdout_fallback: str) -> dict:
    if result_json_path.exists():
        return json.loads(result_json_path.read_text(encoding="utf-8"))
    return {
        "status": "ok",
        "outputs": {"response_text": stdout_fallback.strip()},
        "raw_result_json": {"stdout": stdout_fallback, "stderr": ""},
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.acp.test_cli_runner -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ryan_comfy_utils/acp/cli_runner.py ryan_comfy_utils/acp/result_parser.py tests/acp/test_cli_runner.py
git commit -m "feat: add acp cli runner"
```

### Task 5: Compose The ACP Runtime Facade

**Files:**
- Create: `ryan_comfy_utils/acp/runtime.py`
- Test: `tests/acp/test_runtime.py`

- [ ] **Step 1: Write the failing runtime test**

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ryan_comfy_utils.acp.runtime import execute_text_session


class TestACPRuntime(unittest.TestCase):
    @patch("ryan_comfy_utils.acp.runtime.run_cli_command")
    def test_execute_text_session_returns_response_and_session_paths(self, run_cli_command):
        run_cli_command.return_value = {
            "returncode": 0,
            "stdout": "hello from runtime",
            "stderr": "",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_text_session(
                workspace_root=Path(tmpdir),
                session_id="session_001",
                skill_root=Path(tmpdir),
                skill_id="video_prompt_generator",
                context_template="用户输入:\\n{input.text}",
                user_text="describe this clip",
                runner_profile={
                    "command": ["python3", "-c", "print('hello from runtime')"],
                    "timeout_seconds": 10,
                    "environment": {},
                },
            )
            self.assertEqual(result["outputs"]["response_text"], "hello from runtime")
            self.assertTrue(result["session_dir"].endswith("session_001"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.acp.test_runtime -v`
Expected: FAIL with `ImportError` for runtime module

- [ ] **Step 3: Write the minimal runtime facade**

```python
from __future__ import annotations

from pathlib import Path

from .cli_runner import run_cli_command
from .context_builder import build_context_payload
from .result_parser import parse_text_result
from .session import create_session_record
from .template_engine import render_context_template
from .workspace import prepare_workspace


def execute_text_session(
    workspace_root: Path,
    session_id: str,
    skill_root: Path,
    skill_id: str,
    context_template: str,
    user_text: str,
    runner_profile: dict,
) -> dict:
    session_dir = prepare_workspace(workspace_root, session_id)
    payload = build_context_payload(
        skill_id=skill_id,
        skill_directory=skill_root / skill_id,
        user_text=user_text,
        image_paths=[],
        file_paths=[],
        workspace_info={"session_dir": str(session_dir)},
    )
    rendered = render_context_template(context_template, payload)
    create_session_record(
        workspace=session_dir,
        runner=runner_profile.get("runner", "unknown"),
        skill_id=skill_id,
        context_payload={"rendered_context": rendered, **payload},
    )
    cli_result = run_cli_command(
        command=runner_profile["command"],
        cwd=session_dir,
        timeout_seconds=runner_profile["timeout_seconds"],
        env_overrides=runner_profile.get("environment", {}),
    )
    parsed = parse_text_result(
        session_dir / "output" / "result.json",
        stdout_fallback=cli_result["stdout"],
    )
    parsed["session_dir"] = str(session_dir)
    parsed["raw_result_json"] = cli_result
    return parsed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.acp.test_runtime -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ryan_comfy_utils/acp/runtime.py tests/acp/test_runtime.py
git commit -m "feat: compose acp runtime facade"
```

### Task 6: Add Ryan ACP Universal Agent

**Files:**
- Create: `ryan_comfy_utils/nodes/acp_nodes.py`
- Modify: `__init__.py`
- Modify: `README.md`
- Test: `tests/nodes/test_acp_nodes.py`

- [ ] **Step 1: Write the failing node tests**

```python
import unittest

from ryan_comfy_utils.nodes.acp_nodes import RyanACPUniversalAgent


class TestACPNode(unittest.TestCase):
    def test_node_returns_text_contract_outputs(self):
        node = RyanACPUniversalAgent()
        self.assertEqual(node.RETURN_TYPES, ("STRING", "STRING", "STRING"))
        self.assertEqual(
            node.RETURN_NAMES,
            ("response_text", "session_dir", "raw_result_json"),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.nodes.test_acp_nodes -v`
Expected: FAIL with `ImportError` for `acp_nodes`

- [ ] **Step 3: Write the minimal node implementation**

```python
from pathlib import Path

from ..acp.contracts import load_manifest, load_profile
from ..acp.runtime import execute_text_session


class RyanACPUniversalAgent:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "skill_id": ("STRING", {"default": ""}),
                "user_text": ("STRING", {"default": "", "multiline": True}),
                "profile_path": ("STRING", {"default": "ryan_comfy_utils/acp/fixtures/profiles/local_codex.json"}),
                "manifest_path": ("STRING", {"default": "ryan_comfy_utils/acp/fixtures/manifests/universal_agent.json"}),
                "workspace_root": ("STRING", {"default": "output/acp_workspace"}),
                "session_id": ("STRING", {"default": "session_manual"}),
                "skill_root": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "session_dir", "raw_result_json")
    FUNCTION = "run"
    CATEGORY = "Ryan Utils / ACP"

    def run(self, skill_id, user_text, profile_path, manifest_path, workspace_root, session_id, skill_root):
        manifest = load_manifest(Path(manifest_path))
        profile = load_profile(Path(profile_path))
        result = execute_text_session(
            workspace_root=Path(workspace_root),
            session_id=session_id,
            skill_root=Path(skill_root).expanduser(),
            skill_id=skill_id or manifest["skill_id"],
            context_template=manifest["context_template"],
            user_text=user_text,
            runner_profile=profile,
        )
        return (
            result["outputs"].get("response_text", ""),
            result["session_dir"],
            str(result["raw_result_json"]),
        )
```

- [ ] **Step 4: Register the node and update docs**

```python
from .ryan_comfy_utils.nodes.acp_nodes import RyanACPUniversalAgent

NODE_CLASS_MAPPINGS = {
    "Ryan ACP Universal Agent": RyanACPUniversalAgent,
}
```

```md
### Ryan ACP Universal Agent

分类：`Ryan Utils / ACP`

最小版 ACP Agent 节点。第一阶段只支持文本输入和文本输出，用于打通：

- manifest/profile 加载
- session/workspace 创建
- skill/context 组装
- CLI 执行
- 文本结果回传
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m unittest tests.nodes.test_acp_nodes -v`
Expected: PASS

- [ ] **Step 6: Run the full ACP test suite**

Run: `python3 -m unittest discover -s tests -p 'test_*.py' -v`
Expected: PASS for all ACP tests

- [ ] **Step 7: Commit**

```bash
git add __init__.py README.md ryan_comfy_utils/nodes/acp_nodes.py tests/nodes/test_acp_nodes.py
git commit -m "feat: add acp universal agent node"
```

## Self-Review Checklist

- 覆盖了协议、session/workspace、skill/context、CLI、runtime、node 六个实现层次。
- 所有计划步骤都包含精确文件路径与可执行命令，没有 `TODO/TBD` 占位。
- 测试聚焦外部行为：schema 读取、workspace 结构、context 输出、CLI 输出、runtime 返回值、节点 contract。

## Execution Notes

- 优先使用 fixtures 和 fake CLI 命令跑通单元测试，不要一开始依赖真实 Codex/Claude CLI。
- 在 `Ryan ACP Universal Agent` 打通前，不要提前扩固定绑定节点。
- 如果后续需要图片/文件输入，新增 issue 单独扩展 `asset_materializer`，不要塞进第一阶段。
