#!/usr/bin/env python3
"""Dead dhcp/connecting must not stay 'waiting for sink IP' because a GO iface remains."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

import persist_idle_status as persist  # noqa: E402


class NextStatusTest(unittest.TestCase):
    def test_dead_dhcp_with_group_up_is_an_error(self):
        out = persist.next_status(
            {
                "phase": "dhcp",
                "message": "P2P up; waiting for sink IP / RTSP",
                "running": True,
                "pid": "99999999",
                "peer": "de:84:03:8d:51:17",
                "peerName": "hotyeah",
                "mode": "extend",
            },
            True,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out["phase"], "error")
        self.assertFalse(out["running"])
        self.assertIsNone(out["pid"])
        self.assertIn("before the sink got an IP", out["message"])
        self.assertEqual(out["peer"], "de:84:03:8d:51:17")

    def test_dead_connecting_with_group_up_is_an_error(self):
        out = persist.next_status(
            {"phase": "connecting", "running": True, "pid": "99999999", "mode": "extend"},
            True,
        )
        self.assertEqual(out["phase"], "error")
        self.assertFalse(out["running"])

    def test_dead_streaming_with_group_up_keeps_the_phase(self):
        out = persist.next_status(
            {
                "phase": "streaming",
                "message": "Extending",
                "running": True,
                "pid": "99999999",
            },
            True,
        )
        self.assertEqual(out["phase"], "streaming")
        self.assertFalse(out["running"])

    def test_live_pid_is_left_alone(self):
        out = persist.next_status(
            {"phase": "dhcp", "running": True, "pid": str(os.getpid())},
            True,
        )
        self.assertIsNone(out)

    def test_dead_dhcp_with_group_down_is_idle(self):
        out = persist.next_status(
            {"phase": "dhcp", "running": True, "pid": "99999999"},
            False,
        )
        self.assertEqual(out["phase"], "idle")
        self.assertEqual(out["message"], "Idle")


if __name__ == "__main__":
    unittest.main()
