"""Interior wall faces and proposed electrical layout for floor-plan.house.json.

CAD axes increase westward and northward. A station is a CAD x or y coordinate.
Receptacle heights are design targets for box centers above finished floor.
"""
import json
from dataclasses import dataclass, field
from math import ceil, hypot
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = json.loads((ROOT / 'output/floor-plan.house.json').read_text())
MEASUREMENTS = json.loads(Path(__file__).with_name('model-measurements.json').read_text())
WALLS = {wall['name']: wall for wall in PROJECT['walls'].values()}
LABELS = {label['name']: label for label in PROJECT['room_labels'].values()}
HEIGHT = 2438.4
MM = 25.4
FACES = {}
DEVICES = []

@dataclass
class Opening:
    low: float
    high: float
    sill: float | None
    head: float | None
    kind: str
    id: str = ''
    hinge_station: float | None = None

    @property
    def center(self):
        return (self.low + self.high) / 2

@dataclass
class Detail:
    name: str
    low: float
    high: float
    bottom: float
    top: float
    style: str

@dataclass
class Device:
    tag: str
    face: str
    station: float
    height: float
    circuit: str
    use: str
    provisional: bool = False

@dataclass
class Face:
    id: str
    room: str
    direction: str
    fixed: float
    low: float
    high: float
    hosts: list
    openings: list = field(default_factory=list)
    details: list = field(default_factory=list)
    devices: list = field(default_factory=list)

    @property
    def span(self):
        return self.high - self.low

    @property
    def across(self):
        return self.direction in 'SN'

    def offset(self, station):
        return station - self.low if self.direction in 'SW' else self.high - station

    def point(self, station, inset=0):
        shift = inset if self.direction in 'SE' else -inset
        return (station, self.fixed + shift) if self.across else (self.fixed + shift, station)

    def detail(self, name, lo, hi, bottom, top, style='cabinet'):
        self.details.append(Detail(name, lo, hi, bottom, top, style))

    def model(self, name, obj, style='cabinet'):
        x, y, z = MEASUREMENTS['model_bounds'][obj]
        self.detail(name, *(x if self.across else y), *z, style)


def face(key, room, direction, fixed, lo, hi, *hosts, portals=()):
    f = FACES[key] = Face(key, room, direction, fixed, lo, hi, list(hosts))
    axis = 'x' if f.across else 'y'
    host_ids = {WALLS[name]['id'] for name in hosts}
    for group in ('doors', 'windows'):
        for entry in PROJECT[group].values():
            if entry['wall'] not in host_ids:
                continue
            wall = PROJECT['walls'][entry['wall']]
            center = wall['start'][axis] + entry['position']
            a, b = center - entry['width'] / 2, center + entry['width'] / 2
            if min(hi, b) - max(lo, a) < 0.1:
                continue
            stub = entry['id'][:8]
            kind = entry.get('kind', 'Window')
            if stub == 'c0d5528e':
                kind = 'Round'
            sill, head = MEASUREMENTS['opening_sill_head'].get(stub, (0, 2032))
            hinge = (b if entry.get('hinge_at_end') else a) if kind == 'Hinged' else None
            f.openings.append(Opening(max(lo, a), min(hi, b), sill, head, kind, stub, hinge))
    for a, b, head in portals:
        f.openings.append(Opening(a, b, 0, head, 'Portal'))
    f.openings.sort(key=lambda op: op.low)
    return f


def room(prefix, name, *, walls=None, edges=None, extras=None):
    if walls is None:
        refs = LABELS[name]['clear_spans']
        walls = [PROJECT['walls'][refs[key]]['name'] for key in ('north', 'east', 'south', 'west')]
    if edges is None:
        edges = []
        for direction, name_wall in zip('SWNE', walls):
            w = WALLS[name_wall]
            coord = 'y' if direction in 'SN' else 'x'
            sign = 1 if direction in 'SE' else -1
            edges.append(w['start'][coord] + sign * w['thickness'] / 2)
    y0, x1, y1, x0 = edges
    extras = extras or {}
    for i, (direction, fixed, lo, hi, name_wall) in enumerate(zip(
        'SWNE', edges, [x0, y0, x0, y0], [x1, y1, x1, y1], walls
    ), 1):
        face(f'{prefix}{i}', name, direction, fixed, lo, hi, name_wall, **extras.get(i, {}))


