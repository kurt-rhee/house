import bpy, math, json, os
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender/full-house'
os.makedirs(OUT,exist_ok=True)
doc=json.load(open(OUT+'/drawing-snapshot.json'))
# Full-copy the bathroom scene so the previous editable study remains available.
bpy.ops.scene.new(type='FULL_COPY');scene=bpy.context.scene;scene.name='Full House | Drawing Revision '+str(doc['revision'])
scene.timeline_markers.clear();scene.frame_start=1;scene.frame_end=1
for o in list(scene.objects):
 o.animation_data_clear()
 if o.get('source_wall_id') or o.name.startswith(('Frosted window','Window frame','Window jamb','Oak door jamb','Bathroom 1 ceiling','Bathroom 2 ceiling')) or o.type=='CAMERA':
  bpy.data.objects.remove(o,do_unlink=True)
 else:o.hide_render=False;o.hide_set(False)
col=bpy.data.collections.new('Full house architecture');scene.collection.children.link(col)
def mat(name,c,rough=.6,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
plaster=bpy.data.materials['Warm white plaster'];oak=bpy.data.materials['Natural oak'];chrome=bpy.data.materials['Brushed chrome'];white=bpy.data.materials['Gloss white porcelain'];quartz=bpy.data.materials['Ivory quartz'];glass=bpy.data.materials['Window frosted glazing']
concrete=mat('Garage concrete',(.34,.36,.35),.9);floor=mat('Pale oak flooring',(.55,.39,.24),.65);dark=mat('Appliance glass',(.025,.035,.04),.25);metal=mat('Stainless appliances',(.42,.47,.49),.32,.85);sill=mat('Window and door trim',(.86,.85,.79),.5);ground=mat('Neutral site base',(.25,.29,.27),.95);porch=mat('Porch concrete',(.47,.45,.39),.85);label=mat('Room label graphite',(.08,.10,.09),.8)
X0,Y0=19383.1,10783
H=2.4384
def xyz(x,y,z=0):return ((x-X0)/1000,-(y-Y0)/1000,z)
def cube(name,loc,dim,ma,parent=None,bev=.004):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o)
 if parent:o.parent=parent
 if ma:o.data.materials.append(ma)
 if bev:
  b=o.modifiers.new('Edge highlights','BEVEL');b.width=bev;b.segments=2;o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
 return o
def slab(name,poly,ma,z=-.012):
 verts=[xyz(x,y,z) for x,y in poly];me=bpy.data.meshes.new(name);me.from_pydata(verts,[],[tuple(reversed(range(len(verts))))]);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o);me.materials.append(ma);sol=o.modifiers.new('Floor slab thickness','SOLIDIFY');sol.thickness=.13;return o
