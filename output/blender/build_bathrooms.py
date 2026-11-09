import bpy, math, json, os
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender'
doc=json.load(open(OUT+'/drawing-snapshot.json'))
scene=bpy.data.scenes.new('Two Bathrooms | Architectural Study')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
scene['source_revision']=doc['revision']
scene['design_notes']='Plan footprints preserved. Assumed ceiling 2438 mm, doors 2032 mm, window sill 1450 mm. Concept finishes and fixture geometry.'
COL=bpy.data.collections.new('Bathrooms from drawing');scene.collection.children.link(COL)
def link(o):
 for c in list(o.users_collection):c.objects.unlink(o)
 COL.objects.link(o)
 return o
def mat(name,col,rough=.5,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 return m
plaster=mat('Warm white plaster',(.78,.76,.70),.8)
ceramic=mat('Gloss white porcelain',(.91,.93,.92),.19)
stone=mat('Ivory quartz',(.76,.74,.66),.32)
grout=mat('Warm gray grout',(.35,.36,.33),.9)
tile=mat('Limestone porcelain',(.56,.57,.52),.65)
chrome=mat('Brushed chrome',(.57,.64,.66),.23,.94)
black=mat('Drain recess',(.045,.05,.05),.5)
wood=mat('Natural oak',(.42,.25,.12),.45)
nodes=wood.node_tree.nodes;links=wood.node_tree.links;p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
tex=nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4;tex.inputs['Detail'].default_value=3
coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(5,5,.35)
links.new(coord.outputs['Generated'],mapping.inputs[0]);links.new(mapping.outputs[0],tex.inputs['Vector'])
ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.22,.105,.035,1);ramp.color_ramp.elements[1].color=(.62,.41,.20,1);links.new(tex.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],p.inputs['Base Color'])
mirror=mat('Silver mirror',(.83,.86,.86),.045,1)
glass=mat('Window frosted glazing',(.66,.81,.84),.25)
p=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Transmission Weight'].default_value=.3

def cube(name,loc,dim,ma,parent=None,bevel=.008):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=link(bpy.context.object);o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if parent:o.parent=parent
 if ma:o.data.materials.append(ma)
 if bevel:
  b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=bevel;b.segments=3
  o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
 return o

def cyl(name,a,b,r,ma,parent=None):
 a,b=Vector(a),Vector(b);d=b-a
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=d.length,location=(a+b)/2);o=link(bpy.context.object);o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
 if parent:o.parent=parent
 o.data.materials.append(ma)
 for f in o.data.polygons:f.use_smooth=True
 return o

def bowl(name,cx,cy,profiles,ma,parent=None,power=2):
 # Continuous outer shell, lip and inner basin, specified bottom to rim to basin floor.
 verts=[];N=64
 for rx,ry,z in profiles:
  for i in range(N):
   t=2*math.pi*i/N;co,si=math.cos(t),math.sin(t)
   verts.append((cx+rx*math.copysign(abs(co)**(2/power),co),cy+ry*math.copysign(abs(si)**(2/power),si),z))
 faces=[]
 for j in range(len(profiles)-1):
  for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
 faces.append(tuple(reversed(range(N))));faces.append(tuple((len(profiles)-1)*N+i for i in range(N)))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);COL.objects.link(o)
 if parent:o.parent=parent
 me.materials.append(ma)
 for f in me.polygons:f.use_smooth=True
 return o
# Architectural origin: west / north inside faces. x right, Blender Y points north.
X0,Y0=19383.1,10783.0
H=2.4384
walls=[]
def world(x,y,z):return ((x-X0)/1000,-(y-Y0)/1000,z)
for i,(l,r) in enumerate([(19383.1,20974.25),(21079.45,22670.6)],1):
 w=(r-l)/1000;xx=(l-X0)/1000;depth=(13136.85-Y0)/1000
 cube(f'Bathroom {i} floor slab',(xx+w/2,-depth/2,-.06),(w,depth,.12),grout)
 # 300 x 600 mm floor tiles, clipped at perimeter
 for a in range(math.ceil(w/.3)):
  for b in range(math.ceil(depth/.6)):
   xa,xb=a*.3,min((a+1)*.3,w);ya,yb=b*.6,min((b+1)*.6,depth)
   cube(f'B{i} floor tile {a}-{b}',(xx+(xa+xb)/2,-(ya+yb)/2,.007),(xb-xa-.003,yb-ya-.003,.014),tile,bevel=.001)
