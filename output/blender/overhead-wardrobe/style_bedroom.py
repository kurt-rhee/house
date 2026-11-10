import bpy,math,os
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender/overhead-wardrobe'
assert bpy.context.scene.name.startswith('Main Bedroom |')
bpy.ops.scene.new(type='FULL_COPY');s=bpy.context.scene;s.name='Main Bedroom | Integrated Headboard Design'
col=bpy.data.collections.new('Integrated headboard finish');s.collection.children.link(col)
def mat(name,c,rough=.65,metal=0):
 m=bpy.data.materials.new('Design | '+name);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
def fabric(name,c):
 m=mat(name,c,.95);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220;noise.inputs['Detail'].default_value=2;b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.20;b.inputs['Distance'].default_value=.002;l.new(noise.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],p.inputs['Normal']);return m
paint=mat('Warm plaster lacquer',(.71,.67,.58),.72);linen=fabric('Oatmeal upholstery',(.48,.40,.30));bedding=fabric('Cream washed linen',(.76,.72,.62));clay=fabric('Muted terracotta',(.36,.18,.11));rug=fabric('Natural woven rug',(.44,.36,.25));bronze=mat('Aged bronze',(.16,.10,.055),.35,.7);oak=bpy.data.materials['Study | Pale oak'];wall=bpy.data.materials.new('Design | Warm limewash');wall.diffuse_color=(.71,.67,.58,1);wall.use_nodes=True;wall.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.71,.67,.58,1);wall.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9
led=mat('Warm LED diffuser',(1,.68,.32));p=led.node_tree.nodes['Principled BSDF'];p.inputs['Emission Color'].default_value=(1,.52,.20,1);p.inputs['Emission Strength'].default_value=3

def cube(name,loc,dims,ma,bev=.008):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.data.materials.append(ma)
 if bev:
  b=o.modifiers.new('Soft millwork edges','BEVEL');b.width=bev;b.segments=4;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
# Conceal the schematic mechanism and replace the original two exposed oak boxes.
for o in list(s.objects):
 if o.name.startswith(('Wardrobe ','Rail pivot','Pull-down pivot arm','Hanging rail','Pull-down handle','Grip','Hanging shirt','Clothes hanger','Hanger hook','Shirt placket','Low headboard')):
  o.hide_render=True;o.hide_set(True)
 if o.type=='MESH':
  if any(m and m.name=='Study | Warm plaster' for m in o.data.materials):
   # Full-copy scene shares materials: replace slots rather than editing originals.
   for i,m in enumerate(o.data.materials):
    if m and m.name=='Study | Warm plaster':o.data.materials[i]=wall
 if o.name.startswith(('Soft duvet','Folded linen edge','Floor bed pillow')):
  o.data.materials.clear();o.data.materials.append(bedding)
 if o.type=='LIGHT':
  if 'Ceiling fill' in o.name:o.data.energy=100
  elif 'Sliding door daylight' in o.name:o.data.energy=160
  elif 'Camera fill' in o.name:o.data.energy=45
# Retain the north-wall cutaway and headboard-window infill in this scene.
W,H=3.09025,2.4384;cx=W/2;bottom=1.30;depth=.6096
cube('Continuous concealed cabinet back',(cx,.015,(bottom+H)/2),(W,.03,H-bottom),paint)
cube('Continuous cabinet top',(cx,depth/2,H-.014),(W,depth,.028),paint)
cube('Continuous cabinet underside',(cx,depth/2,bottom),(W,depth,.025),paint)
for x in [.014,.579925,1.545125,2.510325,W-.014]:cube('Concealed cabinet partition',(x,depth/2,(bottom+H)/2),(.025,depth,H-bottom),paint)
# Two central bypass fronts; matching side fronts carry the composition to the walls.
for i,(a,b) in enumerate([(.006,.579925),(.579925,1.545125),(1.545125,2.510325),(2.510325,W-.006)]):
 y=.628 if i!=2 else .652
 o=cube('Flush wardrobe front '+str(i+1),((a+b)/2,y,(bottom+H)/2),(b-a-.004,.023,H-bottom-.012),paint,.003)
 o['design_intent']='Central panels slide on concealed bypass tracks; hardware and rail travel need verification.'
