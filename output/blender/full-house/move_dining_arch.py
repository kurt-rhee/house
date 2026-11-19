"""Synchronize the existing arch location with its editable 2D opening station."""
import bpy, json
from pathlib import Path
from mathutils import Vector

base = Path('/Users/kurt/Programs/house/output/blender/full-house')
doc = json.loads((base.parent.parent / 'floor-plan.house.json').read_text())
door = doc['doors']['862d92a8-b4be-4526-b8c9-f2461f36b83a']
wall = doc['walls'][door['wall']]
assert wall['start']['x'] == wall['end']['x'] and wall['end']['y'] > wall['start']['y']
yc = (10783 - wall['start']['y'] - door['position']) / 1000
half = door['width'] / 2000
lo, hi = yc-half, yc+half
header = bpy.data.objects['Dining arch | curved plaster header']
corners = [header.matrix_world @ Vector(p) for p in header.bound_box]
old_yc = (min(p.y for p in corners) + max(p.y for p in corners)) / 2
delta = yc - old_yc
header.location.y += delta
bpy.data.objects['Dining arch | continuous plaster reveal'].location.y += delta
piers = sorted((o for o in bpy.context.scene.objects if o.name.startswith('Dining arch | plaster pier')), key=lambda o: o.location.y)
wall_lo = (10783-wall['end']['y'])/1000
wall_hi = (10783-wall['start']['y'])/1000
for pier, a, b in [(piers[0],wall_lo,lo),(piers[1],hi,wall_hi)]:
    assert b > a
    pier.location.y = (a+b)/2
    pier.dimensions.y = b-a
bpy.context.view_layer.update()
header['source_door_id'] = door['id']
header['source_revision'] = doc['revision']
header['opening_center_station_mm'] = door['position']
scene = bpy.context.scene
scene['source_revision'] = doc['revision']
scene.name = 'Full House | Drawing Revision '+str(doc['revision'])
scene['kitchen_revision_notes'] = '1400 mm rounded arch sink-side jamb aligned with front face of the sink cabinet run; crown 2180 mm and spring 1780 mm. No door. Oak fridge surround and upper cabinets retained.'
scene.camera = bpy.data.objects['Current | Kitchen arch and fridge']
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
assert abs((lo+hi)/2-yc) < 1e-7
print(f'Arch moved {-delta*1000:.1f} mm toward fridge; opening y={lo:.4f} to {hi:.4f}; revision {doc["revision"]}')
