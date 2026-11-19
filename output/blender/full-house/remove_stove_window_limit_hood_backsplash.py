"""Revision 38: solid stove wall and soapstone only directly under hood."""
import bpy, json, shutil
from pathlib import Path
from mathutils import Vector

base = Path('/Users/kurt/Programs/house/output')
doc = json.loads((base / 'floor-plan.house.json').read_text())
old_revision = doc['revision']
revision = old_revision + 1
backup = base / 'blender' / f'before-stove-wall-revision-{revision}'
backup.mkdir(exist_ok=True)
for path in [base/'floor-plan.house.json', base/'blender/full-house/full-house.blend', base/'walkthrough/house-walkthrough.blend']:
    shutil.copy2(path, backup/path.name)
wall_id = 'ad218721-76be-4635-81dc-048de2d8bdae'
removed_windows = [key for key, window in doc['windows'].items() if window['wall'] == wall_id]
for key in removed_windows:
    del doc['windows'][key]
doc['revision'] = revision
for label in doc['room_labels'].values():
    if label['name'].startswith('Soapstone:'):
        label['name'] = 'Soapstone: under hood only / solid stove wall'

source = next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour = bpy.data.scenes['House | Interior walkthrough']
original_camera = tour.camera

def bounds(obj):
    bb = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return [(min(v[i] for v in bb), max(v[i] for v in bb)) for i in range(3)]

def box_mesh(name, extents, inverse=None):
    x,y,z = extents
    verts = [Vector((x[i],y[j],z[k])) for i,j,k in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
    if inverse is not None:
        verts = [inverse @ v for v in verts]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    mesh.update()
    return mesh

for scene in [source, tour]:
    bpy.context.window.scene = scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    assembly = next(o for o in scene.objects if o.name.startswith('Kitchen west | wall assembly'))
    pieces = [o for o in scene.objects if o.get('source_wall_id') == wall_id and o.type == 'MESH']
    plaster = next(o.data.materials[0] for o in pieces if o.name.startswith('Kitchen west solid'))
    wall_bounds = [(min(bounds(o)[i][0] for o in pieces), max(bounds(o)[i][1] for o in pieces)) for i in range(3)]
    collection = assembly.users_collection[0]
    for obj in pieces:
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = box_mesh('Kitchen west uninterrupted plaster wall', wall_bounds)
    mesh.materials.append(plaster)
    wall = bpy.data.objects.new('Kitchen west | solid plaster wall, no window', mesh)
    collection.objects.link(wall)
    wall.parent = assembly
    wall.matrix_parent_inverse = assembly.matrix_world.inverted()
    wall['source_wall_id'] = wall_id
    wall['source_revision'] = revision
    wall['view_wall_opacity'] = 1.0

    hood = next(o for o in scene.objects if o.name.startswith('Architectural hood | tapered plaster shell'))
    hb = bounds(hood)
    slab = next(o for o in scene.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
    stone = slab.data.materials[0]
    target = [(-2.0241,-2.0041), hb[1], (.9325, hb[2][0])]
    slab.data = box_mesh('Soapstone panel confined to architectural hood width', target, slab.matrix_world.inverted())
    slab.data.materials.append(stone)
    slab['source_revision'] = revision
    slab['width_mm'] = (hb[1][1]-hb[1][0])*1000
    slab['bottom_mm'] = 932.5
    slab['top_mm'] = hb[2][0]*1000
    root = slab.parent
    root['source_revision'] = revision
    root['top_mm'] = hb[2][0]*1000
    root['location'] = 'Only directly beneath architectural range hood; plaster behind stove-side shelf'
    for key in ['low_band_top_mm','low_band_height_mm']:
        if key in root:
            del root[key]
    scene['source_revision'] = revision
    scene['stove_wall_notes'] = 'Solid plaster stove wall; former west window and all trim removed'
    scene['backsplash_notes'] = 'Stove wall soapstone only beneath range hood, hood-width panel from countertop 932.5 mm to hood underside 1805 mm. Plaster behind floating shelf and former window. Existing sink low upstand and microwave full-height stone retained.'
    bpy.context.view_layer.update()
    assert not any('glazing' in o.name.lower() and o.get('source_wall_id') == wall_id for o in scene.objects)
    sb = bounds(slab)
    assert abs(sb[1][0]-hb[1][0]) < 1e-6 and abs(sb[1][1]-hb[1][1]) < 1e-6
    assert abs(sb[2][1]-hb[2][0]) < 1e-6
    assert wall.dimensions.z > 2.43
    print(scene.name, 'solid wall', bounds(wall), 'hood-only stone', sb)

source.name = f'Full House | Drawing Revision {revision}'
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:
    path.write_text(json.dumps(doc, indent=2)+'\n')
bpy.context.window.scene = source
bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene = tour
tour.camera = original_camera
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.shading.type = 'RENDERED'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
notes = base/'walkthrough/RENDER-NOTES.txt'
notes.write_text(notes.read_text()+f'\nRevision {revision}: removed stove-wall window and all trim, restored full-height plaster wall. Stove-wall soapstone confined to hood-width panel between countertop and hood underside. No stone behind stove-side shelf.\n')
print('Saved revision', revision, 'removed window IDs', removed_windows)
