"""Soft sculpted plaster hood and warm arched stone backsplash from reference."""
import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());revision=doc['revision']+1
backup=base/'blender'/f'before-rounded-hood-revision-{revision}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'));tour=bpy.data.scenes['House | Interior walkthrough']
stone=bpy.data.materials['Kitchen | Honed charcoal soapstone'].copy();stone.name='Backsplash | Warm greige honed stone'
for n in stone.node_tree.nodes:
    if n.type=='VALTORGB' and max(e.color[0]+e.color[1]+e.color[2] for e in n.color_ramp.elements)<1:
        n.color_ramp.elements[0].color=(.24,.213,.174,1)
        n.color_ramp.elements[-1].color=(.36,.325,.269,1)
    elif n.type=='BSDF_PRINCIPLED':n.inputs['Roughness'].default_value=.52

def mesh(name,verts,faces):
    m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update()
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(m);bm.free()
    return m

for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    hood=next(o for o in sc.objects if o.name.startswith('Architectural hood | tapered plaster shell'))
    inv=hood.matrix_world.inverted();cy=6.812075;bottom=1.476;top=2.4384
    verts=[];rings=25;points=68
    for j in range(rings):
        t=j/(rings-1)
        # A subtly full lower skirt tapers smoothly into a narrow ceiling neck.
        width=.85-.42*(t*t*(3-2*t))
        depth=.4-.11*(t*t*(3-2*t))
        z=bottom+(top-bottom)*t
        r=min(.145,width*.24,depth*.43)
        back=-2.0251;front=back+depth;ylo=cy-width/2;yhi=cy+width/2
        corners=[(front-r,yhi-r,0),(back+r,yhi-r,math.pi/2),(back+r,ylo+r,math.pi),(front-r,ylo+r,3*math.pi/2)]
        for x,y,start in corners:
            for k in range(17):
                a=start+k*math.pi/32
                verts.append(inv@Vector((x+r*math.cos(a),y+r*math.sin(a),z)))
    faces=[]
    for j in range(rings-1):
        for i in range(points):faces.append((j*points+i,j*points+(i+1)%points,(j+1)*points+(i+1)%points,(j+1)*points+i))
    faces.extend([tuple(range(points-1,-1,-1)),tuple((rings-1)*points+i for i in range(points))])
    plaster=hood.data.materials[0]
    hood.data=mesh('Smooth rounded sculptural plaster hood',verts,faces);hood.data.materials.append(plaster)
    for p in hood.data.polygons:p.use_smooth=len(p.vertices)==4
    for mod in list(hood.modifiers):hood.modifiers.remove(mod)
    b=hood.modifiers.new('Soft lower plaster lip','BEVEL');b.width=.004;b.segments=3
    hood['source_revision']=revision;hood['profile']='Soft rounded plan corners, curved taper to ceiling, warm mineral plaster'
    slab=next(o for o in sc.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
    # Straight lower sides with large quarter-circle shoulders and short flat crown.
    r=.30;half=.6;z0=.9325;z1=bottom
    outline=[(-half,z0),(half,z0),(half,z1-r)]
    for k in range(1,33):
        a=k*math.pi/64;outline.append((half-r+r*math.cos(a),z1-r+r*math.sin(a)))
    outline.append((-half+r,z1))
    for k in range(1,33):
        a=math.pi/2+k*math.pi/64;outline.append((-half+r+r*math.cos(a),z1-r+r*math.sin(a)))
    N=len(outline);inv=slab.matrix_world.inverted()
    verts=[inv@Vector((x,cy+y,z)) for x in [-2.0241,-2.0041] for y,z in outline]
    faces=[tuple(range(N-1,-1,-1)),tuple(N+i for i in range(N))]+[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)]
    slab.data=mesh('Warm arched stove backsplash with rounded shoulders',verts,faces);slab.data.materials.append(stone)
    slab['source_revision']=revision;slab['shape']='Arched top with 300 mm rounded shoulders';slab['finish']='Warm greige honed stone, subtle mineral veining'
    slab.parent['finish']='Warm greige honed stone';slab.parent['source_revision']=revision
    sc['source_revision']=revision
    sc['hood_notes']='Soft rounded sculptural plaster hood, 850 mm lower width, narrow 430 mm ceiling neck; bottom 1476 mm'
    sc['backsplash_notes']='Warm greige honed stone, 1200 mm centered panel, rounded arched shoulders radius 300 mm, top 1476 mm'
    print(sc.name,'rounded hood and arched warm stone created')

f=doc['fixtures']['cc99b809-cb08-51b4-a631-7c1eae3d9db0'];f['style']='sculptural_rounded_plaster_hood_curved_taper_ceiling_bottom_1476mm';f['material']='Warm ivory mineral plaster, soft rounded corners'
for label in doc['room_labels'].values():
    if label['name'].startswith('Soapstone:'):label['name']='Arched warm stone: 1200 mm / top 1476 mm'
    elif label['name'].startswith('Plaster hood:'):label['name']='Rounded plaster hood: soft taper to ceiling'
doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {revision}: reference-style soft sculptural plaster hood with rounded plan corners and smooth curved taper from 850 mm base to 430 mm ceiling neck. Backsplash changed to warm greige honed stone with arched top/300 mm rounded shoulders, still 1200 mm wide and top 1476 mm. Countertop stone, windows, sink shelf and warm lighting retained.\n')
