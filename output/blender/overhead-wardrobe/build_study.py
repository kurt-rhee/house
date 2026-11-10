import bpy, math, json, os
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender/overhead-wardrobe'
doc=json.load(open(OUT+'/drawing-snapshot.json'))
s=bpy.data.scenes.new('Main Bedroom | Overhead Wardrobe Trial')
bpy.context.window.scene=s
s['design_status']='Concept: 8ft ceiling, 6in floor mattress, wardrobe underside 1.30m; actual mounting height, structural support and rail travel unverified. Existing window overlaps cabinet.'
s['source_revision']=doc['revision']
col=bpy.data.collections.new('Overhead wardrobe study');s.collection.children.link(col)
def mat(name,c,rough=.5,metal=0):
 m=bpy.data.materials.new('Study | '+name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
plaster=mat('Warm plaster',(.79,.76,.69),.85);oak=mat('Pale oak',(.54,.36,.20),.5);wood=mat('Light oak floor',(.38,.27,.17),.65);linen=mat('Ivory linen',(.79,.76,.65),.95);white=mat('Mattress ticking',(.91,.88,.78),.9);metal=mat('Rail satin chrome',(.48,.52,.56),.26,.85);dark=mat('Mechanism',(.07,.08,.075),.4);trim=mat('Window trim',(.85,.83,.76));glass=mat('Glazing',(.56,.75,.79),.2)
p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.75;p.inputs['IOR'].default_value=1.45
cloth=[mat('Shirt '+str(i),c,.95) for i,c in enumerate([(.61,.69,.72),(.83,.83,.76),(.43,.54,.59),(.72,.71,.65),(.36,.42,.46)])]
# Oak grain, kept subtle rather than patterned cabinetry.
for m in [oak,wood]:
 n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4;tex.inputs['Detail'].default_value=2
 tc=n.new('ShaderNodeTexCoord');mp=n.new('ShaderNodeMapping');mp.inputs['Scale'].default_value=(4,4,.15);l.new(tc.outputs['Generated'],mp.inputs['Vector']);l.new(mp.outputs['Vector'],tex.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.008;l.new(tex.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],p.inputs['Normal'])
def cube(name,loc,dims,ma,bev=.008):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.data.materials.append(ma)
 if bev:
  b=o.modifiers.new('Rounded edges','BEVEL');b.width=bev;b.segments=4;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def rod(name,a,b,r,ma):
 a,b=Vector(a),Vector(b);v=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=r,depth=v.length,location=(a+b)/2);o=bpy.context.object;o.name=name;o.rotation_euler=v.to_track_quat('Z','Y').to_euler()
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.data.materials.append(ma)
 for p in o.data.polygons:p.use_smooth=True
 return o
def xyz(x,y,z):return ((x-16187.65)/1000,(13136.85-y)/1000,z)
W,D,H=3.09025,3.35325,2.4384
cube('Bedroom floor',(W/2,D/2,-.05),(W,D,.1),wood)
# Reconstruct the four walls and their actual openings from the saved drawing.
for wid in ['231ea206-9a1c-442f-9ff1-b29882656d79','95a31876-8718-4029-aee7-31665058e3d2','33407ad6-ccf9-441a-850c-218fe8112e4c','bd749d8f-0193-4fc9-a63a-567e6da048d9']:
 w=doc['walls'][wid];a,b=w['start'],w['end'];dx,dy=b['x']-a['x'],b['y']-a['y'];L=math.hypot(dx,dy);ux,uy=dx/L,dy/L
 # Only the main bedroom portion of shared long horizontal walls.
 lo,hi=(0,L)
 if abs(dy)<.01:lo=16108.75-a['x'];hi=19330.5-a['x']
 def part(l,r,z1,z2,ma=plaster,label='wall'):
  if r-l<.1 or z2-z1<.001:return
  mid=(l+r)/2;o=cube(w['name']+' | '+label,xyz(a['x']+ux*mid,a['y']+uy*mid,(z1+z2)/2),((r-l)/1000,w['thickness']/1000,z2-z1),ma,.002);o.rotation_euler.z=-math.atan2(dy,dx);o['source_wall_id']=wid;return o
 ops=[]
 for category in ['windows','doors']:
  for op in doc[category].values():
   if op['wall']!=wid:continue
   l,r=op['position']-op['width']/2,op['position']+op['width']/2
   if l<lo or r>hi:continue
   ops.append((l,r,category,op))
 cursor=lo
 for l,r,category,op in sorted(ops):
  z1,z2=(1.0,2.1) if category=='windows' else (0,2.032)
  part(cursor,l,0,H);part(l,r,0,z1);part(l,r,z2,H);cursor=r
  for station in [l,r]:part(station-15,station+15,z1,z2,trim,'opening jamb')
  for z in ([z1,z2] if category=='windows' else [z2]):part(l,r,z-.015,z+.015,trim,'opening trim')
  if category=='windows' or op.get('kind')=='SlidingGlass':
   o=part(l,r,z1,z2,glass,'glazing');o.dimensions.y=.012
   part((l+r)/2-12,(l+r)/2+12,z1,z2,trim,'mullion')
 part(cursor,hi,0,H)
