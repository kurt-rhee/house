"""Extend full stove-wall soapstone to hood underside, with round window clear above."""
import bpy, json, math, shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text())
revision=doc['revision']+1
backup=base/'blender'/f'before-full-stove-splash-revision-{revision}'
backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:
    shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']

def box(name,bounds,inverse=None):
    x,y,z=bounds
    v=[Vector((x[i],y[j],z[k])) for i,j,k in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
    if inverse is not None:v=[inverse@p for p in v]
    m=bpy.data.meshes.new(name)
    m.from_pydata(v,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    m.update();return m

for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    hood=next(o for o in sc.objects if o.name.startswith('Architectural hood | tapered plaster shell'))
    top=min((hood.matrix_world@Vector(c)).z for c in hood.bound_box)
    slab=next(o for o in sc.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
    stone=slab.data.materials[0]
    slab.data=box('Full stove-wall soapstone to underside of hood',[(-2.0241,-2.0041),(5.6316,8.4949),(.9325,top)],slab.matrix_world.inverted())
    slab.data.materials.append(stone)
    slab['source_revision']=revision;slab['top_mm']=round(top*1000,1);slab['width_mm']=2863.3
    slab.parent['source_revision']=revision;slab.parent['top_mm']=round(top*1000,1)
    slab.parent['location']='Full stove counter run, top aligned to hood underside'

    # Lift the circular opening 200 mm to keep a straight backsplash top with 30 mm clearance.
    root=next(o for o in sc.objects if o.name.startswith('Window | Round stove-side aperture'))
    old_center=root['center_height_mm']/1000
    new_center=top+.225+.03
    delta=new_center-old_center
    root.location.z+=delta;root['center_height_mm']=round(new_center*1000,1);root['source_revision']=revision
    wall=next(o for o in sc.objects if o.name.startswith('Kitchen west | plaster wall with circular window'))
    plaster=wall.data.materials[0]
    wall.data=box('Stove wall with raised circular daylight opening',[(-2.1829,-2.0251),(6.483,8.5738),(0,2.4384)],wall.matrix_world.inverted())
    wall.data.materials.append(plaster)
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.225,depth=.6,location=(-2.104,7.83,new_center),rotation=(0,math.pi/2,0))
    cutter=bpy.context.object
    bpy.ops.object.select_all(action='DESELECT');wall.select_set(True);bpy.context.view_layer.objects.active=wall
    mod=wall.modifiers.new('Raised circular opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    solvers=[i.identifier for i in mod.bl_rna.properties['solver'].enum_items]
    if 'EXACT' in solvers:mod.solver='EXACT'
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    wall['source_revision']=revision
    sc['source_revision']=revision
    sc['backsplash_notes']='Continuous 20 mm honed soapstone across full stove counter run, countertop 932.5 mm to hood underside 1805 mm. Round window lifted to center 2060 mm, 30 mm plaster below frame. Sink-wall low band retained.'
    sc['stove_wall_notes']='Full-width soapstone to hood underside; round window above at 2060 mm center'
    bpy.context.view_layer.update()
    assert abs(max((slab.matrix_world@Vector(c)).z for c in slab.bound_box)-top)<1e-5
    assert new_center+.225<2.4384
    print(sc.name,'splash top',round(top*1000),'window center',round(new_center*1000))

for label in doc['room_labels'].values():
    if label['name'].startswith('Soapstone:'):label['name']='Soapstone: full stove wall / top 1805 mm at hood'
    elif label['name'].startswith('Round stove window:'):label['name']='Round stove window: Ø450 mm / center 2060 mm AFF'
doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:
    p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.shading.type='RENDERED'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt'
p.write_text(p.read_text()+f'\nRevision {revision}: continuous stove-wall soapstone raised to hood underside at 1805 mm; full 2863.3 mm counter run. Round window lifted 200 mm to center 2060 mm, leaving 30 mm plaster between stone and frame. Warm lighting retained.\n')
