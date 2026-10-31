




import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import uuid
from protocol import dashboard_commands, encode


def uid():
    h = uuid.uuid4().hex
    return h[:8] + '-' + h[8:12] + '-' + h[12:16] + '-' + h[16:]


def read_native(path):
    text = path.read_text(encoding='utf-8-sig').replace(' 12hTF=', ' Lox12hTF=')


    text = re.sub(r'(\bCode=")([\s\S]*?)(")',
                  lambda m: m[1] + m[2].replace('\n', '&#10;') + m[3], text)
    return ET.ElementTree(ET.fromstring(text))


def remove_project_credentials(tree):

    for element in tree.iter():
        for key in ('APPKEY', 'APPID'):
            element.attrib.pop(key, None)
        for child in list(element):
            if child.tag == 'HP':
                element.remove(child)


def add_telemetry(document, connector):
    repository = Path(__file__).resolve().parents[1]
    source = (repository / 'native/telemetry_core.c').read_text(encoding='utf-8') + '\n'
    driver = (repository / 'native/telemetry_driver.c').read_text(encoding='utf-8')
    driver = driver.replace('#ifdef PXL_HOST_TEST\nvoid px_run() {\n#endif\n', '')
    driver = driver.replace('\n#ifdef PXL_HOST_TEST\n}\n#endif\n', '\n')
    source += driver
    command = ET.SubElement(connector, 'C', {'Type': 'VirtualOutCmd', 'IName': 'VQC43', 'V': '178', 'U': uid(),
        'Title': 'Telemetry JSON POST, read-only', 'Nio': '1', 'WF': '16384', 'Analog': 'true', 'NoEmpty': 'true',
        'CmdOn': '/v1.9/?user=oper', 'CmdOnHTTP': 'Content-Type: application/json', 'CmdOnPost': '<v>',
        'CmdOnMethod': '1', 'CmdAnswer': '/user/pixlite-telemetry.json', 'SourceValHigh': '1', 'DestValHigh': '1', 'Tx': 'true'})
    command_pin = ET.SubElement(command, 'Co', {'K': 'I', 'Nc': '1', 'U': uid()})
    ET.SubElement(command, 'Display', {'Unit': '<v>', 'StateOnly': 'true'})
    page = next(c for c in document.iter('C') if c.get('Type') == 'Page')
    script = ET.SubElement(page, 'C', {'Type': 'Code16', 'V': '178', 'U': uid(), 'Title': 'PixLite telemetry, enable after commissioning',
        'Px': '3600', 'Py': '3000', 'Px2': '6288', 'Py2': '6960', 'Cl': '141,255,112', 'Nio': '34', 'Code': source, 'Task': '1'})
    keys = ['TI1', 'TI2', 'TI3'] + [f'AI{i}' for i in range(1, 14)] + ['Remanence', 'TQ1', 'TQ2', 'TQ3'] + [f'AQ{i}' for i in range(1, 14)] + ['TeQ']
    pins = {key: uid() for key in keys}
    for key in keys:
        ET.SubElement(script, 'Co', {'K': key, 'U': pins[key]})


    output = ET.SubElement(page, 'C', {'Type': 'OutputRef', 'V': '178', 'U': uid(), 'Title': 'Telemetry JSON POST, read-only',
        'Px': '7400', 'Py': '3200', 'Px2': '9512', 'Py2': '3392', 'Cl': '238,238,238', 'Nio': '2',
        'Ref': command.get('U'), 'WF': '131072', 'Analog': 'true', 'Text': 'true', 'LinkRefType': '74'})
    pin = ET.SubElement(output, 'Co', {'K': 'AI', 'Nc': '1', 'U': uid()})
    ET.SubElement(pin, 'In', {'Input': pins['TQ1']})
    output_pin = ET.SubElement(output, 'Co', {'K': 'AQ', 'U': uid()})
    ET.SubElement(command_pin, 'In', {'Input': output_pin.get('U')})


def build(baseline, output, channels=3, telemetry=False):


    tree = read_native(baseline)
    document = tree.getroot().find('C')
    populated = any(c.get('Type') in ('VirtualOut', 'VirtualOutCmd') for c in document.iter('C'))
    populated |= any(c.get('Type') not in ('Program', 'Page')
                     for program in document.iter('C') if program.get('Type') == 'Program'
                     for c in program.iter('C'))
    if populated:
        raise ValueError('Use a new empty Config project, not a populated installation')
    remove_project_credentials(tree)
    document.set('Title', 'PixLite SHOWTime experimental commands')
    caption = next(c for c in document.iter('C') if c.get('Type') == 'VirtualOutCaption')
    for child in list(caption): caption.remove(child)
    connector = ET.SubElement(caption, 'C', {'Type': 'VirtualOut', 'IName': 'VQ1', 'V': '178', 'U': uid(),
                    'Title': 'PixLite Mk3 HTTP(S) experimental', 'WF': '16384', 'Address': 'https://127.0.0.1:4443', 'CloseAfterSend': 'true'})
    for i, (title, message) in enumerate(dashboard_commands(channels=channels), 1):
        command = ET.SubElement(connector, 'C', {'Type': 'VirtualOutCmd', 'IName': f'VQC{i}', 'V': '178', 'U': uid(), 'Title': title,
                    'Nio': '1', 'WF': '16400', 'CmdOn': '/v1.9/?user=oper', 'CmdOnHTTP': 'Content-Type: application/json',
                    'CmdOnPost': encode(message), 'CmdOnMethod': '1', 'CmdOff': '', 'CmdOffHTTP': '', 'CmdOffPost': '',
                    'SourceValHigh': '1', 'DestValHigh': '1', 'Tx': 'false'})
        ET.SubElement(command, 'Co', {'K': 'I', 'U': uid()})
        ET.SubElement(command, 'Display', {'Unit': '<v>', 'StateOnly': 'true'})
    if telemetry:
        add_telemetry(document, connector)
        document.set('Title', 'PixLite native telemetry experimental')
    tree.getroot().set('NextObj', '47' if telemetry else '43')
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space='\t')
    result = ET.tostring(tree.getroot(), encoding='unicode').replace(' Lox12hTF=', ' 12hTF=').replace('&#10;', '\n')
    output.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + result + '\n', encoding='utf-8')
    return len(dashboard_commands(channels=channels)) + int(telemetry)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build an experimental native Config project from a new empty Config export.')
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--channels', type=int, choices=[3, 4, 5], default=3)
    parser.add_argument('--telemetry', action='store_true', help='Include the disabled experimental native polling Program and read-only HTTP link')
    args = parser.parse_args()
    print('Generated', build(args.baseline, args.output, args.channels, args.telemetry), 'native commands. Runtime validation required; telemetry enable and MAC remain unwired.')
