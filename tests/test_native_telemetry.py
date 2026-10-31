




import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

EXE = os.environ.get('PXL_NATIVE_CORE_EXE')
DRIVER_EXE = os.environ.get('PXL_NATIVE_DRIVER_EXE')
MAC = '000000000001'


@unittest.skipUnless(EXE, 'Set PXL_NATIVE_CORE_EXE to the compiled local decoder adapter')
class NativeTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.cap = {'resp': 'constantRead', 'id': 201, 'result': {'constant': {'dev': {
            'macAddr': MAC, 'pixPorts': 4, 'pwrBanksIn': 1, 'pwrOut': True}}}}
        self.stats = {'resp': 'statisticRead', 'id': 202, 'result': {'statistic': {
            'dev': {'temp': {'current': 27.25}, 'bankVolt': [24203]},
            'pixPwrOuts': {'fuseGood': [True, False, True], 'stat': ['Good', 'OvrCur', 'FuseBlwn', 'Inactv']}}}}

    def run_decoder(self, cap=None, stats=None, mac=MAC):
        def encode(value):
            return value if isinstance(value, str) else json.dumps(value, separators=(',', ':'))
        with tempfile.TemporaryDirectory() as folder:
            c = Path(folder) / 'cap.json'
            s = Path(folder) / 'stats.json'
            c.write_text(encode(self.cap if cap is None else cap), encoding='utf-8')
            s.write_text(encode(self.stats if stats is None else stats), encoding='utf-8')
            result = subprocess.run([EXE, str(c), str(s), mac, '201', '202'], capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

    def test_units_and_separate_fuse_semantics(self):
        result = self.run_decoder()
        self.assertEqual(result['accepted'], 1)
        self.assertAlmostEqual(result['temperature'], 27.25)
        self.assertAlmostEqual(result['bank_values'][0], 24.203, places=5)
        self.assertEqual(result['fuse_good'], [1, 0, 1, -1])
        self.assertEqual(result['fuse_state'], [0, 2, 3, 1])

    def test_signal_only_device_does_not_report_healthy_fuses(self):
        self.cap['result']['constant']['dev'].update(pixPorts=16, pwrBanksIn=0, pwrOut=False)
        self.stats['result']['statistic'].update(pixPwrOuts=None)
        self.stats['result']['statistic']['dev']['bankVolt'] = []
        result = self.run_decoder()
        self.assertEqual(result['accepted'], 1)
        self.assertEqual(result['fuse_good'], [])
        self.assertEqual(result['bank_values'], [])

    def test_wrong_identity_and_response_id_are_rejected(self):
        self.assertEqual(self.run_decoder(mac='000000000002')['accepted'], 0)
        numeric_mac = json.loads(json.dumps(self.cap))
        numeric_mac['result']['constant']['dev']['macAddr'] = 123456789012
        self.assertEqual(self.run_decoder(cap=numeric_mac, mac='123456789012')['accepted'], 0)
        self.stats['id'] = 201
        self.assertEqual(self.run_decoder()['accepted'], 0)

    def test_json_error_inside_http_success_is_rejected(self):
        self.stats['error'] = {'code': 4}
        self.assertEqual(self.run_decoder()['accepted'], 0)

    def test_duplicate_members_and_nested_spoofs_are_rejected(self):
        raw = json.dumps(self.stats, separators=(',', ':')).replace('"id":202', '"id":202,"id":202')
        self.assertEqual(self.run_decoder(stats=raw)['accepted'], 0)
        self.assertEqual(self.run_decoder(stats={'wrapper': self.stats})['accepted'], 0)

    def test_truncation_trailing_junk_and_bad_grammar(self):
        raw = json.dumps(self.stats, separators=(',', ':'))
        for bad in [raw[:-1], raw + '{}', raw.replace('202', '0202', 1), raw.replace('202', '202.', 1),
                    raw.replace('202', '202e', 1), raw.replace('202', 'true', 1), raw.replace('202', '-1', 1)]:
            with self.subTest(bad=bad):
                self.assertEqual(self.run_decoder(stats=bad)['accepted'], 0)

    def test_missing_measurements_are_unavailable(self):
        self.stats['result']['statistic'] = {}
        result = self.run_decoder()
        self.assertEqual(result['accepted'], 1)
        self.assertEqual(result['temp_valid'], 0)
        self.assertEqual(result['bank_values'], [None])
        self.assertEqual(result['fuse_good'], [-1] * 4)

    def test_wrong_types_and_nonfinite_values_are_not_measurements(self):
        self.stats['result']['statistic']['dev'].update(temp={'current': True}, bankVolt=[True])
        self.stats['result']['statistic']['pixPwrOuts'] = {'fuseGood': [1], 'stat': ['bad']}
        result = self.run_decoder()
        self.assertEqual(result['temp_valid'], 0)
        self.assertEqual(result['bank_values'], [None])
        self.assertEqual(result['fuse_good'], [-1] * 4)
        raw = json.dumps(self.stats).replace('"current": true', '"current": 1e999')
        self.assertEqual(self.run_decoder(stats=raw)['temp_valid'], 0)

    def test_capability_bounds_and_types(self):
        for key, value in [('pixPorts', 33), ('pixPorts', 0), ('pwrBanksIn', 9), ('pwrOut', 1)]:
            with self.subTest(key=key, value=value):
                cap = json.loads(json.dumps(self.cap))
                cap['result']['constant']['dev'][key] = value
                self.assertEqual(self.run_decoder(cap=cap)['accepted'], 0)

    def test_escaped_strings_are_rejected_as_a_whole(self):
        raw = json.dumps(self.stats).replace('"Good"', '"G\\u006fod"')
        self.assertEqual(self.run_decoder(stats=raw)['accepted'], 0)

    def test_depth_and_token_limits_are_bounded(self):
        nested = '[]'
        for _ in range(15):
            nested = '[' + nested + ']'
        raw = json.dumps(self.stats, separators=(',', ':'))[:-1] + ',"extra":' + nested + '}'
        self.assertEqual(self.run_decoder(stats=raw)['accepted'], 0)
        raw = json.dumps(self.stats, separators=(',', ':'))[:-1] + ',"extra":[' + ','.join(['0'] * 256) + ']}'
        self.assertEqual(self.run_decoder(stats=raw)['accepted'], 0)


@unittest.skipUnless(DRIVER_EXE, 'Set PXL_NATIVE_DRIVER_EXE to the compiled local driver adapter')
class NativeLifecycleTests(unittest.TestCase):
    def test_polling_lifecycle_contract(self):
        for scenario in range(14):
            with self.subTest(scenario=scenario):
                result = subprocess.run([DRIVER_EXE, str(scenario)], capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['passed'], 1)
