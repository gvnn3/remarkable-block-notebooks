#!/usr/bin/env python3
"""Package the generated templates as RCU .rmt archives.

An .rmt is a USTAR tar holding template.json and template.svg, as documented
in Appendix D of the RCU manual.  RCU rasterises the SVG itself on upload, but
where generate.py has already produced a preview PNG at the native panel
resolution we ship that too: the one template confirmed working on a tablet
carried its own template.png, and matching it costs only file size.

Identity, display name and category come from templates.json, which is written
by generate.py and checked in.  fileName is a stable UUID from that catalog --
never derived from the file's path -- so moving or renaming a template cannot
silently create a second copy of it in the tablet's template picker.
"""

import argparse
import io
import json
import struct
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET

SVG_NS = '{http://www.w3.org/2000/svg}'


class BuildError(Exception):
    pass


def svg_viewport(data):
    try:
        element = ET.fromstring(data)
    except ET.ParseError as exc:
        raise BuildError(f'not well-formed SVG: {exc}') from exc
    if element.tag != SVG_NS + 'svg':
        raise BuildError(f'root element is {element.tag}, not <svg>')
    try:
        _, _, width, height = (float(v) for v in element.attrib['viewBox'].split())
    except (KeyError, ValueError) as exc:
        raise BuildError(f'missing or malformed viewBox: {exc}') from exc
    return int(round(width)), int(round(height))


def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise BuildError('not a PNG')
    width, height = struct.unpack('>II', data[16:24])
    return width, height


def wrap_png(data, width, height):
    import base64
    encoded = base64.b64encode(data).decode('ascii')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<image width="{width}" height="{height}" '
        f'xlink:href="data:image/png;base64,{encoded}"/>'
        f'</svg>'
    ).encode()


def payloads_for(entry, root, with_png):
    """Return the archive members plus the template's pixel size."""
    source = root / entry['source']
    if not source.exists():
        raise BuildError(f'missing source {entry["source"]}')
    data = source.read_bytes()

    if source.suffix == '.png':
        # The wrapper SVG already carries this exact image, so a separate
        # template.png would only double the archive for no gain.
        width, height = png_size(data)
        svg = wrap_png(data, width, height)
        preview = None
    else:
        svg = data
        width, height = svg_viewport(svg)
        sibling = source.with_suffix('.png')
        preview = sibling.read_bytes() if sibling.exists() else None

    if (width, height) != (entry['width'], entry['height']):
        raise BuildError(
            f'{entry["source"]} is {width}x{height}, '
            f'catalog says {entry["width"]}x{entry["height"]}'
        )

    metadata = {
        'name': entry['name'],
        'fileName': entry['id'],
        'categories': [entry['category']],
        'iconCode': entry['iconCode'],
        'landscape': width > height,
    }
    members = {
        'template.json': json.dumps(metadata, indent=2,
                                    ensure_ascii=True).encode(),
        'template.svg': svg,
    }
    if with_png and preview is not None:
        members['template.png'] = preview
    return members, metadata, width, height


def write_archive(target, members):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, 'w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    with tarfile.open(target) as archive:
        if archive.getnames() != list(members):
            raise BuildError(f'{target.name}: member list did not round-trip')
        for name, data in members.items():
            if archive.extractfile(name).read() != data:
                raise BuildError(f'{target.name}: {name} did not round-trip')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path,
                        help='write packages here instead of beside the sources')
    parser.add_argument('--no-png', action='store_true',
                        help='ship SVG only, letting RCU rasterise on upload')
    args = parser.parse_args()

    root = args.root.resolve()
    output = (args.output or root).resolve()
    catalog = json.loads((root / 'templates.json').read_text())

    manifest = []
    for entry in catalog:
        members, metadata, width, height = payloads_for(
            entry, root, not args.no_png)
        target = output / Path(entry['source']).with_suffix('.rmt')
        write_archive(target, members)
        manifest.append({
            'package': target.relative_to(output).as_posix(),
            'source': entry['source'],
            'width': width,
            'height': height,
            'members': list(members),
            **metadata,
        })

    ids = [e['fileName'] for e in manifest]
    if len(ids) != len(set(ids)):
        raise BuildError('duplicate fileName across packages')

    (output / 'rmt-manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n')
    print(f'Built and validated {len(manifest)} RMT packages in {output}')


if __name__ == '__main__':
    try:
        main()
    except BuildError as exc:
        raise SystemExit(f'build_rmt: {exc}')
