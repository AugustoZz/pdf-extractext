"""Verify saved limits/profiles and compare live extraction with the baseline."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

root = Path('/app')
folder = root / 'output/refactor-2026-10-08'
checks = []
for run in ('before', 'after-1', 'after-2'):
    path = folder / run
    services = json.loads((path / 'services.json').read_text(encoding='utf-8-sig'))
    assert len(services) == 6
    workers = [s for s in services if '-extractor-lb-' not in s['Name']]
    assert len(workers) == 5
    for service in workers:
        assert service['HostConfig']['NanoCpus'] == 1_000_000_000
        assert service['HostConfig']['Memory'] == 1024**3
        assert not service['State']['OOMKilled']
    lb = next(s for s in services if '-extractor-lb-' in s['Name'])
    assert lb['HostConfig']['NanoCpus'] == 1_000_000_000
    assert lb['HostConfig']['Memory'] == 512 * 1024**2
    assert lb['HostConfig']['PortBindings']['443/tcp'][0]['HostPort'] == '443'
    assert lb['HostConfig']['PortBindings']['80/tcp'][0]['HostPort'] == '8080'
    for tool, cpu, ram in (('k6', 2_000_000_000, 3*1024**3), ('vegeta', 1_000_000_000, 1024**3)):
        meta = json.loads(next(path.glob(f'carga-{tool}-*.json')).read_text(encoding='utf-8-sig'))
        if isinstance(meta, list):
            meta = meta[0]
        assert meta['HostConfig']['NanoCpus'] == cpu
        assert meta['HostConfig']['Memory'] == ram
        assert meta['State']['ExitCode'] == 0 and not meta['State']['OOMKilled']
    k6 = json.loads((path / 'corregido-k6.json').read_text())
    vegeta = json.loads((path / 'profesor-vegeta.json').read_text())
    assert k6['metrics']['vus']['max'] == 100
    assert k6['metrics']['http_req_failed']['value'] == 0
    assert vegeta['requests'] == 1500 and 49.9 < vegeta['rate'] < 50.1
    assert 29.9 < vegeta['duration']/1e9 < 30.1
    assert vegeta['status_codes'] == {'200': 1500}
    assert len(json.loads((path / 'pdf-hashes.json').read_text(encoding='utf-8-sig'))) == 4
    checks.append({'run': run, 'limits_and_observed_profiles': True, 'all_http_200': True})

expected_hashes = {
    '2020-Scrum-Guide-Spanish-Latin-South-American.pdf': '6bbff3f361e52016cbb75a72671f1b31b5e043fdc1cc3f022f1b15a32795a256',
    'Essential-Kanban-Condensed-Spanish.pdf': '257f73b908420ac5c78852fb8673beb683a8ca0c05d2e6a82b5e9629f6ad7be8',
    'Filosofia Lean.pdf': 'c77b55bd68477ecc0d96074ea4606bffe5802a1c8a241a725f6eb358be17ce40',
    'scrum_manager_historias_usuario.pdf': '30efd6fcd0c022665676edcf164feb28e6b43dcce53ab9738550b99d70f5fd84',
}
baseline = json.loads((folder / 'baseline.json').read_text())
for expected in baseline:
    data = (root / '.test-extractor/tests/stress/pdfs' / expected['name']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected_hashes[expected['name']]
    request = Request('http://extractor-lb/extract', data, {'Content-Type': 'application/pdf'})
    with urlopen(request, timeout=30) as response:
        assert response.status == 200
        result = json.load(response)
    assert set(result) == {'content', 'page_count'}
    assert result['page_count'] == expected['pages']
    assert hashlib.sha256(result['content'].encode()).hexdigest() == expected['sha256']
    checks.append({'pdf': expected['name'], 'official_input_hash': True, 'identical_markdown_and_pages': True})

for url in ('http://extractor-lb/health', 'http://127.0.0.1:8000/web/index.html'):
    with urlopen(url, timeout=10) as response:
        assert response.status == 200
    checks.append({'restored_endpoint': url, 'status': 200})
(folder / 'verification.json').write_text(json.dumps(checks, indent=2))
print(json.dumps(checks, indent=2))
