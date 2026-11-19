"""Widen the laundry pocket opening northward, preserving the south jamb."""
import bpy
import json
import shutil
from pathlib import Path
from mathutils import Vector

BASE = Path('/Users/kurt/Programs/house/output')
DOOR = '9150da68-b336-4060-bdae-30eb0d80deca'
COUNTER = 'c08078d4-006c-4eba-8032-0bf18c432cec'
WALL = '743fa984-048d-48a9-923a-a99198a7c60e'
DELTA = .1524
OLD_JAMB = 5.34595
NEW_JAMB = OLD_JAMB + DELTA
OLD_END = 5.47925
NEW_END = OLD_END + DELTA
RUN_TOP = 6.431075

def bounds(o):
    pts = [o.matrix_world @ Vector(v) for v in o.bound_box]
    return min(v.y for v in pts), max(v.y for v in pts)

def reshape(o, fn):
    # Work on private mesh data so archived scenes remain intact.
    o.data = o.data.copy()
    mat = o.matrix_world.copy()
    inv = mat.inverted()
    for v in o.data.vertices:
        p = mat @ v.co
        p.y = fn(p.y)
        v.co = inv @ p
    o.data.update()

path = BASE / 'floor-plan.house.json'
doc = json.loads(path.read_text())
if doc['doors'][DOOR]['width'] == 914.4:
    shutil.copy2(path, BASE / 'floor-plan.before-42in-laundry-door.house.json')
    doc['doors'][DOOR]['width'] = 1066.8
    doc['doors'][DOOR]['position'] -= 76.2
    doc['fixtures'][COUNTER]['depth'] -= 152.4
    doc['revision'] += 1
    path.write_text(json.dumps(doc, indent=2) + '\n')
assert abs(doc['doors'][DOOR]['width'] - 1066.8) < .001

changed = []
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
for root in list(bpy.data.objects):
    if not root.get('laundry_pocket_door'):
        continue
    if abs(root.get('opening_width_mm', 0) - 1066.8) < .001:
        continue
    scenes = [s for s in bpy.data.scenes if root.name in s.objects]
    assert scenes
    scene = scenes[0]
    # Widen the header and trim, shorten the north wall, and move its jamb.
    for o in scene.objects:
        if o.type != 'MESH' or o.get('source_wall_id') != WALL:
            continue
        low, high = bounds(o)
        if abs(low - OLD_JAMB) < .002 and high > 6.4:
            reshape(o, lambda y: NEW_JAMB + (y-OLD_JAMB)*(high-NEW_JAMB)/(high-OLD_JAMB))
        elif 'opening header' in o.name or 'head trim' in o.name:
            reshape(o, lambda y: low + (y-low)*(high+DELTA-low)/(high-low))
        elif 'jamb' in o.name and low > 5:
            o.location.y += DELTA
    # Extend the concealed leaf and move it fully into the north pocket.
    root.location.y += DELTA
    for o in root.children:
        if 'concealed leaf' in o.name:
            o.data = o.data.copy()
            for v in o.data.vertices:
                v.co.y *= 1066.8/914.4
            o.location.y = 1.0668/2
            o.data.update()
    root['opening_width_mm'] = 1066.8
    root['source_revision'] = doc['revision']
    bpy.context.view_layer.update()
    # Compress only the cabinet segment between the range and the doorway.
    for r in scene.objects:
        if r.type != 'EMPTY' or r.get('source_fixture_id') != COUNTER:
            continue
        for o in r.children_recursive:
            if o.type != 'MESH':
                continue
            low, high = bounds(o)
            if low >= OLD_END-.002 and high <= RUN_TOP+.002:
                reshape(o, lambda y: RUN_TOP + (y-RUN_TOP)*(RUN_TOP-NEW_END)/(RUN_TOP-OLD_END))
        r['plan_footprint_mm'] = [doc['fixtures'][COUNTER]['width'], doc['fixtures'][COUNTER]['depth']]
    for o in scene.objects:
        if o.type == 'MESH' and o.name.startswith('Backsplash | Honed soapstone slab'):
            reshape(o, lambda y: y+DELTA if abs(y-OLD_END) < .002 else y)
        if o.get('source_fixture_id') == COUNTER:
            o['plan_footprint_mm'] = [doc['fixtures'][COUNTER]['width'], doc['fixtures'][COUNTER]['depth']]
            o['source_revision'] = doc['revision']
    scene['source_revision'] = doc['revision']
    scene['laundry_door_notes'] = '42 inch pocket opening; south jamb retained; north jamb moved 152.4 mm. Cabinet end and countertop/backsplash shortened 152.4 mm. Stove shelf retains clearance.'
    if scene.name.startswith('Full House | Drawing Revision'):
        scene.name = 'Full House | Drawing Revision ' + str(doc['revision'])
    changed.append(scene.name)

for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
for root in bpy.data.objects:
    if root.get('laundry_pocket_door'):
        assert abs(root['opening_width_mm'] - 1066.8) < .001
        assert abs(root.matrix_world.translation.y - NEW_JAMB) < .00001
        print('VERIFIED', root.name, 'opening 42 inches; north jamb', NEW_JAMB)
for scene_name in {s.name for s in bpy.data.scenes if any(o.get('laundry_pocket_door') for o in s.objects)}:
    scene = bpy.data.scenes[scene_name]
    for o in scene.objects:
        if o.type == 'MESH' and o.name.startswith('Soapstone kitchen countertop') and o.get('source_fixture_id') == COUNTER:
            low, high = bounds(o)
            if low < 6:
                assert abs(low - NEW_END) < .00001, (scene.name, o.name, low, high, NEW_END)
                print('VERIFIED cabinet/counter setback mm', (low-NEW_JAMB)*1000)
        if o.type == 'MESH' and o.name.startswith('Stove shelf | floating oak board'):
            assert bounds(o)[0] > NEW_JAMB + .012
            print('VERIFIED floating shelf clears doorway by mm', (bounds(o)[0]-NEW_JAMB)*1000)
(BASE / 'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc, indent=2) + '\n')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Saved widened laundry doorway:', changed, 'drawing revision', doc['revision'])
