"""Lay out proposed Blender views with captions keyed to the original A-01 floor plan.

Usage: python3 gallery.py STAGE PROPOSED_RENDER_DIRECTORY
The corrected laundry exterior-door render is read from STAGE.
"""
import base64
import json
import subprocess
import sys
from html import escape
from pathlib import Path
from textwrap import wrap

stage, proposed = map(Path, sys.argv[1:3])
sheets = [
    ('Kitchen | Range and sink', 'A-01–02 floor plans  /  I-01 kitchen elevations',
     [
         ('range', 'Range and round window',
          'The induction range, plaster hood and round window create a new cooking wall. The original range sat on the side counter run.'),
         ('sink', 'Sink, dishwasher and floating shelf',
          'A centered apron sink, dishwasher drawer, wide awning and oak shelf replace the original corner sink and short window arrangement.'),
         ('lantern', 'Paper lantern and window alignment',
          'The kitchen arrangement shown on A-01 is reworked around a centered sink and two new windows. A 560 mm paper lantern lights the new layout.'),
     ]),
    ('Kitchen | Window operation', 'A-01–02 floor plans  /  A-03–04 exterior elevations  /  I-01 kitchen elevations',
     [
         ('awning', 'Sink awning window open',
          'A wide, top-hinged awning replaces the short window beside the original corner sink. This view shows it open above the oak shelf.'),
         ('shade', 'Concealed sink shade lowered',
          'The wide awning replacing the original kitchen window has a concealed roller shade, shown lowered here.'),
         ('round-blind', 'Round window blind closed',
          'The remodel adds a round window to the cooking wall, which had no round opening on A-01. Its fitted pleated blind is shown closed.'),
     ]),
    ('Kitchen and dining | Cabinetry and arch', 'A-01–02 floor plans  /  I-02 interior elevations',
     [
         ('appliances', 'Refrigerator and microwave wall',
          'The kitchen wall shown on A-01 gets a refrigerator surround, an integrated microwave and recessed oak upper cabinets.'),
         ('portal', 'Rounded kitchen-to-dining arch',
          'A 1,400 mm rounded arch replaces the original narrow kitchen-to-dining opening.'),
     ]),
    ('Laundry | Entry and storage', 'A-01–02 floor plans  /  E-01 receptacle plan  /  I-04 laundry elevations',
     [
         ('laundry-front', 'Laundry wall',
          'An all-in-one washer/dryer, worktop and full-height pantry replace the original side-by-side appliance arrangement.'),
         ('laundry-storage', 'Pullouts extended',
          'The wall that originally held side-by-side appliances now includes a trash and recycling pullout and a narrow pantry pullout.'),
         ('laundry-door', 'Widened pocket-door opening',
          'A 42-inch pocket door replaces the original hinged doorway between the kitchen and laundry.'),
         ('laundry-entry', 'Laundry exterior door swing',
          'The exterior door retains the original inward swing and hinge location shown on A-01.'),
     ]),
    ('Main house | Bedroom layout', 'A-01–02 floor plans  /  I-08–09 bedroom elevations',
     [
         ('layout', 'Main house cutaway',
          'The original main house had two living rooms and one hall bath. The remodel converts one living room to Bedroom 3 and adds a second bath.'),
         ('bedroom3', 'Bedroom 3 looking toward the kitchen',
          'Bedroom 3 occupies the original second living room. A glazed partition and closet redefine the former passage toward the kitchen.'),
         ('wardrobe-detail', 'Main bedroom storage',
          'A freestanding bypass wardrobe and rounded shelves replace the original recessed closet arrangement.'),
         ('main-slider', 'Main bedroom exterior access',
          'A glazed sliding door adds exterior access at the main bedroom wall that originally had a window.'),
     ]),
    ('Main house | Bathroom layout', 'A-01–02 floor plans  /  I-05–06 bathroom elevations',
     [
         ('bathrooms-final', 'Two bathrooms in the main house',
          'The original single hall bath and adjoining closets are reconfigured into Bathroom 1 with a tub/shower and Bathroom 2 with a separate shower.'),
     ]),
    ('Detached wing | Office and open room', 'A-01–02 floor plans  /  A-05 exterior elevations  /  I-13–14 interior elevations',
     [
         ('office', 'Office exterior',
          'The original small garage becomes an office. A 6 ft window replaces the smaller side window, and the original hinged entry location is retained.'),
         ('adu-window', 'ADU exterior window',
          'A window replaces the original exterior door next to the ADU bedroom.'),
         ('adu-open', 'Open area beside the ADU bedroom',
          'Removing the original divider joins the enclosed area to the ADU bedroom. The bathroom partition stays in place.'),
     ]),
]
INK='#1c2934'
MUTED='#50626e'
BLUE='#005d84'
LINE='#a8b6bc'