def outlet(key, station, inches, circuit, use, tag=None, provisional=False):
    f = FACES[key]
    if tag is None:
        index = sum(d.face.startswith(key[:-1]) and d.tag.startswith(key[:-1]+'-') for d in DEVICES) + 1
        tag = f'{key[:-1]}-{index:02d}'
    d = Device(tag, key, station, inches * MM, circuit, use, provisional)
    assert f.low + 55 < station < f.high - 55, (d, 'outside wall face')
    for op in f.openings:
        if op.low - 55 < station < op.high + 55:
            assert op.sill is not None and (d.height + 60 < op.sill or
                   (op.head is not None and d.height - 60 > op.head)), (d, op)
    assert all(other.tag != tag for other in DEVICES), tag
    DEVICES.append(d)
    f.devices.append(d)


def subtract(spans, cut):
    result = []
    for a, b in spans:
        if cut[1] <= a or cut[0] >= b:
            result.append((a, b))
        else:
            if a < cut[0]:
                result.append((a, cut[0]))
            if cut[1] < b:
                result.append((cut[1], b))
    return result


def general(key, circuit, built_in=(), pocket=(), height=18):
    f = FACES[key]
    runs = [(f.low, f.high)]
    for hole in [(o.low, o.high) for o in f.openings if o.sill == 0] + list(built_in):
        runs = subtract(runs, hole)
    for a, b in runs:
        if b - a < 2 * 12 * MM:
            continue
        allowed = [(a + 80, b - 80)]
        for cut in list(pocket) + [(o.low - 90, o.high + 90) for o in f.openings if o.sill is None]:
            allowed = subtract(allowed, cut)
        assert allowed, (key, a, b, 'no available wall box position')
        count = ceil((b - a) / (12 * 12 * MM))
        stations = []
        for i in range(count):
            target = a + (i + 0.5) * (b - a) / count
            closest = min((max(l, min(r, target)) for l, r in allowed), key=lambda x: abs(x-target))
            outlet(key, closest, height, circuit, 'Wall duplex')
            stations.append(closest)
        distances = [stations[0] - a, b - stations[-1]]
        distances.extend((q - p) / 2 for p, q in zip(stations, stations[1:]))
        assert max(distances) <= 6 * 12 * MM, (key, a, b, stations)


# Kitchen and dining. All station values are measured to the centers of boxes.
face('K1', 'Kitchen', 'S', 2288.1, 17358, 20356.2, 'Main north')
face('K2', 'Kitchen', 'E', 17358, 2288.1, 6351.45, 'Kitchen west', 'Laundry pocket-door partition')
face('K3', 'Kitchen', 'N', 5588.75, 18895.4875, 20356.2, 'Bedroom 3 closet north')
face('K4', 'Kitchen', 'W', 20356.2, 2288.1, 5588.75, 'Main center partition')
face('K5', 'Kitchen', 'N', 6351.45, 16792.55, 18895.4875, 'Kitchen Bedroom 3 partition')
FACES['K1'].detail('Range-side return (end view)', 17358, 17993, 0, 897.5, 'outline')
FACES['K1'].detail('Return worktop (end view)', 17358, 17993, 897.5, 932.5, 'stone')
FACES['K1'].model('Soapstone worktop', 'Soapstone kitchen countertop | centered sink run', 'stone')
FACES['K1'].detail('Oak sink run', 17993, 20356.2, 0, 897.5)
FACES['K1'].model('Floating oak shelf', 'Panoramic shelf | floating white oak board', 'stone')
FACES['K1'].detail('Apron sink', 18438, 19276.2, 665, 932.5, 'porcelain')
FACES['K1'].detail('Dishwasher drawer', 19276.2, 19885.8, 210, 875, 'appliance')
FACES['K1'].detail('Sink faucet (verify)', 18805, 18909, 932.5, 1200, 'outline')
for name in ('Soapstone kitchen countertop', 'Soapstone kitchen countertop.004'):
    FACES['K2'].model('Soapstone worktop', name, 'stone')
