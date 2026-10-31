
import argparse
from datetime import datetime, timezone
import json
import ipaddress
from pathlib import Path
import urllib.request
from protocol import validate_response


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Controller redirection is not permitted')


def validate_scope(targets, deadline, grant):

    start = datetime.fromisoformat(grant['started_utc'].replace('Z', '+00:00'))
    stop = datetime.fromisoformat(grant['traffic_stop_utc'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    if any(d.tzinfo is None for d in (start, stop, deadline)) or not start <= now < deadline <= stop:
        raise ValueError('Hardware access receipt or requested deadline is not current')
    if not targets or any(str(ipaddress.IPv4Address(host)) not in grant['target_ips'] for host in targets):
        raise ValueError('Target is outside the explicit bench scope')


def capture(targets, deadline, output, grant):
    validate_scope(targets, deadline, grant)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    output.mkdir(parents=True, exist_ok=False)
    for host in targets:
        data = {'target': host, 'started': datetime.now(timezone.utc).isoformat(), 'read_only': True}
        for ident, method in enumerate(('version', 'constantRead', 'configRead', 'statusRead', 'fileList', 'statisticRead'), 1):
            if datetime.now(timezone.utc).timestamp() + 5 >= deadline.timestamp():
                raise RuntimeError('Hardware access deadline reached')
            if method == 'version':
                req = urllib.request.Request('http://' + host + '/ver')
            else:
                message = {'req': method, 'id': ident}
                if method == 'fileList':
                    message['params'] = {'pattern': ['*.scn', '*.pl']}
                body = json.dumps(message, separators=(',', ':')).encode('ascii')
                req = urllib.request.Request('http://' + host + '/v1.9/?user=oper', data=body, headers={'Content-Type': 'application/json'})
            with opener.open(req, timeout=3) as response:
                result = json.loads(response.read(262144))
                if response.status != 200:
                    raise RuntimeError('Unexpected protocol response: ' + method)
                expected = {'req': method}
                if method != 'version':
                    expected['id'] = ident
                validate_response(result, expected)
                data[method] = result
            (output / (host + '.json')).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        data['completed'] = datetime.now(timezone.utc).isoformat()
        (output / (host + '.json')).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        version = data['version']['result']
        constants = data['constantRead']['result'].get('constant', {})
        stats = data['statisticRead']['result'].get('statistic', {})
        print(json.dumps({'target': host, 'model': version['prodName'], 'firmware': version['fwVer'], 'constants': constants.get('dev'), 'statistics': {key: stats.get(key) for key in ('dev', 'pixPwrOuts')}, 'mode': data['statusRead']['result'].get('status', {}).get('mode'), 'saved': data['configRead']['result'].get('saved')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture read-only PixLite bench evidence during an explicitly permitted session.')
    parser.add_argument('--target', action='append', required=True)
    parser.add_argument('--deadline', type=lambda s: datetime.fromisoformat(s), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grant', type=Path, required=True, help='Local receipt of fresh human permission with started_utc, traffic_stop_utc and target_ips')
    args = parser.parse_args()
    if args.deadline.tzinfo is None:
        parser.error('Deadline must include a timezone')
    capture(args.target, args.deadline, args.output, json.loads(args.grant.read_text(encoding='utf-8-sig')))
