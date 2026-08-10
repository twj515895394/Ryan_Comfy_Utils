import io
import unittest
from contextlib import redirect_stdout

from ryan_comfy_utils.nodes.smart_filter_node import (
    MAX_SLOTS,
    RyanSmartAudioFilter,
    RyanSmartImageFilter,
    RyanSmartTextFilter,
    RyanSmartVideoFilter,
)


class TestSmartFilterNode(unittest.TestCase):
    def test_declares_all_slots_without_dynamic_schema(self):
        input_types = RyanSmartImageFilter.INPUT_TYPES()
        slot_names = [f"in_{index:02d}" for index in range(1, MAX_SLOTS + 1)]
        output_names = [f"out_{index:02d}" for index in range(1, MAX_SLOTS + 1)]

        self.assertEqual(
            [name for name in input_types["optional"] if name.startswith("in_")],
            slot_names,
        )
        self.assertEqual(RyanSmartImageFilter.RETURN_NAMES, tuple(output_names))
        self.assertEqual(len(RyanSmartImageFilter.RETURN_TYPES), MAX_SLOTS)

    def test_logs_connected_valid_and_null_counts(self):
        prompt = {
            "node-1": {
                "inputs": {
                    "in_01": ["source-1", 0],
                    "in_02": ["source-2", 0],
                }
            }
        }
        output = io.StringIO()
        with redirect_stdout(output):
            result = RyanSmartTextFilter().filter_inputs(
                unique_id="node-1",
                prompt=prompt,
                in_01="example.png",
                in_02="real.txt",
            )

        self.assertIsNone(result[0])
        self.assertEqual(result[1], "real.txt")
        log = output.getvalue()
        self.assertIn("[text] node=node-1 connected=2 valid_outputs=1 null_outputs=1", log)
        self.assertIn("null_slots=[1]", log)
        self.assertIn("valid_slots=[2]", log)

    def test_all_filter_types_emit_summary_logs(self):
        filters = (
            (RyanSmartImageFilter, "image"),
            (RyanSmartVideoFilter, "video"),
            (RyanSmartAudioFilter, "audio"),
            (RyanSmartTextFilter, "text"),
        )
        for filter_class, group_name in filters:
            output = io.StringIO()
            with redirect_stdout(output):
                result = filter_class().filter_inputs(in_01=object())
            self.assertIsNotNone(result[0])
            self.assertIn(
                f"[{group_name}] node=unknown connected=1 valid_outputs=1 null_outputs=0",
                output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
