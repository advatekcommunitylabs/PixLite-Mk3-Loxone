import unittest
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from capture_baseline import validate_scope


class BenchScopeTests(unittest.TestCase):
    def test_expired_receipt_fails_before_network_access(self):
        now = datetime.now(timezone.utc)
        receipt = {'started_utc': (now - timedelta(hours=2)).isoformat(),
                   'traffic_stop_utc': (now - timedelta(hours=1)).isoformat(),
                   'target_ips': ['192.0.2.1']}
        with self.assertRaises(ValueError):
            validate_scope(['192.0.2.1'], now + timedelta(minutes=1), receipt)

    def test_scope_cannot_be_extended_by_requested_deadline_or_target(self):
        now = datetime.now(timezone.utc)
        receipt = {'started_utc': (now - timedelta(minutes=1)).isoformat(),
                   'traffic_stop_utc': (now + timedelta(minutes=5)).isoformat(),
                   'target_ips': ['192.0.2.1']}
        for targets, deadline in [(['192.0.2.2'], now + timedelta(minutes=1)),
                                  (['192.0.2.1'], now + timedelta(minutes=10)),
                                  (['192.0.2.1/path'], now + timedelta(minutes=1))]:
            with self.subTest(targets=targets, deadline=deadline), self.assertRaises(ValueError):
                validate_scope(targets, deadline, receipt)
