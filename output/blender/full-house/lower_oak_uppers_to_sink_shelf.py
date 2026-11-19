"""Lower side cabinetry to sink shelf height, retaining raised concealed hood bay."""
import bpy, json, shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());revision=doc['revision']+1
backup=base/'blender'/f'before-lowered-uppers-revision-{revision}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']

def bounds(o):
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    return [(min(p[i] for p in bb),max(p[i] for p in bb)) for i in range(3)]
def lower_bottom(o,height):
    bb=bounds(o);old=bb[2][0];inv=o.matrix_world.inverted()
    for v in o.data.vertices:
        world=o.matrix_world@v.co
        if abs(world.z-old)<.00001:world.z=height;v.co=inv@world
    o.data.update()
def make_panel(sc,root,name,x0,x1,y0,y1,z0,z1,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
    o=bpy.context.object;o.name='Oak stove uppers | '+name
    for c in list(o.users_collection):c.objects.unlink(o)
    root.users_collection[0].objects.link(o);o.parent=root;o.dimensions=(x1-x0,y1-y0,z1-z0)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    uv=o.data.uv_layers.active or o.data.uv_layers.new()
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=(co.z/1.6,co.y/1.2)
    b=o.modifiers.new('Soft oak edges','BEVEL');b.width=.001;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    o['source_revision']=revision
    return o

for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    shelf=next(o for o in sc.objects if o.name.startswith('Panoramic shelf | floating'))
    level=bounds(shelf)[2][1]
    root=next(o for o in sc.objects if o.name.startswith('Kitchen | Full-width ceiling oak'))
    parts=[o for o in sc.objects if o.name.startswith('Oak stove uppers |')]
    wood=parts[0].data.materials[0]
    for o in list(parts):
        n=o.name
        if 'flush oak front 2' in n or 'flush oak front 4' in n:
            b=bounds(o);a,c=b[1];split=6.3876 if 'front 2' in n else 7.2365
            leftlow='front 2' in n
            make_panel(sc,root,'side lower door beside hood',*b[0],a,split-.0015,level+.002 if leftlow else b[2][0],b[2][1],wood)
            make_panel(sc,root,'hood access front',*b[0],split+.0015,c,b[2][0] if leftlow else level+.002,b[2][1],wood)
            bpy.data.objects.remove(o,do_unlink=True)
        elif any(f'flush oak front {i}' in n for i in [1,5,6]):lower_bottom(o,level+.002)
        elif any(f'vertical gable {i}' in n for i in [1,2,5,6,7]):lower_bottom(o,level)
        elif 'storage base' in n:o.location.z-=1.805-level
    for y in [6.3876,7.2365]:make_panel(sc,root,'hood bay side',-2.0251,-1.6631,y-.009,y+.009,level,2.4384,wood)
    root['bottom_mm']=round(level*1000,1);root['hood_bottom_mm']=1805;root['source_revision']=revision
    root['construction']='Side cabinets align with sink shelf; raised central concealed hood bay retains existing cooktop clearance'
    sc['source_revision']=revision
    sc['hood_notes']='Side oak uppers lowered to sink shelf top 1476 mm; central hood bay remains at 1805 mm; ceiling top 2438.4 mm'
    bpy.context.view_layer.update()
    print(sc.name,'side cabinet underside',round(level*1000),'hood bay underside 1805')

f=doc['fixtures']['cc99b809-cb08-51b4-a631-7c1eae3d9db0']
f['style']='oak_uppers_side_bottom_1476mm_aligned_sink_shelf_raised_hood_bay_1805mm_ceiling_2438.4mm'
for label in doc['room_labels'].values():
    if label['name'].startswith('Concealed hood in oak'):label['name']='Oak uppers: bottom 1476 mm / hood bay 1805 mm'
doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {revision}: side oak cabinets extended down 329 mm to align underside with sink shelf top at 1476 mm. Concealed hood bay stays at 1805 mm above cooktop, with stepped underside and side panels. Round window remains unobstructed; 2D notes updated.\n')
