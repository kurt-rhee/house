"""Generate proposed plumbing coordination sheets P-01 through P-03.

Run with a staging directory. Convert the SVGs to 11 × 17 PDFs with rsvg-convert.
"""
import argparse
import json
from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'interior-elevations'))
from draw import BLUE, FIELD, INK, LINE, MUTED, PALE, base, criteria, plan_background
from layout import PROJECT

COLD = '#005d84'
HOT = '#a43c32'
WASTE = '#734329'
VENT = '#237264'
ROUTE = '7 4'


@dataclass(frozen=True)
class Fixture:
    tag: str
    name: str
    water: str
    trap: str
    dfu: int
    cad_id: str = ''
    reference_bounds: tuple = ()

    @property
    def bounds(self):
        if self.reference_bounds:
            x, y, xmax, ymax = self.reference_bounds
            return [(x, y), (xmax, y), (xmax, ymax), (x, ymax)]
        f = PROJECT['fixtures'][self.cad_id]
        x, y = f['origin']['x'], f['origin']['y']
        angle = radians(f['rotation'])
        w, d = f['width'], f['depth']
        return [(x + u*cos(angle) - v*sin(angle), y + u*sin(angle) + v*cos(angle))
                for u, v in ((0, 0), (w, 0), (w, d), (0, d))]

    @property
    def center(self):
        return tuple(sum(axis) / 4 for axis in zip(*self.bounds))


# The detached bath comes from the original plan and the existing-fixture trace
# used for the electrical drawing. Its fixtures have no CAD objects.
GROUPS = {
    'Kitchen': (
        Fixture('KS-1', 'Kitchen sink', 'H/C', '1½″', 2, '4be42708-ac78-437e-8895-9042270f0235'),
        Fixture('DW-1', 'Dishwasher drawer', 'H', '—', 0, '9795d0d2-7db7-411f-91b8-ecbebec3fb30'),
    ),
    'Laundry': (
        Fixture('WM-1', 'Clothes washer', 'H/C', '2″', 3, '38ef2eef-84c6-449f-8e20-a1cd630d0cb6'),
    ),
    'Bathroom 1': (
        Fixture('L-1', 'Lavatory', 'H/C', '1¼″', 1, 'e332d192-50d9-4bec-adaf-f254b1ee4c52'),
        Fixture('WC-1', 'Water closet', 'C', '3″*', 3, 'c40f5550-c32f-446b-8617-900a1695731a'),
        Fixture('T-1', 'Tub/shower', 'H/C', '1½″', 2, '99d32ea4-059c-446d-88e9-0b9d8f0ce016'),
    ),
    'Bathroom 2': (
        Fixture('L-2', 'Lavatory', 'H/C', '1¼″', 1, '9addeb36-1b09-4c3e-babc-e569bc6d8599'),
        Fixture('WC-2', 'Water closet', 'C', '3″*', 3, 'a110bdae-e37e-4c6c-b1c8-8e537a664fae'),
        Fixture('S-2', 'Shower', 'H/C', '2″', 2, 'df91bdf7-f8bd-4318-b7f3-980f7103444d'),
    ),
    'Detached bath': (
        Fixture('L-3', 'Lavatory', 'H/C', '1¼″', 1, reference_bounds=(5580, 6670, 6110, 7110)),
        Fixture('WC-3', 'Water closet', 'C', '3″*', 3, reference_bounds=(4880, 6450, 5280, 7110)),
        Fixture('T-3', 'Bathtub', 'H/C', '1½″', 2, reference_bounds=(3997.6, 5943.8, 4700, 7127.3)),
    ),
}
FIXTURES = {f.tag: f for fixtures in GROUPS.values() for f in fixtures}
MAIN_LOAD = sum(f.dfu for f in FIXTURES.values() if not f.reference_bounds)
WING_LOAD = sum(f.dfu for f in FIXTURES.values() if f.reference_bounds)
assert {f.cad_id for f in FIXTURES.values() if f.cad_id} == {
    key for key, f in PROJECT['fixtures'].items()
    if f['kind'] in {'Sink', 'DishwasherDrawer', 'WasherDryer', 'Bath', 'Shower', 'Toilet'}
}

