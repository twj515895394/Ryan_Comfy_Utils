import tempfile
import unittest
from pathlib import Path

from ryan_comfy_utils.nodes.comfy_image_inputs import (
    MAX_RYAN_IMAGE_SLOTS,
    build_image_slot_input_types,
    collect_image_tensors_from_kwargs,
    count_connected_image_slots,
    image_slot_name,
    trim_trailing_empty_slots,
)


class TestComfyImageInputs(unittest.TestCase):
    def test_slot_names(self):
        self.assertEqual(image_slot_name(1), "image_01")
        self.assertEqual(image_slot_name(10), "image_10")

    def test_build_defaults_one_visible_slot(self):
        optional = build_image_slot_input_types()
        self.assertIn("image_01", optional)
        self.assertIn("image_10", optional)
        self.assertIn("image_slot_count", optional)

    def test_collect_from_kwargs(self):
        slots = collect_image_tensors_from_kwargs(
            {"image_01": "t1", "image_02": None, "image_03": "t3"},
            max_slots=3,
        )
        self.assertEqual(slots, ["t1", None, "t3"])
        self.assertEqual(count_connected_image_slots(slots), 2)

    def test_trim_trailing(self):
        self.assertEqual(trim_trailing_empty_slots([1, None, 2, None]), [1, None, 2])


if __name__ == "__main__":
    unittest.main()