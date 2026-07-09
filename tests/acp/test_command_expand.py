import unittest

from ryan_comfy_utils.acp.command_expand import expand_cli_command


class TestCommandExpand(unittest.TestCase):
    def test_expands_known_placeholders(self):
        command = ["tool", "--file", "{context_file}", "{session_dir}"]
        expanded = expand_cli_command(
            command,
            {
                "{context_file}": "/tmp/prompt.txt",
                "{session_dir}": "/tmp/session",
            },
        )
        self.assertEqual(
            expanded,
            ["tool", "--file", "/tmp/prompt.txt", "/tmp/session"],
        )

    def test_leaves_unknown_braces_unchanged(self):
        expanded = expand_cli_command(
            ["echo", "{not_a_placeholder}"],
            {"{context}": "hello"},
        )
        self.assertEqual(expanded, ["echo", "{not_a_placeholder}"])

    def test_empty_command_raises(self):
        with self.assertRaises(ValueError):
            expand_cli_command([], {"{context}": "x"})


if __name__ == "__main__":
    unittest.main()