FACES['K2'].detail('Oak base', 2288.1, 3689.925, 0, 897.5)
FACES['K2'].detail('Oak base', 4451.925, 5151.4, 0, 897.5)
FACES['K2'].detail('Induction range', 3689.925, 4451.925, 0, 932.5, 'appliance')
FACES['K2'].model('Plaster hood', 'Architectural hood | rectangular rounded plaster shell', 'plaster')
FACES['K3'].detail('Microwave base', 18895.4875, 19517.6, 0, 897.5)
FACES['K3'].model('Soapstone worktop', 'Base cabinet | soapstone countertop', 'stone')
FACES['K3'].model('Microwave', 'Microwave | body', 'appliance')
FACES['K3'].detail('Lower upper cabinet', 18895.4875, 19517.6, 1444, 1793)
FACES['K3'].detail('Upper cabinet', 18895.4875, 19517.6, 1793, HEIGHT)
FACES['K3'].model('Refrigerator', 'Refrigerator 31 x 26 body', 'appliance')
FACES['K3'].detail('Fridge upper', 19487.6, 20335, 2036, HEIGHT)
FACES['K3'].detail('Fridge surround', 19487.6, 19505.6, 0, 2036)
FACES['K3'].detail('Fridge surround', 20317, 20335, 0, 2036)

counter_runs = [
    ('K1', 17358, 18438, [(17870, 'S1')]),
    ('K1', 19276.2, 20356.2, [(19810, 'S2')]),
    ('K2', 2288.1, 3689.925, [(2775, 'S2'), (3290, 'S1')]),
    ('K2', 4451.925, 5151.4, [(4770, 'S2')]),
    ('K3', 18895.4875, 19517.6, [(19205, 'S1')]),
]
for key, a, b, boxes in counter_runs:
    assert b - a >= 12 * MM
    positions = [p for p,c in boxes]
    reaches = [positions[0] - a, b - positions[-1]]
    reaches.extend((q-p)/2 for p,q in zip(positions, positions[1:]))
    assert max(reaches) <= 24 * MM, (key, reaches)
    for p,circuit in boxes:
        outlet(key, p, 44, circuit, 'Counter duplex')

outlet('K1', 19030, 20, 'DW', 'Dishwasher in adjacent sink base', 'DW', True)
outlet('K2', 4070.925, 8, 'RG', 'Range connection', 'RG', True)
outlet('K2', 4090, 76, 'HD', 'Hood connection', 'HD', True)
outlet('K3', 19205, 66, 'MW', 'Microwave in accessible cabinet', 'MW', True)
outlet('K3', 19910, 18, 'RF', 'Refrigerator connection', 'RF', True)
general('K4', 'S2', built_in=[(2288.1, 2928.1), (4928.3, 5588.75)])
general('K5', 'S1', built_in=[(16792.55, 17358)])

portal_start, portal_end = 21040, 23472.75
room('D', 'Dining room', extras={3: {'portals': [(portal_start, portal_end, 2133.6)]}})
for n in range(1,5):
    general(f'D{n}', 'S1' if n % 2 else 'S2')

room('L', 'Laundry')
FACES['L1'].model('Washer / dryer', 'All-in-one washer-dryer body', 'appliance')
for name, lo, hi in [('Tandem waste',15963.4,16344.4), ('Pantry pullout',16344.4,16496.8)]:
    FACES['L1'].detail(name, lo, hi, 0, 897.5)
