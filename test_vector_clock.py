"""Pruebas unitarias de las reglas del reloj vectorial."""

import unittest

from vector_clock import VectorClock


class VectorClockTest(unittest.TestCase):
    def test_local_event_increments_own_component(self):
        clock = VectorClock(["A", "B", "C"], "A")
        clock.increment()
        self.assertEqual(clock.copy(), {"A": 1, "B": 0, "C": 0})

    def test_receive_uses_max_then_increments(self):
        clock = VectorClock(["A", "B", "C"], "B")
        clock.increment()
        clock.on_receive({"A": 3, "B": 0, "C": 1})
        self.assertEqual(clock.copy(), {"A": 3, "B": 2, "C": 1})

    def test_happens_before_and_concurrent(self):
        e1 = {"A": 1, "B": 0, "C": 0}
        e2 = {"A": 2, "B": 1, "C": 0}
        e3 = {"A": 0, "B": 0, "C": 1}
        self.assertTrue(VectorClock.happens_before(e1, e2))
        self.assertTrue(VectorClock.concurrent(e1, e3))

    def test_set_values_edits_only_given_positions(self):
        clock = VectorClock(["A", "B", "C"], "A")
        clock.increment()
        clock.set_values({"B": 4, "C": 2})
        self.assertEqual(clock.copy(), {"A": 1, "B": 4, "C": 2})
        clock.on_receive({"A": 0, "B": 1, "C": 7})
        self.assertEqual(clock.copy(), {"A": 2, "B": 4, "C": 7})

    def test_set_values_rejects_invalid_input(self):
        clock = VectorClock(["A", "B", "C"], "A")
        for malo in ({"D": 1}, {"A": -1}, {"A": "3"}, {"A": 1.5}, {"A": True}):
            with self.assertRaises(ValueError):
                clock.set_values(malo)
        self.assertEqual(clock.copy(), {"A": 0, "B": 0, "C": 0})


if __name__ == "__main__":
    unittest.main()