def rect(name,x1,y1,x2,y2,ma,z=-.01):return slab(name,[(x1,y1),(x2,y1),(x2,y2),(x1,y2)],ma,z)
main=[(17279.1,2209.2),(24103.95,2209.2),(24103.95,8416),(26129.05,8416),(26129.05,13215.75),(16108.75,13215.75),(16108.75,9717.85),(16713.65,9717.85),(16713.65,6430.35),(15122.5,6430.35),(15122.5,3905.55),(17279.1,3905.55)]
wing=[(3918.7,670.65),(9691.55,670.65),(9691.55,8836.8),(3918.7,8836.8),(3918.7,6101.6),(907.35,6101.6),(907.35,1354.45),(3918.7,1354.45)]
slab('Main house floor',main,floor);slab('Garage and ADU wing floor',wing,floor)
rect('Large garage concrete',3971.3,749.55,9612.65,5838.6,concrete,-.006)
rect('Office floor',986.25,1433.35,3866.1,6022.7,floor,-.006)
rect('Guest bath tile',3997.6,5943.8,6127.9,7127.3,quartz,-.005)
rect('Utility floor',3997.6,7232.5,6127.9,8757.9,concrete,-.005)
rect('Laundry floor',15201.4,3984.45,17200.2,6351.45,quartz,-.005)
rect('Porch slab',24103.95,4707.7,25511,8337.1,porch,-.06)
rect('Laundry landing',13807.5,4970.7,15122.5,6496.1,porch,-.06)
# Site only: no invented building connection across the open gap.
rect('Site ground',-200,0,27500,14500,ground,-.28)
# A fine staggered plank pattern across the wood floor.
m=floor;n=m.node_tree.nodes;l=m.node_tree.links;p=next(n for n in n if n.type=='BSDF_PRINCIPLED');tex=n.new('ShaderNodeTexBrick');tex.inputs['Scale'].default_value=1;tex.inputs['Color1'].default_value=(.57,.43,.29,1);tex.inputs['Color2'].default_value=(.45,.31,.19,1);tex.inputs['Mortar'].default_value=(.24,.19,.13,1);tex.inputs['Mortar Size'].default_value=.002;tex.inputs['Brick Width'].default_value=1.5;tex.inputs['Row Height'].default_value=.18
coord=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeMapping');mapping.inputs['Rotation'].default_value[2]=math.pi/2;l.new(coord.outputs['Object'],mapping.inputs['Vector']);l.new(mapping.outputs['Vector'],tex.inputs['Vector']);l.new(tex.outputs['Color'],p.inputs['Base Color'])
# All actual wall centerlines, with doors and windows cut from their hosts.
for wid,w in doc['walls'].items():
 if w['thickness']<40:continue
 a,b=w['start'],w['end'];dx,dy=b['x']-a['x'],b['y']-a['y'];L=math.hypot(dx,dy);ux,uy=dx/L,dy/L;t=w['thickness']/1000
 def part(start,end,z1,z2,ma=plaster,name='wall'):
  if end-start<.1 or z2-z1<.001:return
  mid=(start+end)/2;o=cube(w['name']+' | '+name,xyz(a['x']+ux*mid,a['y']+uy*mid,(z1+z2)/2),((end-start)/1000,t,z2-z1),ma,bev=.002);o.rotation_euler.z=-math.atan2(dy,dx);o['source_wall_id']=wid;return o
 openings=[]
 for category in ['doors','windows']:
  for op in doc[category].values():
   if op['wall']!=wid:continue
   lo,hi=op['position']-op['width']/2,op['position']+op['width']/2
   z1,z2=(1.0,2.10) if category=='windows' else (0,2.032)
   if category=='windows' and w['name']=='Main bedroom south' and 19383<a['x']+ux*op['position']<22671:z1,z2=1.45,2.05
   openings.append((lo,hi,z1,z2,category,op))
 cursor=0
 for lo,hi,z1,z2,category,op in sorted(openings):
  part(cursor,lo,0,H);part(lo,hi,0,z1);part(lo,hi,z2,H);cursor=hi
  # Trim and glazing, all sized from semantic openings.
  for station in [lo,hi]:
   o=cube(w['name']+' opening jamb',xyz(a['x']+ux*station,a['y']+uy*station,(z1+z2)/2),(.035,t+.045,z2-z1+.035),sill);o.rotation_euler.z=-math.atan2(dy,dx)
  for z in ([z1,z2] if category=='windows' else [z2]):part(lo-18,hi+18,z-.018,z+.018,sill,'opening trim')
  if category=='windows' or op.get('kind')=='SlidingGlass':
   o=part(lo,hi,z1,z2,glass,'glazing');o.dimensions.y=.018
   part((lo+hi)/2-12,(lo+hi)/2+12,z1,z2,sill,'mullion')
  elif op.get('kind')=='Garage':
   o=part(lo,hi,.02,1.98,concrete,'garage door');o.dimensions.y=.045
   for z in [.4,.8,1.2,1.6]:part(lo,hi,z,z+.012,metal,'garage panel seam')
  # Hinged and pocket door openings remain open in the cutaway.
 part(cursor,L,0,H)
# Low steps / porch outline marks from drawing, never extruded into full walls.
for w in doc['walls'].values():
 if w['thickness']>=40:continue
 a,b=w['start'],w['end'];dx,dy=b['x']-a['x'],b['y']-a['y'];L=math.hypot(dx,dy)
 o=cube(w['name'],xyz((a['x']+b['x'])/2,(a['y']+b['y'])/2,-.04),(L/1000,.035,.08),porch);o.rotation_euler.z=-math.atan2(dy,dx)
