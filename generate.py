#!/usr/bin/env python3
"""Generate the reMarkable notebook templates as native-resolution SVG.

Every layout is defined once, in millimetres, and rendered per device from the
table in DEVICES.  A 5 mm square stays 5 mm on a reMarkable Pure, a Paper Pro
and a Paper Pro Move; only the pixel grid underneath it changes.

Labels are drawn as outlines from lettering.json, so the templates carry no
font dependency and render identically under whatever rasteriser RCU or the
tablet happens to use.

Stroke widths are declared in millimetres too, then clamped to at least one
device pixel: a sub-pixel line aliases away to nothing on e-ink.

Optional PNG previews and per-device PDFs are rasterised by headless Chrome.
Set CHROME_BIN to override the default macOS path.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LETTERING = json.loads((ROOT / 'lettering.json').read_text())

# The legacy masters were drawn for the 226 PPI panel; the harvested glyph
# outlines are in those pixels, so that is the reference scale for lettering.
MASTER_PPI = 226.0
MASTER_PX_PER_MM = MASTER_PPI / 25.4

PAPER = {'white': '#FFFFFF', 'ivory': '#F6F2E8'}

GRID_COARSE = '#808080'   # 5 mm squared grid
GRID_FINE = '#999999'     # 2 mm grid and its rules
ACCENT = '#737E99'        # headings and labels
MECH_1MM = '#B4B4B4'
MECH_5MM = '#8C8C8C'
MECH_10MM = '#606060'
MECH_FRAME = '#404040'

# Stroke weights in millimetres (see clamp in Canvas.stroke_px).
SW_GRID = 0.115
SW_FINE = 0.112
SW_RULE = 0.135
SW_MECH_1MM = 0.135
SW_MECH_5MM = 0.225
SW_MECH_10MM = 0.292
SW_MECH_FRAME = 0.393
MIN_STROKE_PX = 1.0

# Shared layout constants, in millimetres.
SQUARED_CELL = 5.0
TINY_CELL = 2.0
DATE_LABEL_LIFT = 0.56        # baseline above the squared grid's top edge
DATE_LABEL_RIGHT_FRAC = 0.644  # centre of the right-hand variant, across the grid
TINY_TICK = 1.6
TINY_LABEL_INSET = 2.0
TINY_LABEL_BASELINE = 17.49
TINY_SEPARATOR = 18.99
TOC_TITLE_BASELINE = 11.69
TOC_TITLE_RULE = 14.14
TOC_HEAD_BASELINE = 19.05
TOC_HEAD_RULE = 21.84
TOC_ROW_PITCH = 7.0
TOC_PAGE_COL = 26.0
TOC_COL_GAP = 8.0
TOC_LABEL_INSET = 1.1
MECH_DECADE = 10.0
MECH_BAND = 10.0
MECH_SIDE_ALLOWANCE = 9.0
MECH_END_ALLOWANCE = 7.0
MECH_LABEL_BASELINE = 7.5
MECH_RULE_INSET = 3.0
MECH_RULE_LENGTH = 40.0
MECH_LABEL_GAP = 2.0

DEVICES = {
    'remarkable-pure': {
        'label': 'reMarkable / reMarkable Paper Pure',
        'width': 1404, 'height': 1872, 'ppi': 226.0, 'margin': 9.0,
    },
    'remarkable-pro-move': {
        'label': 'reMarkable Paper Pro Move',
        'width': 954, 'height': 1696, 'ppi': 266.0, 'margin': 4.5,
    },
    'remarkable-paper-pro': {
        'label': 'reMarkable Paper Pro',
        'width': 1620, 'height': 2160, 'ppi': 229.0, 'margin': 9.0,
    },
}

# What to build: (device, design, paper).  Paper Pro ships both paper tints;
# the monochrome panels only ever get white.
BUILD = (
    [('remarkable-pure', d, 'white')
     for d in ('squared-left', 'squared-right', 'tiny-grid', 'toc', 'mechanical-grid')]
    + [('remarkable-pro-move', d, 'white')
       for d in ('squared-left', 'squared-right', 'tiny-grid', 'toc')]
    + [('remarkable-paper-pro', d, paper)
       for paper in ('white', 'ivory')
       for d in ('squared-left', 'squared-right', 'tiny-grid', 'toc')]
)

DESIGN_NAMES = {
    'squared-left': ('Squared Left', 'Grids'),
    'squared-right': ('Squared Right', 'Grids'),
    'tiny-grid': ('Tiny Grid', 'Grids'),
    'toc': ('Contents', 'Life/organize'),
    'mechanical-grid': ('Mechanical Grid 1 mm', 'Grids'),
}

# Raster assets that are not line art and so are packaged as they are.
IMAGE_TEMPLATES = (
    ('remarkable-paper-pro', 'cover-fahrenheit451.png',
     'Fahrenheit 451 Cover', 'Creative'),
)

ICON_CODE = ''

# UUIDs carried over from the first generation of packages, so that a tablet
# which already has one of these templates sees an update instead of a second
# copy in the picker.  Keys are "<device>/<stem>".
LEGACY_IDS = {
    'remarkable-pure/squared-left': '804ff173-c7ce-5957-b49b-0d32e951761d',
    'remarkable-pure/squared-right': '7d704d73-8d96-5784-8973-b6647253a2f4',
    'remarkable-pure/tiny-grid': 'b29703f5-8e7d-53b0-bf8e-7b8d1daed1b8',
    'remarkable-pure/toc': '58deb273-d180-56ba-978c-a3e411169c23',
    'remarkable-pure/mechanical-grid': '556786a1-0db0-478c-b5cc-1db11d80ba3d',
    'remarkable-pro-move/squared-left': '700e5939-b7e2-58d0-9e54-541801fe4c17',
    'remarkable-pro-move/squared-right': 'a543ad1e-c4b4-5b71-8e83-d044f26840ec',
    'remarkable-pro-move/tiny-grid': '467a0aca-f33c-57f1-97d3-aa6b1a3c7a82',
    'remarkable-pro-move/toc': '8d92d582-ad5b-5f4b-a617-e5645533127a',
    'remarkable-paper-pro/squared-left': '7a227995-0ac4-533b-a9f1-c0f794f5422c',
    'remarkable-paper-pro/squared-right': 'de00b40e-f733-5a26-9910-457e464b3a2d',
    'remarkable-paper-pro/toc': 'e4b6e131-29a8-5765-90da-b5db524b88d1',
    'remarkable-paper-pro/squared-left-ivory': '3b6bd5ce-c88e-5521-82c9-5c8798a9761c',
    'remarkable-paper-pro/squared-right-ivory': 'cf7dbd85-674d-5a81-973b-6537bfdcbf47',
    'remarkable-paper-pro/tiny-grid-ivory': '7ca1e452-4f1e-5cc3-a806-8229816272a6',
    'remarkable-paper-pro/toc-ivory': 'd976cc8a-0320-5f9b-a760-805bec20a758',
    'remarkable-paper-pro/cover-fahrenheit451': 'a8c8c460-b823-5fef-b9d4-286a43276bef',
}


class Canvas:
    """An SVG page sized in device pixels but drawn in millimetres."""

    def __init__(self, width_px, height_px, ppi, background):
        self.w = width_px
        self.h = height_px
        self.ppi = ppi
        self.px_per_mm = ppi / 25.4
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" '
            f'height="{height_px}" viewBox="0 0 {width_px} {height_px}">',
            f'<rect width="{width_px}" height="{height_px}" fill="{background}"/>',
        ]

    # -- unit helpers -----------------------------------------------------
    def px(self, mm):
        return mm * self.px_per_mm

    def mm_w(self):
        return self.w / self.px_per_mm

    def mm_h(self):
        return self.h / self.px_per_mm

    def stroke_px(self, mm):
        """Millimetres to pixels, never thinner than one device pixel."""
        return max(MIN_STROKE_PX, mm * self.px_per_mm)

    # -- primitives (all arguments in millimetres) ------------------------
    def line(self, x0, y0, x1, y1, color, width_mm):
        w = self.stroke_px(width_mm)
        self.parts.append(
            f'<line x1="{self.px(x0):.2f}" y1="{self.px(y0):.2f}" '
            f'x2="{self.px(x1):.2f}" y2="{self.px(y1):.2f}" '
            f'stroke="{color}" stroke-width="{w:.2f}"/>'
        )

    def frame(self, x, y, w, h, color, width_mm):
        sw = self.stroke_px(width_mm)
        self.parts.append(
            f'<rect x="{self.px(x):.2f}" y="{self.px(y):.2f}" '
            f'width="{self.px(w):.2f}" height="{self.px(h):.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{sw:.2f}"/>'
        )

    def label(self, text, x, baseline, color, anchor='start', scale=1.0):
        """Draw harvested glyph outlines; x/baseline in millimetres."""
        entry = LETTERING[text]
        unit = self.px_per_mm / MASTER_PX_PER_MM * scale
        width_px = entry['width'] * unit
        origin = self.px(x)
        if anchor == 'middle':
            origin -= width_px / 2
        elif anchor == 'end':
            origin -= width_px
        self.parts.append(
            f'<g fill="{color}" transform="translate({origin:.2f},'
            f'{self.px(baseline):.2f}) scale({unit:.6f})">'
        )
        for glyph in entry['run']:
            if not glyph['d']:
                continue
            self.parts.append(
                f'<path transform="translate({glyph["dx"]:.4f},0)" '
                f'd="{glyph["d"].strip()}"/>'
            )
        self.parts.append('</g>')

    def label_width(self, text, scale=1.0):
        unit = self.px_per_mm / MASTER_PX_PER_MM * scale
        return LETTERING[text]['width'] * unit / self.px_per_mm

    def render(self):
        return ''.join(self.parts) + '</svg>\n'


def fit(extent_mm, margin_mm, cell_mm):
    """Largest whole number of cells that fits inside the margins."""
    count = int(math.floor((extent_mm - 2 * margin_mm) / cell_mm + 1e-9))
    if count < 1:
        raise ValueError(f'no room for a {cell_mm} mm cell in {extent_mm} mm')
    span = count * cell_mm
    return count, span, (extent_mm - span) / 2


# -- designs --------------------------------------------------------------

def draw_squared(canvas, margin, side):
    cols, grid_w, x0 = fit(canvas.mm_w(), margin, SQUARED_CELL)
    rows, grid_h, y0 = fit(canvas.mm_h(), margin, SQUARED_CELL)
    x1, y1 = x0 + grid_w, y0 + grid_h

    baseline = y0 - DATE_LABEL_LIFT
    if side == 'right':
        canvas.label('DATUM/DATE', x0 + grid_w * DATE_LABEL_RIGHT_FRAC,
                     baseline, ACCENT, anchor='middle')
    else:
        canvas.label('DATUM/DATE', x0 + SQUARED_CELL, baseline, ACCENT)

    for i in range(cols + 1):
        x = x0 + i * SQUARED_CELL
        canvas.line(x, y0, x, y1, GRID_COARSE, SW_GRID)
    for j in range(rows + 1):
        y = y0 + j * SQUARED_CELL
        canvas.line(x0, y, x1, y, GRID_COARSE, SW_GRID)


def draw_tiny(canvas, margin):
    cols, grid_w, x0 = fit(canvas.mm_w(), margin, TINY_CELL)
    x1 = x0 + grid_w
    usable = canvas.mm_h() - margin - TINY_SEPARATOR
    rows = int(math.floor(usable / TINY_CELL + 1e-9))
    y0 = TINY_SEPARATOR
    y1 = y0 + rows * TINY_CELL

    rule_x0, rule_x1 = margin, canvas.mm_w() - margin
    canvas.line(rule_x0, margin, rule_x1, margin, GRID_FINE, SW_RULE)
    centre = canvas.mm_w() / 2
    canvas.line(centre, margin, centre, margin + TINY_TICK, GRID_FINE, SW_RULE)
    canvas.label('TITLE / NO.', margin + TINY_LABEL_INSET, TINY_LABEL_BASELINE,
                 GRID_FINE)
    canvas.line(rule_x0, TINY_SEPARATOR, rule_x1, TINY_SEPARATOR,
                GRID_FINE, SW_RULE)

    for i in range(cols + 1):
        x = x0 + i * TINY_CELL
        canvas.line(x, y0, x, y1, GRID_FINE, SW_FINE)
    for j in range(rows + 1):
        y = y0 + j * TINY_CELL
        canvas.line(x0, y, x1, y, GRID_FINE, SW_FINE)


def draw_toc(canvas, margin):
    page_x0 = margin
    page_x1 = page_x0 + TOC_PAGE_COL
    topic_x0 = page_x1 + TOC_COL_GAP
    topic_x1 = canvas.mm_w() - margin

    canvas.label('INHALT / CONTENT / CONTENU', canvas.mm_w() / 2,
                 TOC_TITLE_BASELINE, ACCENT, anchor='middle')

    def pair(y):
        canvas.line(page_x0, y, page_x1, y, GRID_COARSE, SW_RULE)
        canvas.line(topic_x0, y, topic_x1, y, GRID_COARSE, SW_RULE)

    pair(TOC_TITLE_RULE)
    canvas.label('SEITE / PAGE', page_x0 + TOC_LABEL_INSET,
                 TOC_HEAD_BASELINE, ACCENT)
    canvas.label('THEMA / TOPIC / SUJET', topic_x0 + TOC_LABEL_INSET,
                 TOC_HEAD_BASELINE, ACCENT)
    pair(TOC_HEAD_RULE)

    usable = canvas.mm_h() - margin - TOC_HEAD_RULE
    for i in range(1, int(math.floor(usable / TOC_ROW_PITCH + 1e-9)) + 1):
        pair(TOC_HEAD_RULE + i * TOC_ROW_PITCH)


def draw_mechanical(canvas):
    """Landscape 1 mm engineering grid with 5 mm and 10 mm emphasis."""
    def decades(span_mm, allowance):
        usable = span_mm - allowance
        count = int(math.floor(usable / MECH_DECADE + 1e-9))
        if count < 2:
            raise ValueError('no room for a mechanical grid')
        extent = count * MECH_DECADE
        return extent, (span_mm - extent) / 2

    frame_w, fx = decades(canvas.mm_w(), MECH_SIDE_ALLOWANCE)
    frame_h, fy = decades(canvas.mm_h(), MECH_END_ALLOWANCE)
    grid_y0 = fy + MECH_BAND
    grid_h = frame_h - MECH_BAND

    canvas.frame(fx, fy, frame_w, frame_h, MECH_FRAME, SW_MECH_FRAME)

    rule_x1 = fx + frame_w - MECH_RULE_INSET
    rule_x0 = rule_x1 - MECH_RULE_LENGTH
    baseline = fy + MECH_LABEL_BASELINE
    canvas.line(rule_x0, baseline, rule_x1, baseline, MECH_10MM, SW_MECH_5MM)
    canvas.label('DATUM/DATE', rule_x0 - MECH_LABEL_GAP, baseline,
                 MECH_FRAME, anchor='end')

    def weight(step):
        if step % 10 == 0:
            return MECH_10MM, SW_MECH_10MM
        if step % 5 == 0:
            return MECH_5MM, SW_MECH_5MM
        return MECH_1MM, SW_MECH_1MM

    for step in range(int(frame_w) + 1):
        color, width = weight(step)
        x = fx + step
        canvas.line(x, grid_y0, x, grid_y0 + grid_h, color, width)
    for step in range(int(grid_h) + 1):
        color, width = weight(step)
        y = grid_y0 + step
        canvas.line(fx, y, fx + frame_w, y, color, width)


def build_svg(device, design, paper):
    spec = DEVICES[device]
    landscape = design == 'mechanical-grid'
    width = spec['height'] if landscape else spec['width']
    height = spec['width'] if landscape else spec['height']
    canvas = Canvas(width, height, spec['ppi'], PAPER[paper])
    margin = spec['margin']

    if design.startswith('squared-'):
        draw_squared(canvas, margin, design.split('-', 1)[1])
    elif design == 'tiny-grid':
        draw_tiny(canvas, margin)
    elif design == 'toc':
        draw_toc(canvas, margin)
    elif design == 'mechanical-grid':
        draw_mechanical(canvas)
    else:
        raise ValueError(f'unknown design {design!r}')
    return canvas.render(), width, height


def template_id(key, existing):
    if key in existing:
        return existing[key]
    if key in LEGACY_IDS:
        return LEGACY_IDS[key]
    import uuid
    return str(uuid.uuid5(uuid.UUID('c956cffb-c224-4cac-8a22-74f344bbbc0e'), key))


# -- rasterisation --------------------------------------------------------

def chrome_bin():
    return os.environ.get(
        'CHROME_BIN',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    )


def rasterise(entries, out_root, build_dir):
    chrome = chrome_bin()
    if not Path(chrome).exists():
        print(f'warning: {chrome} not found; skipping PNG/PDF render',
              file=sys.stderr)
        return
    by_device = {}
    for entry in entries:
        if not entry['source'].endswith('.svg'):
            continue
        by_device.setdefault(entry['source'].split('/')[0], []).append(entry)

    for device, group in by_device.items():
        for entry in group:
            svg = (out_root / entry['source']).read_text()
            html = build_dir / (entry['source'].replace('/', '_') + '.html')
            html.write_text(
                '<!DOCTYPE html><html><head><style>'
                'html,body{margin:0;padding:0;}'
                f'svg{{display:block;width:{entry["width"]}px;'
                f'height:{entry["height"]}px;}}'
                '</style></head><body>' + svg + '</body></html>'
            )
            png = out_root / entry['source'].replace('.svg', '.png')
            subprocess.run(
                [chrome, '--headless', '--disable-gpu', '--hide-scrollbars',
                 '--force-device-scale-factor=1',
                 f'--window-size={entry["width"]},{entry["height"]}',
                 f'--screenshot={png}', html.as_uri()],
                check=True, capture_output=True,
            )

        # One PDF per orientation: the page box has to match the panel
        # exactly, and a single document cannot carry two sizes reliably.
        ppi = DEVICES[device]['ppi']
        orientations = {}
        for entry in group:
            orientations.setdefault(entry['landscape'], []).append(entry)
        for landscape, items in orientations.items():
            pages = []
            for entry in items:
                svg = (out_root / entry['source']).read_text()
                pages.append(f'<div class="page">{svg}</div>')
            page_w = items[0]['width'] / ppi * 25.4
            page_h = items[0]['height'] / ppi * 25.4
            sheet = build_dir / f'{device}-{int(landscape)}.html'
            sheet.write_text(
                '<!DOCTYPE html><html><head><style>'
                f'@page {{ size: {page_w:.2f}mm {page_h:.2f}mm; margin: 0; }}'
                'html,body{margin:0;padding:0;line-height:0;'
                '-webkit-print-color-adjust:exact;print-color-adjust:exact;}'
                f'.page{{width:{page_w:.2f}mm;height:{page_h:.2f}mm;'
                'page-break-after:always;overflow:hidden;}'
                '.page:last-child{page-break-after:auto;}'
                'svg{display:block;width:100%;height:100%;}'
                '</style></head><body>' + ''.join(pages) + '</body></html>'
            )
            suffix = '-landscape' if landscape else ''
            subprocess.run(
                [chrome, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                 f'--print-to-pdf={out_root / device / (device + suffix + ".pdf")}',
                 sheet.as_uri()],
                check=True, capture_output=True,
            )
    print(f'Rendered PNG previews and per-device PDFs under {out_root}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    parser.add_argument('--no-raster', action='store_true',
                        help='skip the Chrome PNG/PDF render')
    args = parser.parse_args()
    out_root = args.output.resolve()

    catalog_path = out_root / 'templates.json'
    existing = {}
    if catalog_path.exists():
        existing = {e['key']: e['id'] for e in json.loads(catalog_path.read_text())}

    entries = []
    for device, design, paper in BUILD:
        stem = design if paper == 'white' else f'{design}-{paper}'
        key = f'{device}/{stem}'
        svg, width, height = build_svg(device, design, paper)
        target = out_root / device / f'{stem}.svg'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg)
        name, category = DESIGN_NAMES[design]
        if paper != 'white':
            name = f'{name} {paper.capitalize()}'
        entries.append({
            'key': key, 'id': template_id(key, existing),
            'name': name, 'category': category,
            'source': f'{device}/{stem}.svg',
            'width': width, 'height': height,
            'landscape': width > height, 'iconCode': ICON_CODE,
        })

    for device, filename, name, category in IMAGE_TEMPLATES:
        path = out_root / device / filename
        if not path.exists():
            print(f'warning: {path} missing; skipping {name}', file=sys.stderr)
            continue
        import struct
        data = path.read_bytes()
        width, height = struct.unpack('>II', data[16:24])
        key = f'{device}/{Path(filename).stem}'
        entries.append({
            'key': key, 'id': template_id(key, existing),
            'name': name, 'category': category,
            'source': f'{device}/{filename}',
            'width': width, 'height': height,
            'landscape': width > height, 'iconCode': ICON_CODE,
        })

    ids = [e['id'] for e in entries]
    if len(ids) != len(set(ids)):
        raise SystemExit('duplicate template ids in catalog')
    catalog_path.write_text(json.dumps(entries, indent=2) + '\n')
    print(f'Wrote {len(entries)} templates and templates.json under {out_root}')

    if not args.no_raster:
        build_dir = out_root / '.build'
        build_dir.mkdir(exist_ok=True)
        try:
            rasterise(entries, out_root, build_dir)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
