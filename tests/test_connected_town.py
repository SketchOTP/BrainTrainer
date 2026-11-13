from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples/persistent_individual/interactive_art/v1'))
from build_connected_town import TRAILS_V10, validate_connected_town
from build_natural_town import make_natural_pack


class ConnectedTownTests(unittest.TestCase):
    def test_paths_connect_doors_and_pond_bank_without_crossing_water(self):
        pack = make_natural_pack(trails=TRAILS_V10)
        self.assertEqual(validate_connected_town(pack), 44)


if __name__ == '__main__':
    unittest.main()