# Wall solids split around all plan openings intersecting bathroom rectangle.
wallids=['10170a0b-df5f-47d1-9080-143f6e0c5578','33407ad6-ccf9-441a-850c-218fe8112e4c','8071d128-b525-406b-b839-87b24230ca1c','95a31876-8718-4029-aee7-31665058e3d2','db42f8d2-7bac-4e61-ab4a-89b5a9209859']
for wid in wallids:
 w=doc['walls'][wid];s,e=w['start'],w['end'];horizontal=abs(e['y']-s['y'])<1
 lo=max(s['x'],19330.5) if horizontal else max(s['y'],10730.4)
 hi=min(e['x'],22723.2) if horizontal else min(e['y'],13215.75)
 ops=[]
 for kind in ['doors','windows']:
  for op in doc[kind].values():
   if op['wall']!=wid:continue
   center=(s['x'] if horizontal else s['y'])+op['position'];a=center-op['width']/2;b=center+op['width']/2
   if a>=lo and b<=hi:ops.append((a,b,0 if kind=='doors' else 1.45,2.032 if kind=='doors' else 2.05,kind))
 def block(a,b,z1,z2,label):
  if b-a<.1 or z2-z1<.001:return
  loc=world((a+b)/2 if horizontal else s['x'],s['y'] if horizontal else (a+b)/2,(z1+z2)/2)
  o=cube(w['name']+' '+label,loc,((b-a)/1000,w['thickness']/1000,z2-z1) if horizontal else (w['thickness']/1000,(b-a)/1000,z2-z1),plaster,bevel=.002);o['source_wall_id']=wid;walls.append(o)
 cursor=lo
 for a,b,z1,z2,kind in sorted(ops):
  block(cursor,a,0,H,'pier');block(a,b,0,z1,'sill');block(a,b,z2,H,'header');cursor=b
  if kind=='windows':
   loc=world((a+b)/2,s['y'],(z1+z2)/2)
   cube('Frosted window',loc,((b-a)/1000,.022,z2-z1),glass)
   for z in [z1,z2]:cube('Window frame',world((a+b)/2,s['y'],z),((b-a)/1000+.04,.07,.035),ceramic)
   for x in [a,b]:cube('Window jamb',world(x,s['y'],(z1+z2)/2),(.035,.07,z2-z1),ceramic)
  else:
   # Open doorway: timber jambs, header. Door leaves are omitted for visibility.
   for a1 in [a,b]:
    loc=world(a1 if horizontal else s['x'],s['y'] if horizontal else a1,1.016)
    cube('Oak door jamb',loc,(.025,.13,2.032) if horizontal else (.13,.025,2.032),wood)
 block(cursor,hi,0,H,'pier')