SHEETS = [
    ('P-01', 'Plumbing fixture floor plan and count'),
    ('P-02', 'Domestic water and sanitary sewer'),
    ('P-03', 'Drain, waste and vent schematic'),
]


def heading(sheet, subtitle, label='PLUMBING  /  FIELD COORDINATION'):
    number, title = SHEETS[sheet - 1]
    return base(number, title, subtitle, label)


def poly(c, points, color, width=1.5, dash='', fill='none'):
    c.path('M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in points), color, width, fill, dash)


def tag(c, x, y, name, color=BLUE):
    w = max(31, 6 * len(name) + 10)
    c.rect(x-w/2, y-8, w, 16, 'white', color, .8)
    c.text(x, y+3, name, 9, color, 700, 'middle')


def leader(c, x, y, end, name, color=BLUE):
    c.line(x, y, *end, color, .9)
    c.circle(x, y, 2.7, 'white', color, 1)
    tag(c, *end, name, color)


def arrow(c, x, y, heading, color):
    a = radians(heading)
    tip = (x, y)
    wings = [(x - 7*cos(a+t), y - 7*sin(a+t)) for t in (-.46, .46)]
    poly(c, [wings[0], tip, wings[1]], color, 1.4)


def notes(c, x, y, caption, entries, width=65):
    c.text(x, y, caption, 13, INK, 700)
    y += 19
    for key, message in entries:
        c.text(x, y, key, 9.8, INK, 700)
        y = c.paragraph(x, y+14, message, width, 9.7, 12) + 7
    return y


def fixture_plan():
    c = heading(1, 'Proposed top-down plans. See P-02 for service routing and P-03 for drainage and vents.')
    c.text(40, 128, 'MAIN HOUSE', 14, INK, 700)
    c.text(40, 146, '3⁄16″ = 1′–0″ at 11 × 17', 9, MUTED)
    c.text(678, 128, 'DETACHED WING', 14, INK, 700)
    c.text(678, 146, '3⁄16″ = 1′–0″ at 11 × 17', 9, MUTED)
    c.line(648, 119, 648, 712, LINE, .8)
    k = 13.5/304.8

    def main(x, y):
        return 50 + (x-14500)*k, 167 + (y-1950)*k

    def wing(x, y):
        return 684 + (x-700)*k, 160 + (y-520)*k

    plan_background(c, False, main, k, omit_labels=('Bathroom 1', 'Bathroom 2'))
    plan_background(c, True, wing, k, omit_labels=('Bathroom', 'ADU bedroom'))
    c.text(291, 592, 'Bath 1', 8, MUTED, 700, 'middle')
    c.text(391, 592, 'Bath 2', 8, MUTED, 700, 'middle')
    c.text(994, 488, 'ADU bedroom', 9.3, INK, 700, 'middle')
    c.text(867, 392, 'Existing bath', 8, FIELD, 700, 'middle')

    positions = {
        'KS-1': (227, 153), 'DW-1': (290, 153), 'WM-1': (75, 255),
        'L-1': (288, 571), 'WC-1': (288, 605), 'T-1': (289, 672),
        'L-2': (405, 571), 'WC-2': (410, 605), 'S-2': (396, 672),
        'L-3': (960, 463), 'WC-3': (891, 500), 'T-3': (797, 447),
    }
    for f in FIXTURES.values():
        pt = wing if f.reference_bounds else main
        color = FIELD if f.reference_bounds else BLUE
        corners = [pt(*p) for p in f.bounds]
        poly(c, corners+[corners[0]], color, .85, '3 2' if f.reference_bounds else '')
        leader(c, *pt(*f.center), positions[f.tag], f.tag, color)

    c.text(71, 652, 'N', 10, INK, 700, 'middle')
    c.line(71, 658, 71, 683, INK, 1)
    arrow(c, 71, 684, 90, INK)
    c.text(87, 678, 'North down on both floor plans', 9, MUTED)

    x, y = 680, 544
    c.text(x, y, 'Fixture and appliance count', 14, INK, 700)
    cols = (x+7, x+297, x+380, x+470)
    for col, title in zip(cols, ('TYPE', 'MAIN', 'DETACHED', 'TOTAL')):
        c.text(col, y+20, title, 9, MUTED, 700)
    totals = [0, 0]
    for index, (prefix, label) in enumerate([
        ('WC-', 'Water closets'), ('L-', 'Lavatories'), ('T-', 'Bathtubs / tub-shower'),
        ('S-', 'Separate shower'), ('KS-', 'Kitchen sink'),
        ('DW-', 'Dishwasher'), ('WM-', 'Clothes washer'),
    ]):
        row = y+35+14*index
        count = [sum(f.tag.startswith(prefix) and bool(f.reference_bounds) == detached
                     for f in FIXTURES.values()) for detached in (False, True)]
        if index % 2 == 0:
            c.rect(x, row-10, 507, 14, PALE)
        for i, value in enumerate((label, *count, sum(count))):
            c.text(cols[i], row, value, 9.8, weight=700 if i==3 else 400)
        totals = [a+b for a,b in zip(totals,count)]
    c.line(x, y+126, x+507, y+126, LINE, .7)
    for col, value in zip(cols, ('TOTAL', *totals, sum(totals))):
        c.text(col, y+140, value, 10, INK, 700)
    c.text(x, y+160, 'Blue tags use CAD fixture locations. Brown tags trace retained fixtures. Verify on site.', 9, MUTED)
    c.text(41, 719, 'Count covers shown fixtures and appliance connections. Confirm water-heater scope, exterior hose bibbs and any refrigerator ice-maker feed.', 9.3, MUTED)
    return c


# Lot-local coordinates in feet, taken from the GIS registration on A-00.
# The two footprint polygons preserve that sheet's separately registered buildings.
SITE_MAIN = [(40.29,7.14),(17.39,7.14),(17.39,27.50),(10.74,27.50),
             (10.74,43.77),(44.13,43.77),(44.13,31.82),(42.15,31.82),
             (42.15,21.51),(47.37,21.51),(47.37,12.71),(40.29,12.71)]
SITE_WING = [(87.54,5.29),(68.17,5.29),(68.17,32.60),(87.63,32.60),
             (87.63,23.63),(97.51,23.63),(97.51,7.54),(87.54,7.54)]
# Ventura Water public Service Line Inventory, 214 KATHERINE DR N, in A-00's CRS.
# GIS point (6180386.109, 1925984.378) converted to parcel-local coordinates.
WATER_SERVICE_POINT = (-8.16, 14.40)
SITE_DRIVE = [(0,1.4),(25,1.4),(46,.9),(67.8,.9),(67.8,21.2),(55,21.2),
              (50,14.6),(44,9.1),(24,8.6),(0,8.6)]


def utility_plan():
    c = heading(2, 'Site corridors and building connections are proposed for coordination. Field-locate all existing utility points before routing.')
    c.text(42, 133, 'PROPOSED UTILITY ROUTING', 14, INK, 700)
    c.text(42, 151, 'APN 074-0-115-120  /  1″ = 15′ at 11 × 17  /  parcel and footprints from A-00', 9, MUTED)

    def pt(u, v):
        return 110 + 4.8*u, 485 - 4.8*v

    def route(points, color):
        poly(c, [pt(*p) for p in points], color, 2, ROUTE)

    def polygon(coords, fill, stroke=LINE):
        poly(c, [pt(*uv) for uv in coords+[coords[0]]], stroke, .8, fill=fill)

    polygon([(-14,0),(-3,0),(-3,50),(-14,50)], PALE)
    polygon([(0,0),(125,0),(125,50),(0,50)], '#f9f8f2', INK)
    polygon(SITE_DRIVE, '#e8e3dc')
    polygon(SITE_MAIN, '#e0e8ec', MUTED)
    polygon(SITE_WING, '#e0e8ec', MUTED)
    c.items.append('<g transform="rotate(-90 69 338)">')
    c.text(69, 338, 'N KATHERINE DRIVE', 10, MUTED, 700, 'middle')
    c.items.append('</g>')
    c.text(*pt(28,30), 'MAIN HOUSE', 11, INK, 700, 'middle')
    c.text(*pt(82,17), 'GARAGE / ADU', 11, INK, 700, 'middle')
    c.text(*pt(54,10), 'Driveway', 9, MUTED)
    c.text(686, 220, 'N', 10, INK, 700, 'middle')
    c.line(680, 249, 684, 227, INK, 1)
    arrow(c, 684, 227, -80, INK)

    route([WATER_SERVICE_POINT,(5,14.40),(5,47.6),(79,47.6),(79,32.6)], COLD)
    route([(5,34),(10.74,34)], COLD)
    route([(39,43.77),(39,49),(83,49),(83,32.6)], HOT)
    route([(75,32.6),(75,45.25),(0,45.25)], WASTE)
    route([(30,43.77),(30,45.25)], WASTE)
    arrow(c, *pt(65,47.6), 0, COLD)
    arrow(c, *pt(9,34), 0, COLD)
    arrow(c, *pt(60,49), 0, HOT)
    arrow(c, *pt(13,45.25), 180, WASTE)
    for uv, end, label, color in [
        (WATER_SERVICE_POINT,(91,434),'W0',COLD), ((0,45.25),(134,284),'S0',WASTE),
        ((10.74,34),(181,304),'W1',COLD), ((30,43.77),(247,313),'S1',WASTE),
        ((79,32.6),(510,347),'W2',COLD), ((75,32.6),(463,347),'S2',WASTE),
    ]:
        leader(c, *pt(*uv), end, label, color)
    c.text(113, 504, 'W0 uses Ventura Water GIS. S0 and building entries are schematic. Confirm actual utility locations on site.', 9.2, FIELD)

    for x, color, description in ((43,COLD,'Proposed cold water'), (250,HOT,'Potential shared hot water'), (480,WASTE,'Proposed sanitary sewer')):
        c.line(x, 524, x+36, 524, color, 2, ROUTE)
        c.text(x+47, 528, description, 9.5, INK)
    c.text(42, 558, 'Service points and sizing inputs', 13, INK, 700)
    y = 578
    for code, message in [
        ('W0', 'Field-verify GIS service point, meter, shutoff, service size, available pressure and developed lengths.'),
        ('W1 / W2', 'Verify building entries. Provide accessible isolation to each building on the shared-service concept.'),
        ('S0', 'Locate and camera the private lateral. Verify approved tap, diameter, material, condition and invert.'),
        ('S1 / S2', 'Confirm drain exits and tie-in with surveyed inverts. Verify gravity fall and cleanouts on P-03.'),
    ]:
        c.text(42, y, code, 10, INK, 700)
        c.text(113, y, message, 9.3, MUTED)
        y += 20

    c.line(735, 118, 735, 712, LINE, .8)
    x = 758
    c.text(x, 133, 'Domestic water distribution', 14, INK, 700)
    c.text(x, 151, 'Branch diagram  /  H = hot water  /  C = cold water', 9, MUTED)
    tag(c, 782, 187, 'W0', COLD)
    c.line(803,187,827,187,COLD,1.5)
    c.line(827,187,827,237,COLD,1.5)
    c.line(827,187,853,187,COLD,1.5)
    c.line(827,237,853,237,COLD,1.5)
    tag(c, 875,187,'W1',COLD)
    tag(c, 875,237,'W2',COLD)
    c.text(900,191,'Main house isolation', 10, INK, 700)
    c.text(900,241,'Detached wing isolation', 10, INK, 700)
    c.text(x, 273, 'W1 cold feed → main cold distribution + electric WH', 10, COLD, 700)
    c.text(x, 293, 'Electric WH outlet → main hot distribution + detached bath*', 10, HOT, 700)
    c.text(x, 313, 'W2 cold feed → detached bath cold fixtures', 10, COLD, 700)
    yy = 341
    for group, fixtures in GROUPS.items():
        c.text(x, yy, group, 9.7, INK, 700)
        c.text(x+100, yy, '    '.join(f'{f.tag}  {f.water}' for f in fixtures), 9.7, MUTED)
        c.line(x, yy+6, 1184, yy+6, LINE, .5)
        yy += 23

    notes(c, x, 480, 'Field coordination', [
        ('* Hot-water service', 'The red route applies if both buildings share an electric heater. Confirm heater location, capacity and detached hot-water service. Confirm condensate, pan and relief discharges as applicable.'),
        ('Water and sewer sizing', 'Size water service and branches under CPC §610. Coordinate separate trench routes, crossings, materials and cover under CPC §609.2 and Ventura Water standards.'),
        ('Utility approval', 'Confirm allowable service arrangement for the detached wing. Use the verified lateral and meter locations to finalize routes, sizes, slopes, and invert elevations.'),
    ], 71)
    c.text(42, 673, 'Sources  /  Site sheet A-00 and Ventura Water public Service Line Inventory', 9, MUTED)
    c.text(42, 713, 'Gas service and piping  /  N/A. Proposed design is all-electric.', 10, INK, 700)
    return c


def dwv_group(c, x, width, name, fixtures):
    y, right = 182, x+width
    c.rect(x, y, width, 206, '#f8faf9', LINE, .7)
    c.text(x+10, y+18, name, 11, INK, 700)
    load = sum(f.dfu for f in fixtures)
    c.text(right-9, y+18, f'{load} DFU', 9, WASTE, 700, 'end')
    drains = [f for f in fixtures if f.dfu]
    stations = [x+width*(index+.5)/len(drains) for index in range(len(drains))]
    stacks = [station+17 for station in stations]
    vent_at = (stacks[0]+stacks[-1])/2
    c.line(vent_at, 259, vent_at, 221, VENT, 1.55, '4 2')
    arrow(c, vent_at, 221, -90, VENT)
    c.text(vent_at, 216, 'VENT TO ROOF', 7.8, VENT, 700, 'middle')
    if len(stacks)>1:
        c.line(stacks[0], 259, stacks[-1], 259, VENT, 1.55, '4 2')
    c.line(x+11, 374, right-11, 374, WASTE, 1.7)
    arrow(c, right-11, 374, 0, WASTE)

    for f, station, stack in zip(drains, stations, stacks):
        tag(c, station-7, 278, f.tag, WASTE)
        start = station-17
        c.text(start, 352, f.trap, 8.2, WASTE, 700)
        if f.tag.startswith('WC'):
            poly(c, [(start,289),(start,319),(stack,326)], WASTE)
        else:
            c.path(f'M{start},289 V318 q0,8 7,8 q7,0 7,-8 v-4 L{stack},326', WASTE, 1.4)
        c.line(stack, 326, stack, 374, WASTE, 1.5)
        c.line(stack, 326, stack, 259, VENT, 1.5, '4 2')
        c.circle(stack, 326, 2.1, WASTE, WASTE, .6)
        c.circle(stack, 374, 2.1, WASTE, WASTE, .6)
        if f.tag == 'KS-1':
            tag(c, x+34, 295, 'DW-1', WASTE)
            poly(c, [(x+34,303),(x+34,310),(start,310)], WASTE, .9, '2 2')
            c.text(x+34, 323, 'Air gap', 7.7, WASTE, 700, 'middle')
        if f.tag == 'WM-1':
            c.text(x+10, 300, 'Standpipe', 8.2, MUTED)
    branch = '2″' if name in ('Kitchen','Laundry') else '3″'
    c.line(right-11, 374, right-11, 423, WASTE, 1.7)
    c.text(right-17, 408, f'{branch} branch', 9, WASTE, 700, 'end')
    return right-11


def dwv_plan():
    c = heading(3, 'Schematic only. Fixture tags match P-01. Sewer tie points match P-02. Sizes are proposed coordination values.')
    c.text(42, 129, 'MAIN HOUSE  /  INDIVIDUALLY VENTED FIXTURE CONCEPT', 13, INK, 700)
    c.text(949, 129, 'DETACHED WING  /  VERIFY EXISTING', 12, FIELD, 700)
    c.line(42, 153, 70, 153, WASTE, 1.7)
    c.text(77, 157, 'Sanitary drain / waste', 9, INK)
    c.line(208, 153, 236, 153, VENT, 1.6, '4 2')
    c.text(243, 157, 'Dry vent', 9, INK)
    c.text(341, 157, '* WC integral trap, 3″ fixture drain', 9, INK)
    c.text(611, 157, 'DFU = drainage fixture units', 9, INK)
    columns = [(42,202), (256,171), (439,223), (674,247), (949,238)]
    exits = [dwv_group(c, x, width, group, fixtures)
             for (x,width),(group,fixtures) in zip(columns,GROUPS.items())]
    c.text(42, 411, 'Drain flow →', 9, WASTE, 700)
    c.line(42, 423, 922, 423, WASTE, 2)
    c.line(960, 423, exits[-1], 423, WASTE, 2)
    for join in exits[:-1]:
        c.circle(join, 423, 2.3, WASTE, WASTE, .6)
    c.text(282, 445, f'3″ main building drain  /  {MAIN_LOAD} DFU', 10, WASTE, 700)
    c.text(976, 445, f'3″ detached building drain  /  {WING_LOAD} DFU', 9.4, WASTE, 700)
    c.line(922,423,922,460,WASTE,1.7)
    c.line(960,423,960,460,WASTE,1.7)
    tag(c, 922, 469, 'S1', WASTE)
    tag(c, 960, 469, 'S2', WASTE)
    c.text(895, 474, 'CO', 8, WASTE, 700, 'end')
    c.text(985, 474, 'CO', 8, WASTE, 700)
    poly(c, [(922,477),(922,502),(841,502)],WASTE,1.7,ROUTE)
    poly(c, [(960,477),(960,502),(922,502)],WASTE,1.7,ROUTE)
    arrow(c, 843, 502, 180, WASTE)
    tag(c, 818, 502, 'S0', WASTE)
    c.text(794, 506, f'To verified lateral   /   {MAIN_LOAD+WING_LOAD} DFU shown', 10, WASTE, 700, 'end')
    c.text(42, 501, 'Design slope ¼″ per foot on horizontal drainage and sewer. Confirm fall to verified inverts.', 9.3, MUTED)
    c.line(42, 519, 1187, 519, LINE, .8)
    y = notes(c, 42, 543, 'Fixture connections', [
        ('Kitchen and laundry', 'Connect DW-1 through a listed dishwasher air gap to the sink tailpiece upstream of the trap. KS-1 carries the combined load. WM-1 discharges into a trapped, vented 2″ standpipe per CPC §804.1.'),
        ('Bathroom groups', 'DFU basis assumes private-use gravity-tank WCs at 1.6 gpf or less and a single showerhead per assembly. Verify retained fixtures, final outlets and actual water-heater discharges.'),
        ('Materials', 'Proposed listed ABS DWV for new sanitary branches subject to approved transitions. Select underground piping after confirming existing lateral material and utility requirements.'),
    ], 94)
    assert y < 739, y
    y = notes(c, 626, 543, 'Vents, cleanouts and final sizing', [
        ('Vents', 'Keep trap arms within CPC Table 1002.2. Rise before offsetting or joining per §905.3. Coordinate roof terminals, opening clearances per §906, and vent sizing and aggregate area per §§703.2 and 904.'),
        ('Drainage', 'Provide accessible cleanouts at building drain exits (CO) and as required by CPC §§707 and 719. Size sewer and vents after measuring developed lengths and confirming the lateral and invert elevations.'),
        ('Basis', '2025 California Plumbing Code, with Ventura Municipal Code Ch. 12.120. Drainage loads from CPC Table 702.1. City Building & Safety checklist BS-007, page 4.'),
    ], 96)
    assert y < 739, y
    return c


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('staging', type=Path)
    stage = parser.parse_args().staging
    stage.mkdir(parents=True, exist_ok=True)
    for (sheet, _), canvas in zip(SHEETS, (fixture_plan(), utility_plan(), dwv_plan())):
        canvas.write(stage/f'{sheet}.svg')
    criteria().write(stage/'E-00.svg')
    (stage/'plumbing-manifest.json').write_text(json.dumps({
        'sheets': [{'id': id, 'title': title} for id, title in SHEETS],
        'fixtureTags': list(FIXTURES),
        'utilityTags': ['W0','W1','W2','S0','S1','S2'],
    }, indent=2))


if __name__ == '__main__':
    main()
