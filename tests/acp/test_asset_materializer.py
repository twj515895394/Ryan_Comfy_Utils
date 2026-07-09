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

            self.assertEqual(assets["images"], ["input/images/01_frame_001.png"])
            self.assertEqual(assets["files"], ["input/files/01_notes.txt"])
            self.assertTrue((session_dir / "input" / "images" / "01_frame_001.png").exists())
            self.assertTrue((session_dir / "input" / "files" / "01_notes.txt").exists())

    def test_same_basename_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_dir = root / "sessions" / "session_001"
            (session_dir / "input").mkdir(parents=True)
            a = root / "a" / "frame.png"
            b = root / "b" / "frame.png"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_bytes(b"aaa")
            b.write_bytes(b"bbb")
            assets = materialize_input_assets(
                session_dir=session_dir,
                image_inputs=[str(a), str(b)],
            )
            self.assertEqual(
                assets["images"],
                ["input/images/01_frame.png", "input/images/02_frame.png"],
            )
            self.assertEqual(
                (session_dir / "input" / "images" / "01_frame.png").read_bytes(),
                b"aaa",
            )
            self.assertEqual(
                (session_dir / "input" / "images" / "02_frame.png").read_bytes(),
                b"bbb",
            )

    def test_skips_copy_when_already_under_session_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            session_dir = root / "sessions" / "session_001"
            images_dir = session_dir / "input" / "images"
            images_dir.mkdir(parents=True)
            existing = images_dir / "ryan_slot01_00.png"
            existing.write_bytes(b"slot")
            assets = materialize_input_assets(
                session_dir=session_dir,
                image_inputs=[str(existing)],
            )
            self.assertEqual(assets["images"], ["input/images/ryan_slot01_00.png"])
            # 不应再生成序号副本
            self.assertEqual(list(images_dir.iterdir()), [existing])


if __name__ == "__main__":
    unittest.main()
