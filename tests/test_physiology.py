import json
import math
import unittest

from creature_brain.physiology import DRIVE_CHEMICAL_IDS, Physiology, PhysiologyConfig


class PhysiologyTests(unittest.TestCase):
    def test_twenty_drives_and_verified_chemical_channels(self):
        body = Physiology()
        drives, chemicals = body.drives, body.chemicals
        self.assertEqual(len(drives), 20)
        self.assertEqual(len(chemicals), 256)
        self.assertEqual([chemicals[i] for i in DRIVE_CHEMICAL_IDS], drives)
        self.assertTrue(all(0 <= value <= 1 for value in chemicals))
        body.ingest(starch=0.2)
        self.assertGreater(body.chemicals[204], 0)
        body.hurt(0.3)
        self.assertGreater(body.chemicals[205], 0)
        drives[0] = 999
        self.assertLessEqual(body.drives[0], 1)

    def test_metabolism_raises_separate_hungers_and_food_relieves_them(self):
        body = Physiology()
        before = body.drives
        body.step(300, effort=0.7)
        hungry = body.drives
        self.assertGreater(hungry[1], before[1])
        self.assertGreater(hungry[2], before[2])
        self.assertGreater(hungry[3], before[3])
        body.ingest(protein=0.5, starch=0.5, fat=0.5)
        self.assertLess(body.drives[1], hungry[1])
        self.assertLess(body.drives[2], hungry[2])
        self.assertLess(body.drives[3], hungry[3])

    def test_temperature_changes_drive_and_can_damage_body(self):
        cold, warm, hot = Physiology(), Physiology(), Physiology()
        cold.step(400, ambient_temperature=-40)
        warm.step(400, ambient_temperature=22)
        hot.step(400, ambient_temperature=80)
        self.assertGreater(cold.drives[4], warm.drives[4])
        self.assertGreater(hot.drives[5], warm.drives[5])
        self.assertLess(cold.temperature, warm.temperature)
        self.assertGreater(hot.temperature, warm.temperature)
        self.assertLess(cold.health, warm.health)
        self.assertLess(hot.health, warm.health)

    def test_sleep_cycles_rem_and_recovers_then_wakes(self):
        body = Physiology()
        body.fatigue, body.sleep_debt = 0.7, 0.7
        self.assertTrue(body.request_sleep())
        body.step(29)
        self.assertEqual(body.sleep_state, "nrem")
        self.assertGreater(body.chemicals[212], 0)
        body.step(1)
        self.assertEqual(body.sleep_state, "rem")
        self.assertEqual(body.chemicals[213], 1)
        body.step(15)
        self.assertEqual(body.sleep_state, "nrem")
        self.assertLess(body.fatigue, 0.7)
        self.assertLess(body.sleep_debt, 0.7)
        body.step(700)
        self.assertEqual(body.sleep_state, "awake")
        self.assertEqual(body.last_wake_reason, "recovered")

    def test_pain_and_threat_wake_sleeping_creature(self):
        body = Physiology()
        body.request_sleep()
        body.hurt(0.4)
        self.assertEqual(body.sleep_state, "awake")
        self.assertEqual(body.last_wake_reason, "pain")
        body.soothe(1)
        self.assertTrue(body.request_sleep())
        body.step(1, threat=0.8)
        self.assertEqual(body.sleep_state, "awake")
        self.assertFalse(body.request_sleep())
        self.assertEqual(body.last_wake_reason, "threat")

    def test_real_deprivation_deteriorates_and_dies_without_resurrection(self):
        body = Physiology()
        body.protein = body.starch = body.fat = body.energy = 0
        body.step(3000)
        self.assertFalse(body.alive)
        self.assertEqual(body.health, 0)
        self.assertEqual(body.death_reason, "starvation")
        body.ingest(protein=1, starch=1, fat=1)
        self.assertFalse(body.alive)
        self.assertFalse(body.request_sleep())

    def test_social_events_and_separation_affect_drives_without_proximity_reward(self):
        body = Physiology()
        body.step(60, nearby_creatures=0, separation=0.8)
        lonely = body.drives[8]
        self.assertGreaterEqual(lonely, 0.64)
        self.assertEqual(body.reward, 0)
        body.interact(positive=1)
        self.assertGreater(body.reward, 0)
        body.step(60, nearby_creatures=1)
        self.assertLess(body.drives[8], lonely)
        angry = body.drives[12]
        body.interact(negative=1)
        self.assertGreater(body.drives[12], angry)
        self.assertGreater(body.drives[10], 0)

    def test_checkpoint_retains_sleep_clock_and_exact_continuation(self):
        body = Physiology()
        body.request_sleep()
        body.step(13, ambient_temperature=12, nearby_creatures=1)
        copy = Physiology.from_dict(json.loads(json.dumps(body.to_dict())))
        for _ in range(50):
            self.assertEqual(body.step(1, ambient_temperature=10),
                             copy.step(1, ambient_temperature=10))
        self.assertEqual(body.to_dict(), copy.to_dict())

    def test_integer_batched_steps_match_single_second_steps(self):
        batch, singles = Physiology(), Physiology()
        batch.step(20, effort=0.3)
        for _ in range(20):
            singles.step(1, effort=0.3)
        self.assertEqual(batch.to_dict(), singles.to_dict())

    def test_invalid_inputs_preserve_state(self):
        body = Physiology()
        before = body.to_dict()
        for amount in (math.nan, math.inf, -1):
            with self.assertRaises(ValueError):
                body.step(amount)
        with self.assertRaises(ValueError):
            body.step(1, nearby_creatures=-1)
        with self.assertRaises(ValueError):
            body.step(1, threat=1.1)
        self.assertEqual(before, body.to_dict())


if __name__ == "__main__":
    unittest.main()
