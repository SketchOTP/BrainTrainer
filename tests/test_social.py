import json
import math
import unittest

from creature_brain.social import SocialMemory


class SocialTests(unittest.TestCase):
    def test_identities_keep_slots_and_unknown_is_not_familiar(self):
        memory = SocialMemory()
        self.assertIsNone(memory.slot("stranger"))
        self.assertEqual(memory.opinion("stranger")["familiarity"], 0)
        alice = memory.observe("alice", positive=1)
        bob = memory.observe("bob", negative=1)
        self.assertNotEqual(alice["slot"], bob["slot"])
        self.assertEqual(memory.observe("alice")["slot"], alice["slot"])
        self.assertGreater(memory.opinion("alice")["affinity"], 0)
        self.assertLess(memory.opinion("bob")["affinity"], 0)
        self.assertGreater(memory.opinion("bob")["threat"], 0)

    def test_capacity_replaces_lru_slot_without_aliasing_old_identity(self):
        memory = SocialMemory(capacity=2)
        first = memory.observe("first")["slot"]
        memory.observe("second")
        memory.observe("first")
        replacement = memory.observe("third")
        self.assertEqual(memory.slot("first"), first)
        self.assertIsNone(memory.slot("second"))
        self.assertEqual(replacement["slot"], 1)
        self.assertEqual(len(memory.identities), 2)
        self.assertEqual(memory.opinion("third")["affinity"], 0)

    def test_social_events_are_identity_specific_and_separation_is_bond_dependent(self):
        memory = SocialMemory()
        for _ in range(20):
            memory.observe("friend", positive=1)
        memory.observe("neutral")
        self.assertEqual(memory.opinion("neutral")["affinity"], 0)
        self.assertEqual(memory.separation_distress(["friend"]), 0)
        self.assertGreater(memory.separation_distress([]), 0)
        memory.observe("foe", negative=1)
        self.assertGreater(memory.nearby_threat(["foe"]), 0)
        self.assertEqual(memory.nearby_threat(["friend"]), 0)

    def test_absence_removes_current_inputs_but_retains_history(self):
        memory = SocialMemory()
        memory.observe("friend", positive=1)
        self.assertEqual(len(memory.forf_inputs()), 36)
        self.assertGreater(sum(memory.forf_inputs()), 0)
        memory.advance(10, [])
        self.assertEqual(memory.forf_inputs(), [0.0] * 36)
        self.assertGreater(memory.opinion("friend")["affinity"], 0)
        self.assertFalse(memory.opinion("friend")["present"])

    def test_native_slot_capacity_reserves_final_forf_neuron(self):
        memory = SocialMemory()
        for index in range(35):
            memory.observe(f"creature-{index}")
        self.assertEqual(len(memory.identities), 35)
        self.assertEqual(len(memory.forf_inputs()), 36)
        self.assertEqual(memory.forf_inputs()[35], 0)
        self.assertEqual(sum(memory.forf_inputs()), 35)
        self.assertTrue(all(memory.slot(identity) < 35 for identity in memory.identities))
        with self.assertRaises(ValueError):
            SocialMemory(36)

    def test_checkpoint_preserves_identity_slots_and_dynamics(self):
        memory = SocialMemory()
        memory.observe("friend", positive=0.7)
        memory.observe("foe", negative=0.8)
        memory.advance(9, ["friend"])
        restored = SocialMemory.from_dict(json.loads(json.dumps(memory.to_dict())))
        for _ in range(10):
            memory.advance(1, ["foe"])
            restored.advance(1, ["foe"])
            self.assertEqual(memory.observe("foe", negative=0.1),
                             restored.observe("foe", negative=0.1))
        self.assertEqual(memory.to_dict(), restored.to_dict())

    def test_opinions_are_detached_and_invalid_input_cannot_create_slot(self):
        memory = SocialMemory()
        before = memory.to_dict()
        with self.assertRaises(ValueError):
            memory.observe("bad", negative=math.nan)
        self.assertEqual(before, memory.to_dict())
        row = memory.observe("friend", positive=0.5)
        row["affinity"] = -1
        self.assertGreater(memory.opinion("friend")["affinity"], 0)
        state = memory.to_dict()
        state["records"][0]["slot"] = 35
        with self.assertRaises(ValueError):
            SocialMemory.from_dict(state)


if __name__ == "__main__":
    unittest.main()
