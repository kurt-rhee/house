#!/usr/bin/env python3
"""Create plan previews and the finish schedule from the standard SVG/JSON exports."""
import csv
import json
import re
import subprocess
from pathlib import Path

output = Path(__file__).resolve().parents[1] / 'output'
svg = (output / 'floor-plan.svg').read_text()
(output / 'floor-plan-model.svg').write_text(svg)
for name, viewbox, width, height in [
    ('kitchen-layout', '16400 1950 7900 4650', 1580, 930),
    ('bathroom-layout', '18400 10250 4650 3350', 1395, 1005),
    ('bedroom-layout', '15800 6200 10600 7300', 1590, 1095),
    ('laundry-layout', '14700 3500 3100 3300', 1240, 1320),
]:
    preview = re.sub(r'<svg\b[^>]*>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" width="{width}" height="{height}">',
        svg, count=1)
    path = output / f'{name}.svg'
    path.write_text(preview)
    subprocess.run(['rsvg-convert', str(path), '-o', str(path.with_suffix('.png'))], check=True)
subprocess.run(['rsvg-convert', '-w', '2048', str(output / 'floor-plan.svg'),
                '-o', str(output / 'floor-plan.png')], check=True)
document = json.loads((output / 'floor-plan.house.json').read_text())
with (output / 'fixture-finishes.csv').open('w') as file:
    writer = csv.writer(file, lineterminator="\n")
    writer.writerow(['Fixture ID', 'Type', 'Width (mm)', 'Depth (mm)', 'Material', 'Style'])
    for fixture in document['fixtures'].values():
        if fixture.get('material') or fixture.get('style'):
            writer.writerow([fixture['id'], fixture['kind'], fixture['width'], fixture['depth'],
                             fixture.get('material', ''), fixture.get('style', '')])
print(f"Generated plan previews and finishes for revision {document['revision']}")