FACES['L1'].model('Worktop', 'Pullout cabinet pale worktop', 'stone')
FACES['L1'].model('Worktop', 'Pullout cabinet pale worktop.001', 'stone')
FACES['L1'].detail('Full-height pantry', 16509.5, 17182.6, 0, HEIGHT)
outlet('L1', 15660, 32, 'LA', 'All-in-one washer / dryer', 'WD', True)
outlet('L3', 16150, 18, 'LA', 'Laundry convenience duplex')

for prefix, name in [('B','Bathroom 1'), ('C','Bathroom 2'), ('A','Bathroom')]:
    room(prefix, name)
for prefix, wall, tub_start, head_name in [
    ('B','B2',12374.85,'Rain shower head.008'), ('C','C4',12273.25,'Rain shower head.009')
]:
    f = FACES[wall]
    f.detail('Floating oak vanity', 10869.0, 11459.0, 180, 780)
    f.detail('Basin rim', 10959, 11369, 780, 860, 'porcelain')
    f.detail('Mirror', 10876.5, 11451.5, 1047.5, 1912.5, 'glass')
    t = 11701.75
    f.detail('Water closet', t, t + 381, 0, 790, 'porcelain')
    f.detail('Tub end' if prefix == 'B' else 'Shower glass to verify',
             tub_start, 13136.85, 0, 510 if prefix == 'B' else 1980, 'porcelain' if prefix == 'B' else 'glass')
    f.model('Showerhead', head_name, 'outline')
    if prefix == 'B':
        f.detail('Tub/shower control zone', 12720, 12822, 815, 900, 'outline')
    else:
        f.detail('Shower mixer', 12672, 12772, 1002.5, 1037.5, 'outline')
    outlet(f'{prefix}1', 20870 if prefix == 'B' else 21490, 42, 'BM', 'Basin GFCI duplex', f'{prefix}-G')
FACES['B3'].detail('Tub apron', 19492.875, 21016.875, 0, 510, 'porcelain')
FACES['B2'].model('Tub filler', 'Tub filler.007', 'outline')
FACES['C3'].detail('Shower curb / glazing', 21231.85, 22670.6, 0, 1980, 'glass')
# The detached bath is traced from the existing reference. Resolve fixtures on site.
FACES['A4'].detail('Existing tub (verify)', 5943.8, 7127.3, 0, 550, 'existing')
FACES['A3'].detail('Tub end (verify)', 3997.6, 4700, 0, 550, 'existing')
FACES['A3'].detail('Water closet (verify)', 4880, 5280, 0, 780, 'existing')
FACES['A3'].detail('Basin cabinet (verify)', 5580, 6110, 0, 860, 'existing')
outlet('A2', 6890, 42, 'BA', 'Basin GFCI duplex', 'A-G', True)
for key, bathing_bounds, basin_edge in [
    ('B1', (19492.875, 12374.85, 21016.875, 13136.85), (20898, 10959)),
    ('C1', (21231.85, 12273.25, 22670.6, 13136.85), (21460, 10959)),
    ('A2', (3997.6, 5943.8, 4700, 7127.3), (5820, 6880)),
]:
    f = FACES[key]
    d = f.devices[0]
    x, y = f.point(d.station)
    x0, y0, x1, y1 = bathing_bounds
    bathing_distance = hypot(max(x0-x, 0, x-x1), max(y0-y, 0, y-y1))
    basin_distance = hypot(x-basin_edge[0], y-basin_edge[1])
    assert bathing_distance > 36*MM + 55 and basin_distance < 36*MM, key

room('P', 'Bedroom 3')
prior = FACES['P1']
face('P1', prior.room, prior.direction, prior.fixed, prior.low, prior.high,
     *prior.hosts, 'Bedroom 3 closet south')
