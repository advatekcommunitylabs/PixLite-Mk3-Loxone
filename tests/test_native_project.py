
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_native import build, read_native


class NativeProjectTests(unittest.TestCase):
    def test_project_credentials_are_not_distributed(self):
        with tempfile.TemporaryDirectory() as folder:
            baseline = Path(folder) / 'blank.Loxone'
            output = Path(folder) / 'generated.Loxone'
            baseline.write_text('<ControlList APPKEY="example"><C Type="Document" APPID="example">'
                                '<HP H="example" S="example" /><C Type="VirtualOutCaption" />'
                                '<C Type="Program"><C Type="Page" /></C></C></ControlList>', encoding='utf-8')
            self.assertEqual(build(baseline, output), 42)
            sample = read_native(output)
            self.assertFalse(any(key in c.attrib for c in sample.iter() for key in ('APPKEY', 'APPID')))
            self.assertFalse(list(sample.iter('HP')))
        for path in (ROOT / 'examples').glob('*.Loxone'):
            tree = read_native(path)
            self.assertFalse(any(key in c.attrib for c in tree.iter() for key in ('APPKEY', 'APPID')), str(path))
            self.assertFalse(list(tree.iter('HP')), str(path))

    def test_script_text_and_disabled_inputs_survive_native_format(self):
        root = read_native(ROOT / 'examples/PixLite-SHOWTime-Telemetry-DRAFT.Loxone').getroot()
        script = next(c for c in root.iter('C') if c.get('Type') == 'Code16')
        core = (ROOT / 'native/telemetry_core.c').read_text(encoding='utf-8')
        driver = (ROOT / 'native/telemetry_driver.c').read_text(encoding='utf-8')
        driver = driver.replace('#ifdef PXL_HOST_TEST\nvoid px_run() {\n#endif\n', '')
        driver = driver.replace('\n#ifdef PXL_HOST_TEST\n}\n#endif\n', '\n')
        self.assertEqual(script.get('Code'), core + '\n' + driver)
        self.assertIn('\n#define PX_BYTES 4096\n', script.get('Code'))
        self.assertNotIn('PXL_HOST_TEST', script.get('Code'))
        for key in ['AI1', 'TI1']:
            self.assertFalse(list(next(c for c in script if c.get('K') == key)))

    def test_only_the_read_only_text_command_is_wired(self):
        root = read_native(ROOT / 'examples/PixLite-SHOWTime-Telemetry-DRAFT.Loxone').getroot()
        commands = [c for c in root.iter('C') if c.get('Type') == 'VirtualOutCmd']
        self.assertEqual(len(commands), 43)
        wired = [c for c in commands if list(c.iter('In'))]
        self.assertEqual(len(wired), 1)
        poll = wired[0]
        self.assertEqual(poll.get('CmdOnPost'), '<v>')
        self.assertEqual(poll.get('CmdOnMethod'), '1')
        self.assertEqual(poll.get('NoEmpty'), 'true')
        self.assertEqual(poll.get('Tx'), 'true')
        self.assertEqual(poll.get('CmdAnswer'), '/user/pixlite-telemetry.json')
        connector = next(c for c in root.iter('C') if c.get('Type') == 'VirtualOut')
        self.assertEqual(connector.get('Address'), 'https://127.0.0.1:4443')
        script = next(c for c in root.iter('C') if c.get('Type') == 'Code16')
        source = next(c for c in script if c.get('K') == 'TQ1').get('U')
        output = next(c for c in root.iter('C') if c.get('Type') == 'OutputRef')
        self.assertEqual(next(output.iter('In')).get('Input'), source)
