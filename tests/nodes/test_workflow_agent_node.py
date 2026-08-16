import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from ryan_comfy_utils.workflow_agent.repository import WorkflowAgentRepository

from ryan_comfy_utils.nodes.workflow_agent_node import RyanWorkflowAgent
from ryan_comfy_utils.workflow_agent.models import RYAN_CONTEXT, RyanContext, RyanContextEntry


def node_result(value):
    return value["result"] if isinstance(value, dict) else value


class TestWorkflowAgentNode(unittest.TestCase):

    def test_declares_max_context_and_image_sockets_with_slot_controls(self):
        inputs = RyanWorkflowAgent.INPUT_TYPES()
        required = inputs["required"]
        optional = inputs["optional"]

        self.assertEqual(required["context_slot_count"][1]["default"], 1)
        self.assertEqual(required["context_slot_count"][1]["max"], 8)
        self.assertEqual(required["image_slot_count"][1]["default"], 1)
        self.assertEqual(required["image_slot_count"][1]["max"], 10)
        self.assertEqual(
            [name for name in optional if name.startswith("context_")],
            [f"context_{index:02d}" for index in range(1, 9)],
        )
        self.assertEqual(
            [name for name in optional if name.startswith("image_")],
            [f"image_{index:02d}" for index in range(1, 11)],
        )
        self.assertEqual(optional["context_01"][0], RYAN_CONTEXT)
        self.assertEqual(optional["image_01"][0], "IMAGE")
        self.assertEqual(
            RyanWorkflowAgent.RETURN_NAMES[:8],
            (
                "context", "response_text", "session_dir", "context_json",
                "artifact_text", "image_prompt", "storyboard_prompt", "video_prompt",
            ),
        )
        self.assertEqual(
            RyanWorkflowAgent.RETURN_NAMES[8:],
            ("concept_image_prompt", "keyframe_prompt", "audio_prompt"),
        )
        self.assertTrue(RyanWorkflowAgent.OUTPUT_NODE)

    def test_legacy_blank_commit_revision_is_queue_valid(self):
        commit_revision = RyanWorkflowAgent.INPUT_TYPES()["required"]["commit_revision"]

        # 隐藏 widget 可能从旧 Workflow 以空字符串恢复；Queue 校验必须允许该历史值。
        result = node_result(RyanWorkflowAgent().run(workflow_id="wf_legacy", commit_revision=""))

        self.assertEqual(result[0].workflow_id, "wf_legacy")
        self.assertEqual(result[0].entries, [])

    def test_queue_merges_context_without_starting_external_agent(self):
        context = RyanContext(
            workflow_id="wf_node",
            entries=[
                RyanContextEntry(
                    entry_id="entry_node",
                    workflow_id="wf_node",
                    source_agent_uid="agent_upstream",
                    kind="creative.story",
                    revision=1,
                    content="Upstream Canon",
                )
            ],
        )

        result = node_result(RyanWorkflowAgent().run(workflow_id="wf_node", context_01=context))

        output_context, response_text, session_dir, context_json, *_ = result
        self.assertEqual(output_context.workflow_id, "wf_node")
        self.assertEqual(output_context.entries[0].content, "Upstream Canon")
        self.assertEqual(response_text, "")
        self.assertEqual(session_dir, "")
        self.assertIn('"workflow_id": "wf_node"', context_json)

    def test_queue_context_preserves_upstream_entry_body(self):
        context = RyanContext(
            workflow_id="wf_selector_flow",
            entries=[
                RyanContextEntry(
                    entry_id="entry_flow",
                    workflow_id="wf_selector_flow",
                    source_agent_uid="agent_upstream",
                    kind="production.design",
                    revision=1,
                    content="Upstream Canonical Design",
                )
            ],
        )
        output_context, *_ = node_result(
            RyanWorkflowAgent().run(workflow_id="wf_selector_flow", context_01=context)
        )
        self.assertEqual(output_context.entries[0].content, "Upstream Canonical Design")
    def test_queue_exposes_structured_prompt_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            repository.write_latest_commit(
                "wf_prompt",
                "agent_prompt",
                {
                    "commit_id": "commit_prompt",
                    "entry_id": "entry_prompt",
                    "workflow_id": "wf_prompt",
                    "agent_uid": "agent_prompt",
                    "revision": 1,
                    "kind": "production.design",
                    "content": "# Design",
                    "asset_refs": [],
                    "upstream_entry_ids": [],
                    "entry": {
                        "entry_id": "entry_prompt",
                        "workflow_id": "wf_prompt",
                        "source_agent_uid": "agent_prompt",
                        "kind": "production.design",
                        "revision": 1,
                        "content": "# Design",
                        "asset_refs": [],
                        "upstream_entry_ids": [],
                        "status": "active",
                        "metadata": {
                            "artifact_bundle": {
                                "artifact_type": "production_design",
                                "content": {},
                                "outputs": [
                                    {"output_id": "image", "kind": "image_prompt", "label": "image", "text": "IMAGE"},
                                    {"output_id": "story", "kind": "storyboard_sheet_prompt", "label": "story", "text": "STORY"},
                                    {"output_id": "video", "kind": "video_prompt", "label": "video", "text": "VIDEO"},
                                ],
                            }
                        },
                    },
                },
            )
            with patch(
                "ryan_comfy_utils.nodes.workflow_agent_node.WorkflowAgentRepository.from_output_root",
                return_value=repository,
            ):
                result = node_result(
                    RyanWorkflowAgent().run(workflow_id="wf_prompt", agent_uid="agent_prompt")
                )
            self.assertEqual(result[4:8], ("IMAGE", "IMAGE", "STORY", "VIDEO"))
            self.assertEqual(result[8:], ("", "", ""))

    def test_queue_exposes_context_and_text_to_on_executed_ui(self):
        result = RyanWorkflowAgent().run(workflow_id="wf_ui")

        self.assertIn("ui", result)
        self.assertEqual(result["ui"]["context_json"], [result["result"][3]])
        self.assertEqual(result["ui"]["text"], [result["result"][1]])

    def test_slot_count_ignores_context_and_images_above_selected_limit(self):
        first = RyanContext(
            workflow_id="wf_slots",
            entries=[
                RyanContextEntry(
                    entry_id="entry_first",
                    workflow_id="wf_slots",
                    source_agent_uid="agent_first",
                    kind="creative.story",
                    revision=1,
                    content="First",
                )
            ],
        )
        second = RyanContext(
            workflow_id="wf_slots",
            entries=[
                RyanContextEntry(
                    entry_id="entry_second",
                    workflow_id="wf_slots",
                    source_agent_uid="agent_second",
                    kind="script.direction",
                    revision=1,
                    content="Second",
                )
            ],
        )

        output_context, *_ = node_result(
            RyanWorkflowAgent().run(
                workflow_id="wf_slots",
                context_slot_count=1,
                image_slot_count=0,
                context_01=first,
                context_02=second,
            )
        )

        self.assertEqual([entry.entry_id for entry in output_context.entries], ["entry_first"])

    def test_image_input_is_materialized_as_session_asset(self):
        class FakeImage:
            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return np.zeros((2, 2, 3), dtype=np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            with patch(
                "ryan_comfy_utils.nodes.workflow_agent_node.WorkflowAgentRepository.from_output_root",
                return_value=repository,
            ):
                output_context, *_ = node_result(
                    RyanWorkflowAgent().run(
                        workflow_id="wf_image",
                        agent_uid="agent_image",
                        image_01=FakeImage(),
                    )
                )

            self.assertEqual(len(output_context.assets), 1)
            asset = output_context.assets[0]
            self.assertEqual(asset.type, "image")
            self.assertEqual(asset.source, "node_input")
            self.assertTrue(Path(asset.uri).is_file())

    def test_empty_queue_context_uses_node_workflow(self):
        output_context, response_text, session_dir, _, *_ = node_result(
            RyanWorkflowAgent().run(workflow_id="wf_empty")
        )

        self.assertEqual(output_context.workflow_id, "wf_empty")
        self.assertEqual(output_context.entries, [])
        self.assertEqual((response_text, session_dir), ("", ""))


if __name__ == "__main__":
    unittest.main()