# Fixtures follow exact source origin and clockwise rotation.
for f in doc['fixtures'].values():
 if f['origin']['y']<10000:continue
 w,d=f['width']/1000,f['depth']/1000
 root=bpy.data.objects.new(f['kind']+' | '+f['id'][:8],None);COL.objects.link(root);root.location=world(f['origin']['x'],f['origin']['y'],0);root.rotation_euler.z=-math.radians(f['rotation']);root['source_fixture_id']=f['id'];root['plan_footprint_mm']=[f['width'],f['depth']]
 def box(name,u,v,z,dx,dy,dz,ma,bev=.008):return cube(name,(u,-v,z),(dx,dy,dz),ma,root,bev)
 def pipe(name,a,b,r=.012,ma=chrome):return cyl(name,(a[0],-a[1],a[2]),(b[0],-b[1],b[2]),r,ma,root)
 if f['kind']=='Sink':
  box('Floating oak vanity',w/2,d/2,.48,w-.02,d-.02,.60,wood)
  box('Drawer reveal',w/2,d-.007,.48,w-.05,.006,.008,black,.001)
  for z in [.34,.64]:box('Chrome drawer pull',w/2,d+.004,z,.22,.018,.012,chrome,.005)
  # Top slabs around inset basin
  for u,dx in [(.045,.09),(w-.045,.09)]:box('Quartz counter edge',u,d/2,.80,dx,d,.035,stone)
  for v,dy in [(.04,.08),(d-.045,.09)]:box('Quartz counter edge',w/2,v,.80,w-.18,dy,.035,stone)
  bowl('Inset washbasin',w/2,-d/2,[(.205,.14,.80),(.19,.125,.80),(.15,.09,.68),(.02,.02,.67)],ceramic,root,power=3)
  pipe('Basin drain',(w/2,d/2,.67),(w/2,d/2,.675),.018)
  pipe('Mixer upright',(w/2,.065,.82),(w/2,.065,1.0),.018)
  pipe('Mixer spout',(w/2,.065,1.0),(w/2,.17,1.0),.014)
  box('Oak mirror frame',w/2,.016,1.48,w,.045,.90,wood)
  box('Vanity mirror',w/2,.042,1.48,w-.035,.008,.865,mirror,.001)
  box('Vanity light bar',w/2,.10,2.02,w-.08,.06,.035,ceramic)
 elif f['kind']=='Toilet':
  bowl('Porcelain pedestal',w/2,-d*.57,[(.11,.18,.025),(.10,.16,.22),(.17,.24,.36),(.15,.21,.38),(.09,.15,.22)],ceramic,root)
  bowl('Oval toilet seat',w/2,-d*.61,[(w*.49,d*.35,.395),(w*.49,d*.35,.423),(w*.36,d*.26,.423),(w*.36,d*.26,.397)],ceramic,root)
  box('Toilet tank',w/2,.095,.55,w,.19,.38,ceramic,.04)
  box('Tank lid',w/2,.095,.75,w+.009,.20,.035,ceramic,.02)
  pipe('Flush button',(w/2,.095,.77),(w/2,.095,.775),.019)
 elif f['kind']=='Bath':
  bowl('1524 x 762 bathtub',w/2,-d/2,[(w/2-.01,d/2-.01,.015),(w/2,d/2,.51),(w/2-.065,d/2-.065,.525),(w/2-.08,d/2-.08,.49),(w/2-.16,d/2-.16,.13),(.03,.03,.12)],ceramic,root,power=5)
  pipe('Tub drain',(w-.25,d/2,.122),(w-.25,d/2,.128),.024)
  # Shared wet wall at the right end in each rotated tub's local frame.
  pipe('Shower riser',(w+.015,d*.52,.85),(w+.015,d*.52,2.10),.011)
  pipe('Shower arm',(w+.015,d*.52,2.10),(w-.21,d*.52,2.10))
  pipe('Rain shower head',(w-.21,d*.52,2.075),(w-.21,d*.52,2.10),.085)
  pipe('Mixer',(w-.015,d*.52,1.02),(w-.055,d*.52,1.02),.05)
  pipe('Tub filler',(w-.015,d*.52,.65),(w-.16,d*.52,.65),.021)
  # Pale tiled wet surround with visible horizontal joints, below window and side wall.
  for j in range(7):
   z=.60+j*.245
   box('Wet-wall porcelain tile',w+.028,d/2,z,.018,d-.008,.242,stone,.001)
# Lighting and camera rigs
worlddata=bpy.data.worlds.new('Soft studio daylight');scene.world=worlddata;worlddata.use_nodes=True
bg=next(n for n in worlddata.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.67,.74,.80,1);bg.inputs[1].default_value=.35

def area(name,loc,target,power,size,color):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
 o=bpy.data.objects.new(name,data);COL.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for x in [.7956,2.492]:
 area('Ceiling softbox',(x,-1.15,2.32),(x,-1.2,0),110,1.1,(1,.88,.73))
 area('Window daylight',(x,-2.25,1.85),(x,-.8,.7),55,.55,(.78,.88,1))
area('Open roof daylight',(1.64,-.5,5),(1.64,-1.4,0),350,4,(1,.94,.84))
def cam(name,loc,target,lens=24,ortho=None):
 data=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,data);COL.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;data.clip_start=.04
 if ortho:data.type='ORTHO';data.ortho_scale=ortho
 return o
cam('01 | Both bathrooms', (4.8,3.9,7.6),(1.64,-1.18,.55),ortho=5.9)
cam('02 | Bathroom 1',(.22,-.17,1.70),(1.05,-1.75,1.0),lens=18)
cam('03 | Bathroom 2',(3.04,-.16,1.70),(2.28,-1.75,1.0),lens=18)
scene.camera=bpy.data.objects['01 | Both bathrooms']
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.render.filepath=OUT+'/01-both-bathrooms.png'
# Favor the model when the saved file opens.
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':
  a.spaces.active.region_3d.view_distance=6;a.spaces.active.region_3d.view_location=(1.65,-1.18,1)
  a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/two-bathrooms.blend')
print('Built',len(COL.objects),'objects. Saved',bpy.data.filepath)