# Floor mattress footprint from semantic bed, with pillows at bottom-wall headboard.
bed=doc['fixtures']['1b621dde-f0da-44d7-90a1-3a31bb2ed549'];left=.579925;right=2.510325;cx=(left+right)/2
cube('6 inch floor mattress | king 76 x 80',(cx,1.016,.0762),(1.9304,2.032,.1524),white,.055)
cube('Soft duvet',(cx,1.23,.18),(1.91,1.56,.095),linen,.045)
cube('Folded linen edge',(cx,.535,.218),(1.91,.16,.045),linen,.018)
for x in [cx-.46,cx+.46]:cube('Floor bed pillow',(x,.24,.225),(.78,.42,.145),white,.065)
# A shallow padded head panel below the overhead assembly.
cube('Low headboard',(cx,.025,.45),(1.93,.05,.56),linen,.025)
# Open-front hanging compartments: actual plan footprint, provisional vertical arrangement.
base,top,dep=1.30,2.38,.6096
for x in [left,cx,right]:cube('Wardrobe vertical support',(x,.3048,(base+top)/2),(.025,dep,top-base),oak)
cube('Wardrobe top',(cx,.3048,top),(1.9554,dep,.025),oak)
cube('Wardrobe lower shelf',(cx,.3048,base),(1.9554,dep,.025),oak)
cube('Wardrobe back | window conflict',(cx,.014,(base+top)/2),(1.93,.025,top-base),oak)
# Clothing mesh with shoulders, sleeves, neckline, hem and light fabric bevels.
def shirt(name,x,y,z,ma,index):
 # Garments hang perpendicular to the rail and slightly fanned for legibility.
 poly=[(-.075,-.04),(-.15,-.07),(-.285,-.23),(-.225,-.29),(-.18,-.20),(-.18,-.76),(.18,-.76),(.18,-.20),(.225,-.29),(.285,-.23),(.15,-.07),(.075,-.04),(.045,-.105),(-.045,-.105)]
 verts=[(0,u,v) for u,v in poly];me=bpy.data.meshes.new(name);me.from_pydata(verts,[],[tuple(range(len(verts)))]);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o);o.location=(x,y,z);o.rotation_euler.z=math.radians(-12+index*3);o.data.materials.append(ma)
 so=o.modifiers.new('Fabric thickness','SOLIDIFY');so.thickness=.012;be=o.modifiers.new('Soft seams','BEVEL');be.width=.008;be.segments=3
 for p in me.polygons:p.use_smooth=True
 rod('Clothes hanger',(x,y-.18,z-.08),(x,y,z),.006,metal);rod('Clothes hanger',(x,y,z),(x,y+.18,z-.08),.006,metal)
 rod('Hanger hook',(x,y,z),(x,y,z+.04),.005,metal)
 # Front placket visible on the end garments.
 rod('Shirt placket',(x+.009,y,z-.13),(x+.009,y,z-.70),.003,ma)
pose_objects=[]
def rail(bay,lowered=False):
 lo=left+bay*(right-left)/2+.065;hi=left+(bay+1)*(right-left)/2-.065
 y,z=(.89,1.50) if lowered else (.32,2.20)
 start=set(col.objects)
 for x in [lo,hi]:
  cube('Rail pivot',(x,.16,1.50),(.045,.075,.10),dark)
  rod('Pull-down pivot arm',(x,.16,1.50),(x,y,z),.014,metal)
 rod('Hanging rail',(lo,y,z),(hi,y,z),.014,metal)
 mid=(lo+hi)/2;rod('Pull-down handle',(mid,y,z),(mid,y+.035,z-.48),.01,metal);rod('Grip',(mid-.08,y+.035,z-.48),(mid+.08,y+.035,z-.48),.014,dark)
 for i in range(5):shirt('Hanging shirt '+str(bay)+' '+str(i),lo+.06+i*(hi-lo-.12)/4,y,z-.025,cloth[i],i)
 return list(set(col.objects)-start)
rail(1,False);raised=rail(0,False)
# Soft daylight and warm ceiling bounce.
s.world=bpy.data.worlds.new('Study daylight');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.75,.81,.87,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.35
for name,loc,power,size,target in [('Ceiling fill',(1.55,1.65,2.35),150,2.4,(1.55,.4,.6)),('Sliding door daylight',(-.08,1.55,1.9),230,1.7,(1.7,.4,1.2)),('Camera fill',(2.6,3.0,2.0),75,1.4,(1.5,.4,1.4))]:
 l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='DISK';l.size=size;o=bpy.data.objects.new(name,l);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Main bed from foot');cam=bpy.data.objects.new(camdata.name,camdata);col.objects.link(cam);cam.location=(2.85,3.16,1.65);target=Vector((1.52,.30,1.25));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=23;camdata.clip_start=.05;s.camera=cam
s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=1200;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
s.render.image_settings.file_format='PNG';s.render.filepath=OUT+'/01-rails-raised.png'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/main-bedroom-overhead-trial.blend')
bpy.ops.render.render(write_still=True)
for o in raised:bpy.data.objects.remove(o,do_unlink=True)
rail(0,True);s.name='Main Bedroom | One Rail Lowered';s.render.filepath=OUT+'/02-one-rail-lowered.png'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/main-bedroom-overhead-trial.blend')
bpy.ops.render.render(write_still=True)
# Leave the new study camera visible in the already open application.
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
print('Rendered raised and lowered wardrobe studies:',OUT)
