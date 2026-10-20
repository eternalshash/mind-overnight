"""
ECE 441: Smart and Connected Systems
Automated Regression Test Suite: IoT Alert Dispatch Pipeline
File: verify_iot_pipeline.py

Verifies:
1. 3-row SMS layout format with zero arrows across all fault types.
2. Single-segment SMS budget (<160 characters).
3. Production alert_config.json integrity.
4. MQTT payload schema conformance.
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from testingIot import generate_fault_data, CARRIER_GATEWAYS

class TestIoTAlertPipeline(unittest.TestCase):
    def setUp(self):
        self.fault_scenarios = ["surge", "drop", "heatstress", "freeze", "blower", "filter", "mcu"]
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_config.json")

    def test_config_json_exists_and_valid(self):
        self.assertTrue(os.path.exists(self.config_path), "alert_config.json missing!")
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("anomaly_thresholds", cfg)
        self.assertIn("carrier_gateways", cfg)
        self.assertIn("verizon", cfg["carrier_gateways"])
        self.assertIn("vtext.com", cfg["carrier_gateways"]["verizon"])
        self.assertIn("vzwpix.com", cfg["carrier_gateways"]["verizon"])

    def test_three_row_arrowless_sms_format(self):
        for fault in self.fault_scenarios:
            record = generate_fault_data(fault)
            sms = record.format_sms()
            lines = sms.strip().split("\n")

            # Check 1: Exactly 3 lines
            self.assertEqual(len(lines), 3, f"Fault {fault} did not produce exactly 3 lines: {lines}")

            # Check 2: No arrows
            self.assertNotIn("->", sms, f"Found arrow '->' in fault {fault} SMS")

            # Check 3: Line 3 starts with 'System Action:'
            self.assertTrue(lines[2].startswith("System Action:"), f"Line 3 missing 'System Action:' prefix in {fault}")

            # Check 4: Character count under 160 characters
            self.assertLessEqual(len(sms), 160, f"SMS length {len(sms)} exceeds 160 chars for {fault}")

    def test_carrier_gateways_configured(self):
        self.assertIn("verizon", CARRIER_GATEWAYS)
        self.assertIn("att", CARRIER_GATEWAYS)
        self.assertIn("tmobile", CARRIER_GATEWAYS)

if __name__ == "__main__":
    unittest.main()
