import asyncio
import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.workflow_agent.routes import _asset_body


class FakePart:
    def __init__(self, name, *, filename=None, value=b"", content_type=None):
        self.name = name
        self.filename = filename
        self._value = value
        self._read = False
        self.headers = {"Content-Type": content_type} if content_type else {}

    async def read_chunk(self, _size):
        if self._read:
            return b""
        self._read = True
        return self._value

    async def text(self):
        return self._value.decode("utf-8")


class FakeMultipart:
    def __init__(self, parts):
        self.parts = parts

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for part in self.parts:
            yield part


class FakeRequest:
    content_type = "multipart/form-data; boundary=test"

    def __init__(self, parts):
        self.parts = parts

    async def multipart(self):
        return FakeMultipart(self.parts)


class TestWorkflowAgentRoutes(unittest.TestCase):
    def test_asset_body_materializes_upload_and_preserves_filename(self):
        request = FakeRequest(
            [
                FakePart("workflow_id", value=b"wf_one"),
                FakePart("agent_uid", value=b"agent_one"),
                FakePart("file", filename="brief.md", value=b"# Brief\n", content_type="text/markdown"),
            ]
        )

        body, temporary_path = asyncio.run(_asset_body(request))
        try:
            self.assertEqual(body["workflow_id"], "wf_one")
            self.assertEqual(body["agent_uid"], "agent_one")
            self.assertEqual(body["display_name"], "brief.md")
            self.assertEqual(body["mime_type"], "text/markdown")
            self.assertEqual(Path(body["source_path"]).read_bytes(), b"# Brief\n")
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)

    def test_asset_body_rejects_upload_over_limit(self):
        from ryan_comfy_utils.workflow_agent.assets import MAX_ASSET_BYTES

        request = FakeRequest([FakePart("file", filename="large.txt", value=b"x" * (MAX_ASSET_BYTES + 1))])
        with self.assertRaisesRegex(ValueError, "maximum size"):
            asyncio.run(_asset_body(request))


if __name__ == "__main__":
    unittest.main()
