import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.repository import WorkflowAgentRepository
from ryan_comfy_utils.workflow_agent.state import AgentState


class TestWorkflowAgentRepository(unittest.TestCase):
    def test_scope_persistence_and_paths_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            first = repository.initialize_scope(
                "wf_one",
                "agent_one",
                state=AgentState(
                    workflow_id="wf_one",
                    agent_uid="agent_one",
                    skill_id="creative-story-planner",
                    draft="draft text",
                    status="draft",
                ),
            )
            second = repository.initialize_scope("wf_two", "agent_one")

            repository.append_pi_session("wf_one", "agent_one", {"role": "user", "text": "hello"})
            repository.write_latest_commit("wf_one", "agent_one", {"entry_id": "entry_one"})
            repository.append_lineage("wf_one", "agent_one", {"entry_id": "entry_one"})

            restored = repository.read_state("wf_one", "agent_one")
            self.assertEqual(restored.draft, "draft text")
            self.assertEqual(repository.read_pi_session("wf_one", "agent_one")[0]["text"], "hello")
            self.assertEqual(repository.read_latest_commit("wf_one", "agent_one")["entry_id"], "entry_one")
            self.assertEqual(repository.read_lineage("wf_one", "agent_one")[0]["entry_id"], "entry_one")
            self.assertNotEqual(first.root, second.root)
            self.assertTrue(first.assets.is_dir())
            self.assertTrue(first.latest_commit.exists())

    def test_agent_sessions_are_isolated_within_one_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")
            repository.initialize_scope("wf_one", "agent_one")
            repository.initialize_scope("wf_one", "agent_two")

            repository.append_pi_session("wf_one", "agent_one", {"role": "user", "text": "A"})
            repository.write_latest_commit("wf_one", "agent_one", {"entry_id": "commit_a"})
            repository.append_pi_session("wf_one", "agent_two", {"role": "user", "text": "B"})
            repository.write_latest_commit("wf_one", "agent_two", {"entry_id": "commit_b"})

            self.assertEqual(
                repository.read_pi_session("wf_one", "agent_one"),
                [{"role": "user", "text": "A"}],
            )
            self.assertEqual(
                repository.read_pi_session("wf_one", "agent_two"),
                [{"role": "user", "text": "B"}],
            )
            self.assertEqual(
                repository.read_latest_commit("wf_one", "agent_one")["entry_id"],
                "commit_a",
            )
            self.assertEqual(
                repository.read_latest_commit("wf_one", "agent_two")["entry_id"],
                "commit_b",
            )

    def test_invalid_scope_id_is_rejected_before_path_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repository = WorkflowAgentRepository(Path(tmp) / "acp_workspace")

            with self.assertRaises(ValueError):
                repository.scope_paths("../outside", "agent_one")

            self.assertFalse((Path(tmp) / "outside").exists())


if __name__ == "__main__":
    unittest.main()
