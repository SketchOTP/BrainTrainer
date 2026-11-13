"""Optional action success model: real matched feedback and portability."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples/persistent_individual'))
from self_model import SuccessModel


class SuccessModelTests(unittest.TestCase):
    def test_unrelated_and_cancelled_results_do_not_train(self):
        model = SuccessModel()
        plan = model.begin('act-1', 4, 'near', ('normal', 'effort'))
        before = model.to_dict()
        self.assertFalse(model.complete('different-id', 4, plan['mode'], True, cost=.1))
        self.assertFalse(model.complete('act-1', 5, plan['mode'], True, cost=.1))
        self.assertFalse(model.complete('act-1', 4, 'wrong-mode', True, cost=.1))
        self.assertEqual(before, model.to_dict())
        self.assertTrue(model.cancel('act-1'))
        self.assertEqual([], model.to_dict()['evidence'])
        self.assertFalse(model.complete('act-1', 4, plan['mode'], True))

    def test_pending_action_and_future_decisions_survive_json_roundtrip(self):
        model = SuccessModel()
        plan = model.begin('a', 4, 'near', ('normal', 'effort'))
        restored = SuccessModel.from_dict(json.loads(json.dumps(model.to_dict())))
        self.assertTrue(model.complete('a', 4, plan['mode'], False, cost=.04))
        self.assertTrue(restored.complete('a', 4, plan['mode'], False, cost=.04))
        self.assertEqual(model.to_dict(), restored.to_dict())
        for i in range(20):
            a = model.begin(str(i), 4, 'near', ('normal', 'effort'))
            b = restored.begin(str(i), 4, 'near', ('normal', 'effort'))
            self.assertEqual(a, b)
            model.complete(str(i), 4, a['mode'], i % 3 != 0, cost=.01)
            restored.complete(str(i), 4, b['mode'], i % 3 != 0, cost=.01)
        self.assertEqual(model.to_dict(), restored.to_dict())

    def test_learning_changes_effort_after_unannounced_body_change_and_recovery(self):
        model = SuccessModel()
        selected = []
        for i in range(240):
            p = model.begin(str(i), 4, 'visible-distance', ('normal', 'effort'))
            mode = p['mode']
            # Both modes work initially; only effort works under impairment;
            # neither hidden regime nor future outcome is supplied to the model.
            impaired = 60 <= i < 120
            success = not impaired or mode == 'effort'
            model.complete(str(i), 4, mode, success, cost=.2 if mode == 'effort' else 0.)
            selected.append(mode)
        self.assertGreater(selected[30:60].count('normal'), 20)
        self.assertGreater(selected[90:120].count('effort'), 20)
        self.assertGreater(selected[210:240].count('normal'), 20)

    def test_success_and_cost_predictions_are_isolated_by_observable_context(self):
        model = SuccessModel()
        for i in range(5):
            plan = model.begin(str(i), 4, 'near', ('normal',))
            model.complete(str(i), 4, plan['mode'], True, cost=.2)
        estimate = model.predict(4, 'near', 'normal')
        self.assertGreater(estimate['success_probability'], .5)
        self.assertAlmostEqual(estimate['mean_cost'], .2)
        self.assertEqual(model.predict(4, 'far', 'normal')['success_probability'], .5)
        self.assertIsNone(model.predict(4, 'far', 'normal')['mean_cost'])

    def test_bad_cost_and_duplicate_inflight_ids_are_rejected(self):
        model = SuccessModel()
        p = model.begin('same', 4, 'near', ('normal',))
        with self.assertRaises(ValueError):
            model.begin('same', 4, 'near', ('normal',))
        for invalid in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                model.complete('same', 4, p['mode'], True, cost=invalid)
        self.assertIn('same', model.pending)


if __name__ == '__main__':
    unittest.main()
