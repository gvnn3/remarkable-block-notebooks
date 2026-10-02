#!/usr/bin/env python3
"""Build RCU RMT archives from SVG masters and device-specific PNG assets."""
import argparse
import base64
import io
import json
import struct
import tarfile
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

NAMESPACE = uuid.UUID('c956cffb-c224-4cac-8a22-74f344bbbc0e')
DEVICES = ('remarkable-pure', 'remarkable-pro-move', 'remarkable-paper-pro')

def png_svg(path):
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'Invalid PNG: {path}')
    w, h = struct.unpack('>II', data[16:24])
    encoded = base64.b64encode(data).decode('ascii')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{encoded}"/>'
            '</svg>').encode(), w, h

def package(source, root, output):
    relative = source.relative_to(root)
    if source.suffix == '.png':
        svg, w, h = png_svg(source)
    else:
        svg = source.read_bytes()
        element = ET.fromstring(svg)
        _, _, w, h = map(float, element.attrib['viewBox'].split())
    ET.fromstring(svg)
    category = 'Life/organize' if ('toc' in source.stem or 'inhalt' in source.stem) else 'Creative' if 'cover' in source.stem else 'Grids'
    device = relative.parent.as_posix()
    name = f'{device if device != "." else "Common"}: {source.stem.replace("_", " ").replace("-", " ")}'
    metadata = {'name': name, 'fileName': str(uuid.uuid5(NAMESPACE, relative.as_posix())),
                'categories': [category], 'iconCode': '\ue9d5', 'landscape': w > h}
    if relative.as_posix() == 'remarkable-pure/pure-mechanical-grid-1mm.svg':
        metadata['fileName'] = '556786a1-0db0-478c-b5cc-1db11d80ba3d'
        metadata['name'] = 'Mechanical Grid - 1 mm'
    target = output / relative.with_suffix('.rmt')
    target.parent.mkdir(parents=True, exist_ok=True)
    payloads = {'template.json': json.dumps(metadata, indent=2, ensure_ascii=True).encode(), 'template.svg': svg}
    with tarfile.open(target, 'w', format=tarfile.USTAR_FORMAT) as archive:
        for filename, data in payloads.items():
            info = tarfile.TarInfo(filename)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    with tarfile.open(target) as archive:
        assert archive.getnames() == list(payloads)
        for filename, data in payloads.items():
            assert archive.extractfile(filename).read() == data
    return {'source': relative.as_posix(), 'package': target.relative_to(output).as_posix(),
            'width': w, 'height': h, 'type': 'vector SVG' if source.suffix == '.svg' else 'embedded PNG', **metadata}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root
    sources = sorted(root.glob('*.svg'))
    for device in DEVICES:
        sources += sorted((root/device).glob('*.png'))
        sources += sorted((root/device).glob('*.svg'))
    # Where an SVG and PNG share a name, use the editable vector master.
    svg_stems = {p.with_suffix('') for p in sources if p.suffix == '.svg'}
    sources = [p for p in sources if p.suffix != '.png' or p.with_suffix('') not in svg_stems]
    manifest = [package(p, root, output) for p in sources]
    ids = [p['fileName'] for p in manifest]
    assert len(ids) == len(set(ids))
    (output/'rmt-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'Built and validated {len(manifest)} RMT packages in {output}')

if __name__ == '__main__':
    main()
