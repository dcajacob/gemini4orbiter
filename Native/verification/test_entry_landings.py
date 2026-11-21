"""Regression checks for the recorded same-save Gemini entry landings."""
import json
from pathlib import Path
import unittest

from gemini8.analyze_entry import verify


class LandingChecks(unittest.TestCase):
    def setUp(self):
        receipt = Path(__file__).parent / "gemini8/entry-comparison.json"
        self.cases = json.loads(receipt.read_text())["cases"]

    def test_qualified_flights(self):
        verify(self.cases)

    def test_first_contact_precedes_settling(self):
        for case in self.cases:
            with self.subTest(drag=case["drag"], bank=case["bank_up"]):
                contact = case["first_contact"]
                recorded = contact["airspeed_m_s"]
                contact["airspeed_m_s"] = 900
                with self.assertRaisesRegex(ValueError, "unexpected first contact"):
                    verify(self.cases)
                contact["airspeed_m_s"] = recorded

    def test_all_splashdowns_displaced(self):
        for case in self.cases:
            lon, lat = case["coordinates_lon_lat_deg"]
            case["coordinates_lon_lat_deg"] = [(lon + 270) % 360 - 180, lat]
        with self.assertRaisesRegex(ValueError, "splashdown .* from reference"):
            verify(self.cases)


if __name__ == "__main__":
    unittest.main()
