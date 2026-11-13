"""Ordinary habitat offerings can lead to an experience-originated code revision."""
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/persistent_individual'))
from habitat import Habitat,DEVICES
from habitat_store import HabitatStore

class HabitatSelfDevelopmentTests(unittest.TestCase):
    def test_offered_lantern_initiates_revision_and_retains_it_on_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            h=Habitat(directory,180)
            try:
                for identity in ('object-0','object-1'):h.command('place',{'identity':identity,'x':0,'visible':False})
                h.command('device',{'function':'responsive-lantern'})
                before=h.creature.snapshot()
                for _ in range(30):
                    h.command('step',{})
                    if h.state()['revision_count']:break
                state=h.state();self.assertEqual(state['revision_count'],1)
                self.assertEqual(h.creature.snapshot()['events'][:len(before['events'])],before['events'])
                report=h.creature.self_review()['development_results'][0]
                self.assertEqual(report['origin'],'own-practice-review')
                self.assertTrue(report['request']['stop_decision']['inputs']['changes'])
                update=state['development_updates'][0]
                self.assertTrue(update['candidate_selected']);self.assertEqual(update['rejected_count'],1)
                self.assertEqual(update['lived_followup_status'],'retained-after-lived-outcome')
                self.assertGreaterEqual(update['accepted_test_count'],6)
                self.assertEqual(update['evidence_kind'],'branched-tests')
                restored=h.store.load();self.assertEqual(restored.snapshot(),h.creature.snapshot())
                for _ in range(5):self.assertEqual(restored.tick(),h.creature.tick())
            finally:h.store.close()

    def test_existing_patient_lantern_semantics_and_no_false_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            h=Habitat(directory,181)
            try:
                h.command('device',{'function':'delayed-switch'})
                toy=h.creature._host.objects['toy'];self.assertEqual(toy['delay'],4)
                self.assertEqual(toy['type_id'],'habitat-delayed-switch')
                self.assertEqual(h.state()['development_updates'],[])
                self.assertEqual([d['id'] for d in h.state()['device_catalog']],list(DEVICES))
                before=h.creature.snapshot()
                with self.assertRaises(ValueError):h.command('device',{'function':'unknown'})
                self.assertEqual(h.creature.snapshot(),before)
            finally:h.store.close()