# Kitchen assemblies use the plan's footprint and local back orientation.
for f in doc['fixtures'].values():
 if f['origin']['y']>10000:continue
 root=bpy.data.objects.new('Kitchen '+f['kind']+' | '+f['id'][:8],None);col.objects.link(root);root.location=xyz(f['origin']['x'],f['origin']['y']);root.rotation_euler.z=-math.radians(f['rotation']);root['source_fixture_id']=f['id'];w,d=f['width']/1000,f['depth']/1000
 def box(name,u,v,z,dx,dy,dz,ma,bev=.005):return cube(name,(u,-v,z),(dx,dy,dz),ma,root,bev)
 if f['kind']=='Countertop':
  box('Oak base cabinets',w/2,d/2,.455,w,d-.025,.87,oak)
  box('Quartz countertop',w/2,d/2,.915,w+.005,d+.01,.035,quartz)
  # Cabinet-front divisions along the exposed long edge.
  if w>d:
   for i in range(1,math.ceil(w/.6)):box('Cabinet seam',w*i/math.ceil(w/.6),d-.009,.47,.004,.004,.77,dark,.001)
  else:
   for i in range(1,math.ceil(d/.6)):box('Cabinet seam',w-.009,d*i/math.ceil(d/.6),.47,.004,.004,.77,dark,.001)
 elif f['kind']=='Refrigerator':
  box('Refrigerator',w/2,d/2,1.0,w,d,2.0,metal,.025)
  box('Refrigerator door seam',w/2,d+.006,1.15,.006,.009,1.55,dark,.001)
  for u in [w/2-.05,w/2+.05]:box('Fridge handles',u,d+.045,1.21,.018,.045,.5,chrome)
  box('Freezer seam',w/2,d+.008,.45,w-.025,.009,.006,dark,.001)
 elif f['kind']=='ApplianceGarage':
  box('Appliance pantry',w/2,d/2,1.13,w,d,2.26,oak)
  box('Appliance garage shutter',w/2,d+.005,1.32,w-.055,.012,.65,metal)
 elif f['kind']=='Stove':
  box('Range',w/2,d/2,.455,w-.01,d-.01,.88,metal)
  box('Black cooktop',w/2,d/2,.936,w-.015,d-.015,.022,dark)
  for u in [w*.26,w*.74]:
   for v in [d*.28,d*.72]:
    bpy.ops.mesh.primitive_torus_add(major_radius=.072,minor_radius=.006,major_segments=32,minor_segments=8,location=(u,-v,.954));o=bpy.context.object;o.parent=root;o.data.materials.append(chrome)
  box('Oven glass',w/2,d+.007,.46,w-.11,.02,.45,dark)
  box('Oven handle',w/2,d+.04,.75,w-.14,.035,.025,chrome)
  box('Range hood',w/2,.22,1.87,w,.44,.13,metal)
 elif f['kind']=='Sink':
  # Cut through the north countertop using a rounded sink cavity.
  cx,cy=f['origin']['x']+f['width']/2,f['origin']['y']+f['depth']/2
  bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(cx,cy,.88));cutter=bpy.context.object;cutter.dimensions=(w-.11,d-.13,.24);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  for o in list(col.objects):
   if o.name.startswith('Quartz countertop'):
    p=o.matrix_world.translation
    if abs(p.x-cutter.location.x)<2 and abs(p.y-cutter.location.y)<.5:
     mod=o.modifiers.new('Sink cutout','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
  bpy.data.objects.remove(cutter,do_unlink=True)
  box('Stainless sink bottom',w/2,d/2,.80,w-.11,d-.13,.025,metal)
  for u in [.05,w-.05]:box('Sink side',u,d/2,.86,.025,d-.10,.13,metal)
  for v in [.055,d-.055]:box('Sink side',w/2,v,.86,w-.10,.025,.13,metal)
  box('Kitchen tap',w/2,.035,1.06,.025,.025,.28,chrome)
  box('Kitchen spout',w/2,.105,1.20,.025,.16,.025,chrome)
# Floor labels make the drawing's room assignments legible in the overhead view.
for r in doc['room_labels'].values():
 if r['name'] in ['Tub/shower','Fridge']:continue
 cu=bpy.data.curves.new(r['name'],'FONT');cu.body=r['name'];cu.align_x='CENTER';cu.align_y='CENTER';cu.size=.25 if 'Bathroom' in r['name'] else .32;cu.extrude=0
 o=bpy.data.objects.new('Label | '+r['name'],cu);col.objects.link(o);o.location=xyz(r['position']['x'],r['position']['y'],.033);cu.materials.append(label)
# Bright open-roof architectural lighting.
scene.world=bpy.data.worlds.new('Full house daylight');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.72,.79,.85,1);bg.inputs[1].default_value=.65
ld=bpy.data.lights.new('Architectural sun','SUN');ld.energy=2;ld.angle=.18;o=bpy.data.objects.new('Architectural sun',ld);col.objects.link(o);o.rotation_euler=(.42,-.30,-.6)
ld=bpy.data.lights.new('Broad daylight fill','AREA');ld.energy=1800;ld.shape='DISK';ld.size=16;o=bpy.data.objects.new('Broad daylight fill',ld);col.objects.link(o);o.location=xyz(17000,5000,12)
def cam(name,loc,target,scale):
 d=bpy.data.cameras.new(name);d.type='ORTHO';d.ortho_scale=scale;o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.clip_end=200;return o
cam('House | Whole property',xyz(38000,30000,42000/1000),xyz(13500,6900,.5),33)
cam('House | Main house',xyz(33000,28000,29),xyz(20500,8000,.3),17)
cam('House | Plan',xyz(13500,6900,40),xyz(13500,6900,0),29)
# Store provenance and provisional vertical assumptions.
scene['source_revision']=doc['revision'];scene['model_notes']='Plan wall and opening locations in millimeters. Roof omitted for cutaway. Ceiling 2438mm, door height 2032mm, typical windows 1000-2100mm assumed. Furniture omitted where not drawn. Bath assemblies preserved.'
scene.camera=bpy.data.objects['House | Whole property'];scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.view_settings.exposure=-.65
scene.render.resolution_x=2000;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=OUT+'/01-whole-property.png'
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':
  a.spaces.active.overlay.show_overlays=False;a.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/full-house.blend')
print('Full house built:',len(scene.objects),'objects. Saved',bpy.data.filepath)
bpy.ops.render.render(write_still=True)
print('Whole property preview rendered')
