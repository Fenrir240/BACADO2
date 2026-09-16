from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "build_graph_packets.py"
SPEC = importlib.util.spec_from_file_location("question_packet_builder_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


class DeterministicQuestionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = builder.load_graph()

    def test_same_graph_produces_identical_packets(self) -> None:
        for spec in builder.SPECS:
            first = builder.build_packet(self.graph, spec)
            second = builder.build_packet(self.graph, spec)
            self.assertEqual(
                json.dumps(first, ensure_ascii=False, separators=(",", ":")),
                json.dumps(second, ensure_ascii=False, separators=(",", ":")),
            )

    def test_packets_have_three_scoped_primary_grounded_slots(self) -> None:
        for spec in builder.SPECS:
            packet = builder.build_packet(self.graph, spec)
            self.assertTrue(packet["validation"]["passed"], packet["validation"])
            self.assertEqual(packet["selection"]["algorithm_version"], builder.SELECTION_ALGORITHM_VERSION)
            self.assertTrue(packet["selection"]["deterministic"])
            self.assertEqual(len(packet["selection"]["question_slots"]), 3)
            self.assertLessEqual(len(packet["nodes"]), 40)
            self.assertLessEqual(len(packet["edges"]), 100)
            for node in packet["nodes"]:
                if node["type"] == "NarrativeEvent":
                    self.assertEqual(node["attributes"]["verification"]["status"], "verified_primary")
                    self.assertTrue(node["attributes"]["verification"]["evidence_quote"])

    def test_files_on_disk_match_current_graph_and_algorithm(self) -> None:
        for spec in builder.SPECS:
            stored = json.loads((builder.OUTPUT_DIR / spec.filename).read_text(encoding="utf-8"))
            expected = builder.build_packet(self.graph, spec)
            self.assertEqual(stored, expected)
            self.assertEqual(stored["metadata"]["source_graph_sha256"], builder.sha256(builder.GRAPH_PATH))

    def test_action_anchors_do_not_duplicate_simple_anchors(self) -> None:
        simple = builder.build_packet(self.graph, builder.SPECS[0])
        action = builder.build_packet(self.graph, builder.SPECS[2])
        simple_events = {
            event_id for slot in simple["selection"]["question_slots"] for event_id in slot["event_ids"]
        }
        action_events = {
            event_id for slot in action["selection"]["question_slots"] for event_id in slot["event_ids"]
        }
        self.assertTrue(simple_events.isdisjoint(action_events))

    def test_next_batch_excludes_every_event_from_previous_batch(self) -> None:
        previous = set()
        for spec in builder.SPECS:
            previous.update(builder.selected_event_ids(builder.build_packet(self.graph, spec)))
        with tempfile.TemporaryDirectory() as temporary:
            _, selected = builder.build_packet_set(
                self.graph,
                Path(temporary),
                excluded_event_ids=previous,
                batch_number=2,
            )
        self.assertTrue(selected)
        self.assertTrue(previous.isdisjoint(selected))

    def test_four_batches_keep_category_focus_events_unique(self) -> None:
        history: dict[str, set[str]] = {}
        with tempfile.TemporaryDirectory() as temporary:
            for batch_number in range(1, 5):
                rows, _ = builder.build_packet_set(
                    self.graph,
                    Path(temporary) / f"batch-{batch_number}",
                    batch_number=batch_number,
                    excluded_event_ids_by_category=history,
                )
                self.assertEqual(len(rows), 8)
                self.assertEqual(sum(len(row["focus_event_ids"]) for row in rows), 24)
                for row in rows:
                    category_id = row["category_id"]
                    focus = set(row["focus_event_ids"])
                    self.assertTrue(history.get(category_id, set()).isdisjoint(focus))
                    history.setdefault(category_id, set()).update(focus)
        self.assertTrue(all(len(values) == 12 for values in history.values()))


if __name__ == "__main__":
    unittest.main()
