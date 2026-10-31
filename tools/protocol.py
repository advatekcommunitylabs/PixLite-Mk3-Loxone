
import json
import math
import re


def integer(value, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError('Integer outside permitted range')
    return value


def request(name, params=None, ident=None):
    result = {'req': name}
    if ident is not None:
        result['id'] = integer(ident, 1, 4294967295)
    if params is not None:
        result['params'] = params
    return result


def encode(message):
    text = json.dumps(message, separators=(',', ':'), ensure_ascii=True)
    if '\\' in text:
        raise ValueError('API v1.9 JSON character escapes are not supported')
    return text


def filename(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9 _.-]{1,63}', value) or not value.endswith(('.scn', '.pl')):
        raise ValueError('Use an exact ASCII root scene or playlist filename')
    return value


def recall(file, fade_ms=0):
    return request('modePlayback', {'op': 'File', 'file': filename(file), 'cnt': 0, 'fadeMs': integer(fade_ms, 0, 4294967295)})


def colour(values, resolution='8Bit', fade_ms=0):
    if resolution not in ('8Bit', '16Bit') or len(values) not in (3, 4, 5):
        raise ValueError('Choose RGB, RGBW or RGBWX and a supported resolution')
    values = [integer(v, 0, 255 if resolution == '8Bit' else 65535) for v in values]
    return request('modePlayback', {'op': 'Color', 'color': values, 'colorRes': resolution, 'durMs': 0, 'fadeMs': integer(fade_ms, 0, 4294967295)})


def intensity(percent, output='Pix', priority=None):
    if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError('Intensity must be finite and between 0 and 100 percent')
    if not re.fullmatch(r'Pix|Aux:[1-9][0-9]*', output):
        raise ValueError('Invalid output')
    if priority not in (None, 'Lo', 'Hi'):
        raise ValueError('Invalid programmed priority')
    op = 'Set' if priority is None else priority + 'Set'
    return request('progInt', {'item': [{'out': output, 'op': op, 'fc': int(percent * 255 / 100 + .5), 'durMs': 0}]})


def dashboard_commands(scene='Example.scn', playlist='Example.pl', channels=3, palette=None):
    if channels not in (3, 4, 5):
        raise ValueError('Invalid channel count')
    commands = [('Live', request('modeLive')), ('Blank', request('modePlayback', {'op': 'Blank'})),
                ('Freeze', request('modePlayback', {'op': 'Freeze'})), ('Stop transient mode', request('modeCtrl', {'op': 'Stop'})),
                ('Recall scene', recall(scene)), ('Recall playlist', recall(playlist))]
    for label, op in [('Play', 'Play'), ('Pause', 'Paus'), ('Pause toggle', 'PausTog'), ('Restart item', 'Rst'),
                      ('Previous item', 'Prv'), ('Next item', 'Nxt'), ('Previous recording', 'PrvRec'), ('Next recording', 'NxtRec')]:
        commands.append((label, request('playbackCtrl', {'op': op})))
    for output in ['Pix', 'Aux:1']:
        for level in [0, 10, 25, 50, 75, 100]:
            commands.append((f'{output} intensity {level} percent', intensity(level, output)))
    defaults = [[255, 0, 0], [255, 128, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255],
                [128, 0, 255], [255, 0, 255], [255, 255, 255], [255, 240, 200], [235, 245, 255], [0, 0, 0]]
    for i, value in enumerate(palette if palette is not None else [v + [0] * (channels - 3) for v in defaults], 1):
        if len(value) != channels:
            raise ValueError('Palette does not match commissioned pixel colour type')
        commands.append((f'Palette {i}', colour(value)))
    commands.extend([('Read status', request('statusRead')), ('Read capabilities', request('constantRead')),
                     ('Read telemetry', request('statisticRead')), ('Read visible catalogue data', request('fileList', {'pattern': ['*.scn', '*.pl']}))])
    return commands


def validate_response(body, message):
    if not isinstance(body, dict) or body.get('resp') != message['req']:
        raise ValueError('Unexpected response type')
    if 'id' in message and (type(body.get('id')) is not int or body['id'] != message['id']):
        raise ValueError('Response ID mismatch')
    if 'error' in body:
        raise ValueError('Controller rejected request: ' + json.dumps(body['error']))
    if not isinstance(body.get('result'), dict):
        raise ValueError('Missing or invalid response result')
    return body['result']


def telemetry(constants, statistics):
    dev = constants.get('dev') or {}
    measured = statistics.get('dev') or {}
    temp = (measured.get('temp') or {}).get('current')
    temperature = temp if isinstance(temp, (int, float)) and not isinstance(temp, bool) and math.isfinite(temp) else None
    count = dev.get('pwrBanksIn', 0)
    volts = measured.get('bankVolt')
    banks = []
    if isinstance(count, int) and 0 <= count <= 255:
        banks = [(volts[i] / 1000 if isinstance(volts, list) and i < len(volts) and isinstance(volts[i], int) and not isinstance(volts[i], bool) and volts[i] >= 0 else None) for i in range(count)]
    powered = statistics.get('pixPwrOuts') if dev.get('pwrOut') is True else None
    ports = dev.get('pixPorts', 0)
    fuses = []
    if isinstance(powered, dict) and isinstance(ports, int) and 0 <= ports <= 255:
        good = powered.get('fuseGood')
        status = powered.get('stat')
        for i in range(ports):
            fuses.append({'port': i + 1, 'good': good[i] if isinstance(good, list) and i < len(good) and type(good[i]) is bool else None,
                          'status': status[i] if isinstance(status, list) and i < len(status) and status[i] in ('Good', 'Inactv', 'OvrCur', 'FuseBlwn') else None})
    return {'temperature_c': temperature, 'bank_voltages_v': banks, 'fuses': fuses,
            'power_telemetry_supported': dev.get('pwrOut') is True, 'validity': 'fresh response only; caller must expire after communication loss'}
