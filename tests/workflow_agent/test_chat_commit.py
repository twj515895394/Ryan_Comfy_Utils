import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.chat_service import WorkflowAgentChatService
from ryan_comfy_utils.workflow_agent.commit_service import CommitServiceError, WorkflowAgentCommitService
from ryan_comfy_utils.workflow_agent.repository import WorkflowAgentRepository


SKILL_DIR = Path("ryan_comfy_utils/acp/fixtures/skills/creative-story-planner")


class FakeRpcRunner:
    def __init__(self):
        self.calls = []
        self.status = "idle"

    def run(self, **kwargs):
        self.calls.append(kwargs)
        self.status = "completed"
        index = len(self.calls)
        return iter(
            [
                {"type": "delta", "text": f"# Canon {index}\n"},
                {"type": "completed"},
            ]
        )


class TestWorkflowAgentChatCommit(unittest.TestCase):
    def test_commit_consumes_rpc_iterator_and_persists_latest_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            runner = FakeRpcRunner()
            service = WorkflowAgentCommitService(
                repository,
                runner,
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            )

            result = service.commit(
                {
                    "workflow_id": "wf_one",
                    "agent_uid": "agent_one",
                    "skill_id": "creative-story-planner",
                    "draft": "A confirmed story draft",
                }
            )

            self.assertEqual(result["status"], "committed")
            self.assertEqual(result["commit_revision"], 1)
            self.assertEqual(result["entry"]["content"], "# Canon 1\n")
            self.assertIn("output_id", runner.calls[0]["prompt"])
            self.assertIn("shot_id", runner.calls[0]["prompt"])
            self.assertIn("Every output requires output_id, kind, label, text, and priority", runner.calls[0]["prompt"])
            self.assertIn('"reference_roles":{"IDENTITY_REFERENCE":["asset_id"]}', runner.calls[0]["prompt"])
            self.assertIn("reference_roles 必须是对象", runner.calls[0]["prompt"])
            self.assertIn("每个角色值必须是数组", runner.calls[0]["prompt"])
            self.assertIn("For ordinary outputs, use text (not prompt)", runner.calls[0]["prompt"])
            self.assertIn("do not use id/constraint instead of output_id/text", runner.calls[0]["prompt"])
            self.assertIn("concept_art", runner.calls[0]["prompt"])
            self.assertIn("质量底线：这是正式交付，不是聊天摘要", runner.calls[0]["prompt"])
            self.assertNotEqual(Path(runner.calls[0]["session_dir"]), repository.agent_root("wf_one", "agent_one"))
            self.assertFalse(Path(runner.calls[0]["session_dir"]).exists())
            self.assertEqual(
                repository.read_latest_commit("wf_one", "agent_one")["entry"]["entry_id"],
                result["latest_entry_id"],
            )
    def test_commit_persists_valid_artifact_bundle_and_cleans_markdown(self):
        class StructuredRunner(FakeRpcRunner):
            def run(self, **kwargs):
                self.calls.append(kwargs)
                return iter(
                    [
                        {
                            "type": "delta",
                            "text": (
                                "# Canonical Story\n\n正文\n\n"
                                "```ryan-artifact\n"
                                '{"artifact_type":"creative_story","schema_version":1,'
                                '"content":{"summary":"结构化摘要"},"outputs":['
                                '{"output_id":"concept_01","kind":"concept_image_prompt","label":"概念图",'
                                '"text":"概念图提示词"}],"shots":[]}'
                                "\n```\n"
                            ),
                        },
                        {"type": "completed"},
                    ]
                )

        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            result = WorkflowAgentCommitService(
                repository,
                StructuredRunner(),
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            ).commit(
                {
                    "workflow_id": "wf_one",
                    "agent_uid": "agent_one",
                    "skill_id": "creative-story-planner",
                    "draft": "confirmed",
                }
            )

            self.assertEqual(result["artifact_status"], "valid")
            self.assertEqual(result["entry"]["content"], "# Canonical Story\n\n正文")
            self.assertEqual(result["entry"]["metadata"]["artifact_bundle"]["outputs"][0]["output_id"], "concept_01")

    def test_commit_persists_absent_artifact_status(self):
        class PlainRunner(FakeRpcRunner):
            def run(self, **kwargs):
                self.calls.append(kwargs)
                self.status = "completed"
                return iter([{"type": "delta", "text": "A plain final answer"}, {"type": "completed"}])

        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            result = WorkflowAgentCommitService(
                repository,
                PlainRunner(),
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            ).commit(
                {
                    "workflow_id": "wf_one",
                    "agent_uid": "agent_one",
                    "skill_id": "creative-story-planner",
                    "draft": "A plain final answer",
                }
            )
            self.assertEqual(result["artifact_status"], "absent")
            self.assertEqual(result["entry"]["metadata"]["artifact_status"], "absent")
    def test_commit_prefers_authoritative_final_text_over_stream_deltas(self):
        result = WorkflowAgentCommitService._commit_text(
            [
                {"type": "message_update", "text": "过程文本"},
                {"type": "agent_end", "final_text": "# Canonical\n"},
            ]
        )
        self.assertEqual(result, "# Canonical\n")

    def test_commit_preserves_pi_failure_detail(self):
        class FailingRunner:
            def run(self, **_kwargs):
                raise RuntimeError("provider rejected request")

        with tempfile.TemporaryDirectory() as tmp:
            service = WorkflowAgentCommitService(
                WorkflowAgentRepository(Path(tmp) / "acp_workspace"),
                FailingRunner(),
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            )
            with self.assertRaisesRegex(
                CommitServiceError, r"Pi COMMIT failed: provider rejected request"
            ):
                service.commit(
                    {
                        "workflow_id": "wf_one",
                        "agent_uid": "agent_one",
                        "skill_id": "creative-story-planner",
                    }
                )


    def test_commit_keeps_invalid_optional_block_as_legacy_content(self):
        class InvalidRunner(FakeRpcRunner):
            def run(self, **kwargs):
                self.calls.append(kwargs)
                return iter([{"type": "delta", "text": "# Canonical\n\n```ryan-artifact\n{bad}\n```"}])

        with tempfile.TemporaryDirectory() as tmp:
            result = WorkflowAgentCommitService(
                WorkflowAgentRepository(Path(tmp) / "acp_workspace"),
                InvalidRunner(),
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            ).commit({"workflow_id": "wf_one", "agent_uid": "agent_one", "skill_id": "creative-story-planner"})
            self.assertEqual(result["artifact_status"], "invalid")
            self.assertIn("```ryan-artifact", result["entry"]["content"])
            self.assertIn("artifact_error", result)

    def test_discuss_generates_unique_request_ids_and_retry_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            runner = FakeRpcRunner()
            service = WorkflowAgentChatService(
                repository,
                runner,
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            )
            base = {
                "workflow_id": "wf_one",
                "agent_uid": "agent_one",
                "skill_id": "creative-story-planner",
            }

            first = service.discuss({**base, "message": "先给一个创意"})
            second = service.discuss({**base, "message": "再补一个冲突"})
            retry = service.discuss(
                {
                    **base,
                    "message": "先给一个创意（重试）",
                    "request_id": first["request_id"],
                    "message_id": first["message_id"],
                }
            )

            self.assertNotEqual(first["request_id"], second["request_id"])
            self.assertEqual(retry["response_text"], first["response_text"])
            self.assertEqual(len(runner.calls), 2)
            self.assertTrue(Path(runner.calls[0]["skill_directory"]).is_absolute())
            self.assertEqual(repository.read_state("wf_one", "agent_one").status, "idle")
            self.assertEqual(len(repository.read_pi_session("wf_one", "agent_one")), 4)
    def test_discuss_uses_authoritative_agent_end_text(self):
        class FinalMessageRunner(FakeRpcRunner):
            def run(self, **kwargs):
                self.calls.append(kwargs)
                self.status = "completed"
                return iter(
                    [
                        {"type": "message_update", "text": "内部草稿\n", "status": "delta"},
                        {
                            "type": "agent_end",
                            "messages": [
                                {"role": "assistant", "content": [{"type": "text", "text": "最终答案"}]},
                            ],
                        },
                        {"type": "agent_settled", "status": "completed"},
                    ]
                )

        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            service = WorkflowAgentChatService(
                repository,
                FinalMessageRunner(),
                skill_directory_resolver=lambda _skill_id: SKILL_DIR,
            )

            result = service.discuss(
                {
                    "workflow_id": "wf_one",
                    "agent_uid": "agent_one",
                    "skill_id": "creative-story-planner",
                    "message": "请给出最终答案",
                }
            )

            self.assertEqual(result["response_text"], "最终答案")
            self.assertEqual(repository.read_state("wf_one", "agent_one").draft, "最终答案")


if __name__ == "__main__":
    unittest.main()
