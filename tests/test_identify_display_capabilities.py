#!/usr/bin/env python3
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin/identify-display-capabilities"
FIX = Path(__file__).resolve().parent / "fixtures"


def parse(edid: Path) -> dict:
    out = subprocess.check_output([str(BIN), "--edid", str(edid)], text=True)
    return json.loads(out)


class EdidCapabilities(unittest.TestCase):
    def test_edp_six_bit_no_cta(self):
        info = parse(FIX / "edid-edp1.bin")
        self.assertEqual(info["mfgId"], "CMN")
        self.assertEqual(info["productCode"], 0x14E7)
        self.assertEqual(info["bitDepth"], 6)
        self.assertEqual(info["videoInterface"], "DisplayPort")
        self.assertFalse(info["names"])
        self.assertIsNone(info["audio"])
        self.assertFalse(info["hdrStatic"])
        self.assertEqual(info["year"], 2020)

    def test_dp_ten_bit_cta_audio(self):
        info = parse(FIX / "edid-dp1.bin")
        self.assertEqual(info["mfgId"], "BOE")
        self.assertEqual(info["names"], ["Display"])
        self.assertEqual(info["serial"], "L56051794302")
        self.assertEqual(info["bitDepth"], 10)
        self.assertEqual(info["videoInterface"], "DisplayPort")
        self.assertEqual(info["rangeHz"], {"min": 40, "max": 65})
        self.assertEqual(info["audio"], [{"format": "LPCM", "channels": 2}])
        self.assertEqual(info["year"], 2025)
        self.assertTrue(info["srgbDefault"])

    def test_missing_is_empty_object(self):
        out = subprocess.check_output([str(BIN), "NO-SUCH-OUTPUT"], text=True)
        self.assertEqual(json.loads(out), {})


if __name__ == "__main__":
    unittest.main()