def text(x,y,value,size=11,weight=400,color=INK,anchor='start'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')


def rule(x0,x1,y):
    return f'<path d="M{x0} {y}H{x1}" stroke="{LINE}" stroke-width="0.8"/>'


def photo(path,x,y,w):
    content=path.read_bytes()
    assert len(content)>3000 and content.startswith(b'\xff\xd8'), path
    encoded=base64.b64encode(content).decode()
    h=w*650/1040
    return (f'<image x="{x}" y="{y}" width="{w}" height="{h}" '
            f'preserveAspectRatio="xMidYMid meet" xlink:href="data:image/jpeg;base64,{encoded}"/>')


def view(spec, x, y, width):
    name, title, caption = spec
    path = (stage if name == 'laundry-entry' else proposed) / f'{name}.jpg'
    image_bottom = y + 18 + width * 650 / 1040
    caption_lines = wrap(caption, 73 if width < 500 else 150)
    assert len(caption_lines) <= 2, title
    return [
        text(x, y, title, 15, 700),
        photo(path, x, y + 18, width),
        *(text(x, image_bottom + 16 + i * 13, line, 11)
          for i, line in enumerate(caption_lines)),
    ]


manifest = []
for number,(title,crossref,views) in enumerate(sheets,7):
    sheet=f'A-{number:02d}'
    svg=[
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="17in" height="11in" viewBox="0 0 1224 792">',
        '<rect width="1224" height="792" fill="white"/>',
        '<g font-family="Helvetica, Arial, sans-serif">',
        text(35,33,'214 N KATHERINE DRIVE  /  VENTURA, CA 93003',11,700,BLUE),
        text(1189,33,'PROPOSED 3D RENDERINGS',10,700,MUTED,'end'),
        text(35,67,title,28,700),
        text(35,87,crossref,10,400,MUTED),
        rule(34,1190,101),
    ]
    if len(views) == 1:
        svg.extend(view(views[0], 180, 125, 864))
    else:
        for index, spec in enumerate(views):
            x = 424 if len(views) == 3 and index == 2 else 129 + index % 2 * 590
            svg.extend(view(spec, x, 122 + index // 2 * 304, 376))

    svg.extend([
        rule(34,1190,721),
        text(35,743,'Captions describe the proposed work relative to the original floor plan on A-01.',10,400,MUTED),
        text(35,759,'Verify rough openings and existing conditions against the plans and on site.',10,400,MUTED),
        text(1190,762,sheet,24,700,INK,'end'),
        '</g></svg>',
    ])
    path=stage/f'{sheet}.svg'
    path.write_text('\n'.join(svg))
    for render in (['-f','pdf'], ['-w','1224']):
        suffix='.pdf' if render[0]=='-f' else '.png'
        subprocess.run(['rsvg-convert', *render, '-o',str(path.with_suffix(suffix)),str(path)],check=True)
    manifest.append(dict(id=sheet,title=title,views=[dict(title=title, caption=caption) for _, title, caption in views]))
(stage/'gallery-manifest.json').write_text(json.dumps(manifest))
print(f'{len(sheets)} sheets with {sum(len(v) for _,_,v in sheets)} proposed views.')
