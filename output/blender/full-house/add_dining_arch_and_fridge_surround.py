import bpy, math
from mathutils import Vector
from pathlib import Path

s = bpy.context.scene
base = Path('/Users/kurt/Programs/house/output/blender/full-house')
col = bpy.data.collections.get('Kitchen arch and refrigerator surround')
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new('Kitchen arch and refrigerator surround')
    s.collection.children.link(col)

# Remove the two scale figures and every component of their assemblies.
people = [o for o in s.objects if o.name.startswith('Person ')]
remove = set(people)
for o in people:
    remove.update(o.children_recursive)
for o in remove:
    bpy.data.objects.remove(o, do_unlink=True)

oak = bpy.data.materials['Natural oak']
metal = bpy.data.materials['Brushed chrome']
partition = [o for o in s.objects if o.name.startswith('Main center partition')]
wallmat = next(o.data.materials[0] for o in partition if '| wall' in o.name)
trim = next(o.data.materials[0] for o in partition if 'jamb' in o.name)
wid = '9d3f5626-ab84-4765-8db3-b1e78aa937d9'
for o in partition:
    bpy.data.objects.remove(o, do_unlink=True)

def box(name, loc, dims, mat, parent=None, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o)
    o.name = name
    o.parent = parent
    o.location = loc
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Soft edges', 'BEVEL'); mod.width=bevel; mod.segments=3
        o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return o

# Broad elliptical arch: 1400 mm clear width, 2180 mm crown, 1780 mm spring line.
xc, yc, half, spring, rise, H, thick = 1.0257, 7.488925, .7, 1.78, .4, 2.4384, .1052
lo, hi = yc-half, yc+half
for a,b in [(1.06515,lo),(hi,8.5738)]:
    o=box('Dining arch | plaster pier',(xc,(a+b)/2,H/2),(thick,b-a,H),wallmat)
    o['source_wall_id']=wid
verts=[]
N=64
for i in range(N+1):
    t=math.pi-i*math.pi/N
    y=yc+half*math.cos(t); z=spring+rise*math.sin(t)
    verts.extend([(xc-thick/2,y,z),(xc+thick/2,y,z),(xc-thick/2,y,H),(xc+thick/2,y,H)])
faces=[]
for i in range(N):
    a,b=4*i,4*(i+1)
    faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
faces.extend([(0,1,3,2),(4*N,4*N+2,4*N+3,4*N+1)])
me=bpy.data.meshes.new('Continuous rounded arch plaster'); me.from_pydata(verts,[],faces); me.update()
o=bpy.data.objects.new('Dining arch | curved plaster header',me);col.objects.link(o);me.materials.append(wallmat)
o['source_wall_id']=wid; o['clear_width_mm']=1400; o['crown_height_mm']=2180; o['opening_type']='Rounded arch, no door'
# A narrow plaster reveal makes the curved opening legible in the transparent-wall view.
curve=bpy.data.curves.new('Arch opening reveal','CURVE');curve.dimensions='3D';curve.bevel_depth=.012;curve.bevel_resolution=3
sp=curve.splines.new('POLY');points=[(xc,lo,0),(xc,lo,spring)]
points += [(xc,yc+half*math.cos(math.pi-i*math.pi/N),spring+rise*math.sin(math.pi-i*math.pi/N)) for i in range(1,N+1)]
points += [(xc,hi,0)];sp.points.add(len(points)-1)
for p,v in zip(sp.points,points):p.co=(*v,1)
o=bpy.data.objects.new('Dining arch | continuous plaster reveal',curve);col.objects.link(o);curve.materials.append(trim)

fridge=next(o for o in s.objects if o.name.startswith('Kitchen | Refrigerator'))
root=bpy.data.objects.new('Kitchen | Oak refrigerator enclosure',None);col.objects.link(root)
root.location=fridge.location;root.rotation_euler=fridge.rotation_euler
w,d,top=.7874,.6604,2.4384
gap,panel=.012,.018
left,right=-gap-panel/2,w+gap+panel/2
outer=w+2*(gap+panel)
for x in [left,right]:
    box('Fridge surround | full height oak side',(x,-.31,top/2),(panel,.62,top),oak,root)
for z in [2.045,top-.009]:
    box('Fridge surround | upper cabinet shelf',(w/2,-.31,z),(outer,.62,.018),oak,root)
box('Fridge surround | cabinet back',(w/2,-.009,2.235),(outer,.018,.37),oak,root)
for i in range(2):
    dw=(w+2*gap-.006)/2
    x=-gap+.0015+dw/2+i*(dw+.003)
    box('Fridge surround | upper oak door',(x,-.624,2.239),(dw,.022,.378),oak,root)
    box('Fridge surround | upper cabinet pull',(x,-.647,2.1),(.13,.018,.012),metal,root)
root['design_notes']='Oak side panels and two storage doors above refrigerator; full height to 2438 mm. Concept ventilation gaps, verify with final appliance specification.'
s['kitchen_revision_notes']='Removed scale people; kitchen to dining opening widened from 1065 to 1400 mm with rounded arch and no door; oak refrigerator enclosure and overhead cabinets.'

cam=bpy.data.objects.get('Current | Kitchen arch and fridge')
if not cam:
    data=bpy.data.cameras.new('Kitchen arch and fridge camera');data.type='ORTHO'
    cam=bpy.data.objects.new('Current | Kitchen arch and fridge',data);col.objects.link(cam)
cam.location=(-4.2,11.8,6.7)
cam.rotation_euler=(Vector((.1,6.8,1.05))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=5.9
s.camera=cam
s.render.resolution_x=1500;s.render.resolution_y=1500;s.render.resolution_percentage=100
s.render.filepath=str(base/'13-kitchen-arch-and-fridge.png')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.overlay.show_overlays=False
        area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Saved: people removed, 1400 mm rounded dining arch, refrigerator oak enclosure with upper cabinets.')
