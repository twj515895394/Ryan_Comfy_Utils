import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.acp.asset_materializer import materialize_input_assets


class TestAssetMaterializer(unittest.TestCase):
    def test_materialize_input_assets_copies_images_and_files_into_session_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_dir = root / "sessions" / "session_001"
            (session_dir / "input").mkdir(parents=True)

            image_source = root / "frame_001.png"
            image_source.write_bytes(b"fake-image-data")
            file_source = root / "notes.txt"
            file_source.write_text("hello file", encoding="utf-8")

            assets = materialize_input_assets(
                session_dir=session_dir,
                image_inputs=[str(image_source)],
                file_inputs=[str(file_source)],
            )

            self.assertEqual(assets["images"], ["input/images/frame_001.png"])
            self.assertEqual(assets["files"], ["input/files/notes.txt"])
            self.assertTrue((session_dir / "input" / "images" / "frame_001.png").exists())
            self.assertTrue((session_dir / "input" / "files" / "notes.txt").exists())
