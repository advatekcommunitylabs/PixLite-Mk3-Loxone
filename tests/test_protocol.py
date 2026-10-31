import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from protocol import colour, dashboard_commands, encode, intensity, recall, request, telemetry, validate_response


class ProtocolTests(unittest.TestCase):
    def test_filename_rejections(self):
        for bad in ['../test.scn', 'café.scn', 'a".scn', 'a\\.scn', '*.scn', 'a.scn\n', 'a' * 64 + '.scn']:
            with self.subTest(bad=bad), self.assertRaises(ValueError): recall(bad)

    def test_order_and_indefinite_playback(self):
        self.assertEqual(encode(recall('Evening Show.pl', 100)), '{"req":"modePlayback","params":{"op":"File","file":"Evening Show.pl","cnt":0,"fadeMs":100}}')
        self.assertEqual(list(colour([1, 2, 3])['params']), ['op', 'color', 'colorRes', 'durMs', 'fadeMs'])

    def test_colour_and_intensity_bounds(self):
        for values in [[0, 0], [0, 0, 256], [True, 0, 0]]:
            with self.assertRaises(ValueError): colour(values)
        for bad in [float('nan'), float('inf'), -1, 101, True]:
            with self.assertRaises(ValueError): intensity(bad)
        self.assertEqual([intensity(v)['params']['item'][0]['fc'] for v in [0, 50, 100]], [0, 128, 255])
        self.assertEqual(intensity(50)['params']['item'][0]['op'], 'Set')

    def test_reject_false_success_and_wrong_response(self):
        for body in [{'resp': 'statusRead', 'id': 2}, {'resp': 'statusRead', 'id': 1, 'error': {'code': 4}}, {'resp': 'modeLive', 'id': 1}]:
            with self.assertRaises(ValueError): validate_response(body, request('statusRead', ident=1))

    def test_error_members_and_malformed_success_are_rejected(self):
        for error in [{}, [], None, False, 0, '']:
            with self.subTest(error=error), self.assertRaises(ValueError):
                validate_response({'resp': 'statusRead', 'id': 1, 'result': {}, 'error': error}, request('statusRead', ident=1))
        for body in [{'resp': 'statusRead', 'id': True, 'result': {}},
                     {'resp': 'statusRead', 'id': 1},
                     {'resp': 'statusRead', 'id': 1, 'result': []}]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                validate_response(body, request('statusRead', ident=1))
        self.assertEqual(validate_response({'resp': 'statusRead', 'id': 1, 'result': {}}, request('statusRead', ident=1)), {})

    def test_missing_power_is_unavailable(self):
        data = telemetry({'dev': {'pwrOut': False, 'pwrBanksIn': 0, 'pixPorts': 16}}, {'dev': {'temp': {'current': 28}, 'bankVolt': []}, 'pixPwrOuts': None})
        self.assertEqual(data['temperature_c'], 28)
        self.assertEqual(data['bank_voltages_v'], [])
        self.assertEqual(data['fuses'], [])

    def test_voltage_units_and_unknown_fuses(self):
        data = telemetry({'dev': {'pwrOut': True, 'pwrBanksIn': 2, 'pixPorts': 2}}, {'dev': {'bankVolt': [24200]}, 'pixPwrOuts': {'fuseGood': [False], 'stat': ['OvrCur']}})
        self.assertEqual(data['bank_voltages_v'], [24.2, None])
        self.assertIs(data['fuses'][0]['good'], False)
        self.assertIsNone(data['fuses'][1]['good'])
        self.assertIsNone(data['temperature_c'])

    def test_every_dashboard_request_is_ascii_json(self):
        for channels in [3, 4, 5]:
            commands = dashboard_commands(channels=channels)
            self.assertEqual(len(commands), 42)
            for title, body in commands: self.assertEqual(json.loads(encode(body)), body)


if __name__ == '__main__': unittest.main()
