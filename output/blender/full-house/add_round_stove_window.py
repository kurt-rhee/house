"""Add a small bronze-framed circular window right of the range (revision 39)."""
import bpy, json, math, shutil, uuid
from pathlib import Path
from mathutils import Vector

base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text())
revision=doc['revision']+1
wall_id='ad218721-76be-4635-81dc-048de2d8bdae'
window_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen/round-stove-window'))
label_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen/round-stove-window-note'))
backup=base/'blender'/f'before-round-window-revision-{revision}'
backup.mkdir(exist_ok=True)
for path in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:
    shutil.copy2(path,backup/path.name)

# Right when facing the west/stove wall is north, towards the sink-wall corner.
center_y=7.83
center_z=1.86
radius=.225
clear_radius=.205
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']
bronze=bpy.data.materials.get('Window | Satin warm bronze')
if bronze is None:
    bronze=bpy.data.materials.new('Window | Satin warm bronze')
    bronze.use_nodes=True
    shader=next(n for n in bronze.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value=(.21,.15,.085,1)
    shader.inputs['Metallic'].default_value=.75
    shader.inputs['Roughness'].default_value=.3
glass=bpy.data.materials['Finish | Clear low iron window glass']

def ring_mesh(name, outer, inner, x0, x1, count=128):
    verts=[]
    for x,r in [(x0,outer),(x1,outer),(x0,inner),(x1,inner)]:
        verts.extend((x,center_y+r*math.cos(i*2*math.pi/count),center_z+r*math.sin(i*2*math.pi/count)) for i in range(count))
    faces=[]
    for i in range(count):
        j=(i+1)%count
        faces.extend([(i,j,count+j,count+i),(2*count+i,3*count+i,3*count+j,2*count+j),(i,2*count+i,2*count+j,j),(count+i,count+j,3*count+j,3*count+i)])
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    return mesh

for scene in [source,tour]:
    bpy.context.window.scene=scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    wall=next(o for o in scene.objects if o.name.startswith('Kitchen west | solid plaster wall'))
    # Applied boolean makes a real daylight opening, also preserved by future GLB exports.
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=radius,depth=.6,location=(-2.104,center_y,center_z),rotation=(0,math.pi/2,0))
    cutter=bpy.context.object
    cutter.name='Temporary circular aperture cutter'
    bpy.ops.object.select_all(action='DESELECT')
    wall.select_set(True);bpy.context.view_layer.objects.active=wall
    mod=wall.modifiers.new('Circular daylight opening','BOOLEAN')
    mod.operation='DIFFERENCE'
    mod.object=cutter
    solvers=[i.identifier for i in mod.bl_rna.properties['solver'].enum_items]
    if 'EXACT' in solvers:mod.solver='EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    wall.name='Kitchen west | plaster wall with circular window'
    wall['source_revision']=revision
    col=bpy.data.collections.new('Kitchen | Small circular stove-side window')
    scene.collection.children.link(col)
    root=bpy.data.objects.new('Window | Round stove-side aperture',None)
    col.objects.link(root)
    root['source_window_id']=window_id
    root['source_revision']=revision
    root['shape']='Circular fixed glazing'
    root['diameter_mm']=450
    root['clear_glazing_diameter_mm']=410
    root['center_height_mm']=1860
    root['position_notes']='Right of stove facing stove wall; between hood and sink-wall corner'
    mesh=ring_mesh('Round window continuous bronze reveal',radius,clear_radius,-2.193,-2.013)
    mesh.materials.append(bronze)
    frame=bpy.data.objects.new('Round stove window | slim bronze frame and reveal',mesh)
    col.objects.link(frame);frame.parent=root
    bevel=frame.modifiers.new('Soft frame edges','BEVEL');bevel.width=.0012;bevel.segments=3
    frame.modifiers.new('Frame weighted normals','WEIGHTED_NORMAL')
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=clear_radius+.001,depth=.006,location=(-2.13,center_y,center_z),rotation=(0,math.pi/2,0))
    pane=bpy.context.object
    pane.name='Round stove window | clear low-iron glazing'
    for c in list(pane.users_collection):c.objects.unlink(pane)
    col.objects.link(pane);pane.parent=root;pane.data.materials.append(glass)
    pane['source_window_id']=window_id
    pane['source_revision']=revision
    scene['source_revision']=revision
    scene['stove_wall_notes']='Small fixed circular bronze-framed window right of stove, 450 mm overall diameter, center 1860 mm above floor; soapstone remains only beneath hood.'
    bpy.context.view_layer.update()
    hood=next(o for o in scene.objects if o.name.startswith('Architectural hood | tapered plaster shell'))
    hood_right=max((hood.matrix_world@Vector(c)).y for c in hood.bound_box)
    assert center_y-radius>hood_right+.25
    assert center_z-radius>1.476+.1
    assert len(wall.data.polygons)>20
    print(scene.name,'round window diameter 450mm, center',center_y,center_z,'hood clearance mm',round((center_y-radius-hood_right)*1000))

wall=doc['walls'][wall_id]
plan_center_y=10783.0-center_y*1000
doc['windows'][window_id]={'id':window_id,'wall':wall_id,'position':plan_center_y-wall['start']['y'],'width':450.0}
doc['room_labels'][label_id]={'id':label_id,'name':'Round stove window: Ø450 mm / center 1860 mm AFF','position':{'x':16470.0,'y':2820.0}}
doc['revision']=revision
source.name=f'Full House | Drawing Revision {revision}'
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:
    path.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source
bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.shading.type='RENDERED'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
notes=base/'walkthrough/RENDER-NOTES.txt'
notes.write_text(notes.read_text()+f'\nRevision {revision}: added real circular daylight opening right of range facing stove wall. 450 mm overall bronze frame, 410 mm clear glazing, center 1860 mm AFF; world Y7830 mm. 2D plan window and elevation note synchronized. Hood-only soapstone retained.\n')
print('Saved revision',revision,'window',window_id)