# Thin oak edge beneath the upper volume.
cube('Fine oak lower reveal',(cx,.626,bottom-.021),(W,.028,.018),oak,.002)
# One upholstered wall composition, lightly divided into three tailored panels.
for a,b in [(.025,.579925),(.579925,2.510325),(2.510325,W-.025)]:
 cube('Oatmeal upholstered headboard',((a+b)/2,.055,.70),(b-a-.008,.09,1.02),linen,.018)
# Small ledges and compact reading lights remain above the side aisles.
for x in [.29,W-.29]:
 cube('Floating bedside ledge',(x,.135,.345),(.30,.23,.035),oak,.008)
 cube('Bronze reading light backplate',(x,.116,.96),(.045,.025,.15),bronze,.008)
 o=cube('Directional reading light',(x,.15,.94),(.035,.08,.065),bronze,.012);o.rotation_euler.x=math.radians(20)
 l=bpy.data.lights.new('Warm reading pool','AREA');l.energy=3;l.color=(1,.69,.40);l.shape='DISK';l.size=.12;o=bpy.data.objects.new(l.name,l);col.objects.link(o);o.location=(x,.19,.92);o.rotation_euler=(Vector((x,.65,.28))-o.location).to_track_quat('-Z','Y').to_euler()
# Recessed diffuser and wall wash; visible source is screened by a front lip.
cube('Concealed LED diffuser',(cx,.47,bottom-.017),(W-.14,.025,.008),led,.002)
cube('LED screening lip',(cx,.565,bottom-.025),(W,.025,.045),paint,.002)
l=bpy.data.lights.new('2700K headboard wash','AREA');l.energy=22;l.color=(1,.65,.34);l.shape='RECTANGLE';l.size=W-.16;l.size_y=.035;o=bpy.data.objects.new(l.name,l);col.objects.link(o);o.location=(cx,.45,1.265);o.rotation_euler=(Vector((cx,.07,.62))-o.location).to_track_quat('-Z','Y').to_euler()
cube('Warm plaster ceiling',(cx,1.67,H+.035),(W,3.36,.07),wall,.002)
# Restrained textiles keep the low bed feeling intentional.
cube('Woven rug',(cx,2.04,.009),(2.50,1.08,.018),rug,.025)
# A draped terracotta throw at the foot, with soft folds.
nx,ny=30,12;verts=[];faces=[]
for j in range(ny+1):
 y=1.58+j/ny*.46
 for i in range(nx+1):
  x=.51+i/nx*2.07
  over=max(.579925-x,x-2.510325,0)
  z=.245-over*1.3+.013*math.sin(i*.72+j*.27)+.006*math.sin(j*1.5)
  verts.append((x,y,z))
for j in range(ny):
 for i in range(nx):
  a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
me=bpy.data.meshes.new('Draped throw');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Muted clay linen throw',me);col.objects.link(o);me.materials.append(clay)
for p in me.polygons:p.use_smooth=True
sol=o.modifiers.new('Linen thickness','SOLIDIFY');sol.thickness=.004;sub=o.modifiers.new('Soft folds','SUBSURF');sub.levels=2
# One small accent cushion, rather than a pile of decorative pillows.
o=cube('Clay accent cushion',(cx,.46,.32),(.56,.26,.15),clay,.065);o.rotation_euler.z=math.radians(-5)
# Closed-front hero view, slightly wider to show the complete headboard treatment.
s.camera.location=(2.78,3.20,1.57);target=Vector((1.48,.23,1.18));s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.lens=22
s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1500;s.render.resolution_y=1300;s.render.resolution_percentage=100;s.view_settings.exposure=-.25;s.render.filepath=OUT+'/03-integrated-headboard.png'
s['design_status']='Styled concept; 8ft ceiling and 6in mattress assumed. Upper storage expanded wall-to-wall. Cabinet door travel, rail mechanism and structural supports remain unverified.'
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=OUT+'/main-bedroom-integrated-design.blend')
bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
print('Styled bedroom rendered and saved:',OUT+'/03-integrated-headboard.png')