room('M', 'Main bedroom')
room('G', 'Guest bedroom')
room('V', 'Living room', extras={1: {'portals': [(portal_start, portal_end, 2133.6)]},
                                 2: {'portals': [(8337.1, 9652.1, HEIGHT)]}})
room('O', 'Office')
room('H', 'Hallway')
room('T', 'Entrance', edges=(8494.9,25234.85,9652.1,24182.85),
     extras={4: {'portals': [(8494.9,9652.1,HEIGHT)]}})

FACES['M1'].detail('Bypass wardrobe', 16213.05, 17889.45, 0, 2286)
FACES['M1'].detail('Round oak shelf tower', 17889.45, 18499.05, 0, 2286, 'shelves')

for prefix, circuit in [('P','BR3'),('M','BR1'),('G','BR2'),('V','LV'),('O','OF')]:
    for index in range(1,5):
        key = f'{prefix}{index}'
        # The main-bath pocket retracts toward the north end of the common wall.
        pocket = [(11605,12475)] if key == 'M2' else []
        cabinet = [(16187.65,18499.05)] if key == 'M1' else []
        general(key, circuit, built_in=cabinet, pocket=pocket)

# Compact hall exceeds 10 ft along its centerline. Use the solid south wall.
outlet('H1', 21620, 18, 'LV', 'Hall duplex')
# Entrance face is under the foyer minimum area. Keep the walls drawn and keyed.

# The L-shaped attached space on the detached wing stays unnamed.
face('U1','ADU bedroom','S',5943.8,6233.1,9612.65,'Garage south')
face('U2','ADU bedroom','W',9612.65,5943.8,8757.9,'Large garage east')
face('U3','ADU bedroom','N',8757.9,3997.6,9612.65,'Guest wing south')
face('U4','ADU bedroom','E',3997.6,7232.5,8757.9,'Guest wing west')
face('U5','ADU bedroom','S',7232.5,3997.6,6233.1,'Guest bathroom south')
face('U6','ADU bedroom','E',6233.1,5943.8,7232.5,'ADU bedroom west')
for i in range(1,7):
    general(f'U{i}', 'AD')
room('J','Garage', walls=['Large garage north','Large garage east','Garage south','Garage dividing wall'])
outlet('J1', 5400, 44, 'GA', 'East bay GFCI duplex')
outlet('J3', 8250, 44, 'GA', 'West bay GFCI duplex')

# Compare against the supplied A-01 original. A change may be a new opening,
# different operation or size, or a revised opening in the same wall.
CHANGED_OPENINGS = {
    '9b44bb93', 'c0d5528e', '9150da68', '862d92a8', 'a7b3e93c',
    'db40b496', 'a97e8375', '9c1b496b', '7787ed89', 'aff1b521',
    '5cc81c53', '24a31300', '3a6af7b2', '660394bb', '68c7570b',
}


def is_changed_opening(opening):
    return opening.id in CHANGED_OPENINGS


SHEETS = [
    ('I-01','Kitchen | Sink and range',['K1','K2']),
    ('I-02','Kitchen | Appliance cabinetry and openings',['K3','K4','K5']),
    ('I-04','Laundry',['L1','L3']),
    ('I-05','Main house | Bathroom 1',['B2','B3','B4']),
    ('I-06','Main house | Bathroom 2',['C1','C3','C4']),
    ('I-08','Bedroom 3 | Glazed partition and closet',['P1']),
    ('I-09','Main bedroom | Wardrobe and exterior slider',['M1','M4']),
    ('I-13','Office | New and enlarged windows',['O1','O4']),
    ('I-14','ADU bedroom | Door-to-window conversion',['U3']),
]

DIRECTIONS = dict(S='South', W='West', N='North', E='East')
shown_faces = [FACES[key] for _, _, keys in SHEETS for key in keys]
assert all(f.details or any(is_changed_opening(o) for o in f.openings) for f in shown_faces)
assert CHANGED_OPENINGS <= {o.id for f in shown_faces for o in f.openings}
