import cProfile
import hashlib
import io
import json
from pathlib import Path
import pstats
import statistics
import time

from extractor_service.pdf_extractor import extract

files = sorted(Path('/source/.test-extractor/tests/stress/pdfs').glob('*.pdf'))
data = [(path.name, path.read_bytes()) for path in files]
for name, pdf in data:
    result = extract(pdf)
    timings = []
    for _ in range(7):
        start = time.perf_counter()
        extract(pdf)
        timings.append(time.perf_counter() - start)
    print(json.dumps({'file': name, 'pages': result.page_count, 'characters': len(result.content), 'sha256': hashlib.sha256(result.content.encode()).hexdigest(), 'median_seconds': statistics.median(timings), 'samples': timings}), flush=True)

profiler = cProfile.Profile()
profiler.enable()
for _, pdf in data:
    extract(pdf)
profiler.disable()
pstats.Stats(profiler).sort_stats('cumulative').print_stats(30)
