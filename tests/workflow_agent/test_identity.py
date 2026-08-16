import unittest

from ryan_comfy_utils.workflow_agent.identity import (
    agent_uid_for_duplicate,
    ensure_workflow_id,
    get_workflow_id,
    validate_id,
    workflow_id_for_save_as,
)


class TestWorkflowAgentIdentity(unittest.TestCase):
    def test_workflow_id_is_persisted_under_extra(self):
        workflow = {"extra": {}}

        workflow_id = ensure_workflow_id(workflow)

        self.assertEqual(get_workflow_id(workflow), workflow_id)
        self.assertEqual(workflow["extra"]["ryan_agent"]["workflow_id"], workflow_id)
        self.assertEqual(ensure_workflow_id(workflow), workflow_id)

    def test_save_as_and_duplicate_create_new_scope_ids(self):
        original_workflow = "wf_original"
        original_agent = "agent_original"

        self.assertNotEqual(workflow_id_for_save_as(original_workflow), original_workflow)
        self.assertNotEqual(agent_uid_for_duplicate(original_agent), original_agent)

    def test_path_escape_ids_are_rejected(self):
        for value in ("", "..", "../etc", "C:/etc", "/etc", "a\\b"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_id(value)


if __name__ == "__main__":
    unittest.main()
