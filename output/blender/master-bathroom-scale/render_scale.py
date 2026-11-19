import bpy, math
from mathutils import Vector
from pathlib import Path

out=Path('/Users/kurt/Programs/house/output/blender/master-bathroom-scale')
s=bpy.context.scene
# Isolate the existing master bathroom, preserving all fixture positions.
for o in s.objects:
    root=o
    while root.parent: root=root.parent
    p=root.matrix_world.translation
    bath=any(c.name.startswith('Bathrooms from drawing') for c in o.users_collection)
    keep=bath and ((root.name.startswith(('Bath |','Sink |','Toilet |')) and p.x<1.8) or o.name.startswith(('Bathroom 1 floor','B1 floor tile')))
    keep=keep or (o.name.startswith('Bathroom dividing wall |'))
    keep=keep or (o.name.startswith('Main bedroom south') and 0<p.x<1.75)
    o.hide_render=not keep
    if keep:
        for slot in o.material_slots:
            if slot.material and slot.material.name.startswith('View | Semi-transparent plaster'):
                slot.material=bpy.data.materials['Warm white plaster']

def mat(name,col,rough=.65):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough
    return m
skin=mat('Scale person | warm neutral skin',(.49,.30,.20))
shirt=mat('Scale person | muted blue shirt',(.13,.25,.31))
pants=mat('Scale person | charcoal trousers',(.105,.12,.13))
hair=mat('Scale person | dark hair',(.055,.035,.025))
shoes=mat('Scale person | shoes',(.06,.055,.05))
col=bpy.data.collections.new('Human scale | 1753 mm');s.collection.children.link(col)
root=bpy.data.objects.new('Person | 5 ft 9 in (1.753 m)',None);col.objects.link(root)
root.location=(.68,-.73,.014);root.rotation_euler.z=-math.pi/2
root['height_m']=1.753;root['purpose']='Architectural human scale reference'
def link(o,name,ma):
    o.name='Scale person | '+name
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o);o.parent=root;o.data.materials.append(ma)
    for p in o.data.polygons:p.use_smooth=True
    return o
def ell(name,loc,size,ma):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc)
    o=link(bpy.context.object,name,ma);o.scale=size;return o
def limb(name,a,b,r1,r2,ma):
    a,b=Vector(a),Vector(b);d=b-a
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=r1,radius2=r2,depth=d.length,location=(a+b)/2)
    o=link(bpy.context.object,name,ma);o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    be=o.modifiers.new('Soft transitions','BEVEL');be.width=.025;be.segments=3
    return o
def torso():
    verts=[];faces=[];N=48
    for z,rx,ry in [(.86,.15,.105),(.98,.145,.105),(1.12,.16,.11),(1.33,.205,.12),(1.40,.18,.10),(1.43,.075,.065)]:
        for i in range(N):
            a=2*math.pi*i/N;verts.append((rx*math.cos(a),ry*math.sin(a),z))
    for j in range(5):
        for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    faces.extend([tuple(reversed(range(N))),tuple(range(5*N,6*N))])
    me=bpy.data.meshes.new('Shirt mesh');me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new('Shirt',me);s.collection.objects.link(o);link(o,'Shirt',shirt)
    sub=o.modifiers.new('Tailored smooth shape','SUBSURF');sub.levels=2
torso()
ell('hips',(0,0,.88),(.17,.12,.16),pants)
for side in [-1,1]:
    x=side*.095
    limb('trouser leg upper',(x,0,.89),(x*1.2,-.01,.51),.085,.065,pants)
    ell('knee',(x*1.2,-.01,.51),(.067,.065,.075),pants)
    limb('trouser leg lower',(x*1.2,-.01,.51),(x*1.3,0,.12),.065,.043,pants)
    ell('shoe',(x*1.3,-.055,.055),(.061,.13,.055),shoes)
    shoulder=(side*.205,0,1.32);elbow=(side*.253,-.015,1.075);wrist=(side*.255,-.065,.875)
    ell('shirt shoulder',shoulder,(.075,.078,.095),shirt)
    limb('short sleeve',shoulder,(side*.236,-.008,1.19),.075,.063,shirt)
    limb('upper arm',(side*.236,-.008,1.20),elbow,.052,.042,skin)
    ell('elbow',elbow,(.044,.044,.05),skin)
    limb('forearm',elbow,wrist,.043,.03,skin)
    ell('hand',(side*.255,-.068,.835),(.036,.032,.068),skin)
limb('neck',(0,0,1.40),(0,0,1.52),.055,.055,skin)
ell('head',(0,-.012,1.625),(.087,.088,.125),skin)
ell('hair',(0,.005,1.683),(.089,.087,.070),hair)
ell('nose',(0,-.099,1.63),(.023,.023,.026),skin)
for side in [-1,1]:ell('ear',(side*.086,-.007,1.626),(.017,.021,.03),skin)
bpy.context.view_layer.update()
# Normalize the assembled figure to the stated height, from sole to crown.
points=[o.matrix_world@Vector(v) for o in col.objects if o.type=='MESH' for v in o.bound_box]
height=max(p.z for p in points)-min(p.z for p in points)
root.scale=(1.753/height,)*3

def area(name,loc,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((.8,-1.1,.7))-o.location).to_track_quat('-Z','Y').to_euler()
area('Scale view | large softbox',(-1,1,4.5),380,3)
area('Scale view | ceiling fill',(1,-1.1,3.7),170,2)
bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.77,.81,.84,1);bg.inputs[1].default_value=.5
d=bpy.data.cameras.new('Master bathroom | Human scale cutaway');d.type='ORTHO';d.ortho_scale=3.65
cam=bpy.data.objects.new(d.name,d);s.collection.objects.link(cam);cam.location=(-3.3,4.8,4.1)
cam.rotation_euler=(Vector((.86,-1.17,1.12))-cam.location).to_track_quat('-Z','Y').to_euler();s.camera=cam
s.cycles.samples=48;s.cycles.use_denoising=True
s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.resolution_percentage=100
s.render.filepath=str(out/'master-bathroom-person.png')
s['scale_render_notes']='Master bathroom (Bathroom 1). 1753 mm / 5 ft 9 in scale person. West/north walls and ceiling omitted for cutaway; fixture positions unchanged.'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'master-bathroom-person.blend'))
bpy.ops.render.render(write_still=True)
print('Rendered',s.render.filepath)
