"""Photographed oak, cabinet joinery, concealed shelf supports and photographic lighting."""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');textures=base/'walkthrough/textures'
doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=16
for f in doc['fixtures'].values():
 if f['kind']=='OverheadCabinet' and ('shelf' in f.get('style','') or f['id']=='e1928df0-155f-546e-b491-516387590509'):
  f['style']=f.get('style','floating_shelves').removesuffix('_concealed_supports')+'_concealed_supports';f['material']='Natural white oak, matte clear finish'
(base/'floor-plan.house.json').write_text(json.dumps(doc,indent=2)+'\n')
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def original(o):return o.get('walkthrough_source_name',o.name)
def mat(name,color,rough=.4,metal=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 return m,p
wood,p=mat('Finish | Photographed white oak satin',(.4,.28,.16))
n=wood.node_tree.nodes;l=wood.node_tree.links
uv=n.new('ShaderNodeTexCoord');maps={}
for key,filename in [('color','white_oak_veneer_diff_2k.jpg'),('rough','white_oak_veneer_rough_2k.jpg'),('normal','white_oak_veneer_nor_gl_2k.jpg')]:
 t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(textures/filename),check_existing=True)
 if key!='color':t.image.colorspace_settings.name='Non-Color'
 t.image.pack();l.new(uv.outputs['UV'],t.inputs['Vector']);maps[key]=t
l.new(maps['color'].outputs['Color'],p.inputs['Base Color'])
r=n.new('ShaderNodeMapRange');r.inputs['To Min'].default_value=.29;r.inputs['To Max'].default_value=.48;l.new(maps['rough'].outputs['Color'],r.inputs['Value']);l.new(r.outputs[0],p.inputs['Roughness'])
norm=n.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.22;l.new(maps['normal'].outputs['Color'],norm.inputs['Color']);l.new(norm.outputs[0],p.inputs['Normal'])
p.inputs['Coat Weight'].default_value=.12;p.inputs['Coat Roughness'].default_value=.32
shadow,_=mat('Finish | Deep cabinet reveals',(.028,.022,.015),.65)
steel,p=mat('Finish | Satin brushed nickel',(.48,.49,.48),.26,1);next(i for i in p.inputs if 'Anisotropic' in i.name and 'Rotation' not in i.name).default_value=.4
iron,_=mat('Finish | Cast iron stove grates',(.016,.018,.017),.56,.55)
# Narrow, low-contrast mineral veins instead of broad graphic white outlines.
stone=bpy.data.materials['Kitchen | Honed charcoal soapstone'];nodes=stone.node_tree.nodes
r=next(n for n in nodes if n.type=='VALTORGB' and n.name.endswith('.001'))
r.color_ramp.elements[0].position=.0008;r.color_ramp.elements[1].position=.0045
mix=next(n for n in nodes if n.type=='MIX_RGB');mix.inputs[2].default_value=(.085,.095,.083,1)
b=next(n for n in nodes if n.type=='BUMP');b.inputs['Distance'].default_value=.00012;b.inputs['Strength'].default_value=.12
p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Roughness'].default_value=.34;p.inputs['Coat Weight'].default_value=.08
# Actual two-surface clear glass; Cycles handles its refraction and daylight transmission.
glass,p=mat('Finish | Clear low iron window glass',(.98,.99,1),.025)
p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.45

def oak_uv(o,shelf=False):
 if o.type!='MESH':return
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale')
 # Each panel takes a different part of the same photographed veneer sheet.
 rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for poly in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(poly.normal[i]))
  for li in poly.loop_indices:
   v=o.data.vertices[o.data.loops[li].vertex_index].co
   x,y,z=[v[i]*o.scale[i] for i in range(3)]
   if shelf:u,vv=((y/.7,x/1.6) if axis==2 else ((z/.7,x/1.6) if axis==1 else (y/.7,z/1.6)))
   else:u,vv=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],vv+off[1])

for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 col=bpy.data.collections.new('Kitchen | Cabinet fronts and photographic detail');scene.collection.children.link(col)
 def box(name,loc,dims,ma=wood,parent=None,bev=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  if bev:
   b=o.modifiers.new('Machined edge highlights','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
  if ma==wood:oak_uv(o)
  return o
 def tube(name,points,radius,ma,parent=None):
  d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=16;d.bevel_depth=radius;d.bevel_resolution=4
  p=d.splines.new('POLY');p.points.add(len(points)-1)
  for a,b in zip(p.points,points):a.co=(*b,1)
  o=bpy.data.objects.new(name,d);col.objects.link(o);o.parent=parent;d.materials.append(ma);return o
 def cyl(name,loc,radius,depth,ma,parent=None,rot=None):
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth)
  o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc
  if rot:o.rotation_euler=rot
  o.data.materials.append(ma)
  b=o.modifiers.new('Soft turned edges','BEVEL');b.width=.001;b.segments=3
  for p in o.data.polygons:p.use_smooth=True
  return o
 # Remove every exposed support and cleat on the five kitchen floating shelves.
 removed=[]
 for o in list(scene.objects):
  n=original(o).lower()
  if any(n.startswith(prefix) for prefix in ['wall shelf |','microwave upper shelf |','stove shelf |','sink window shelf |','sink left shelf |']):
   if any(x in n for x in ['bracket','cleat']):removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
 # Replace wood consistently, with grain following each component's construction.
 for o in list(scene.objects):
  if o.type!='MESH':continue
  waswood=any(m and (m.name.startswith('Natural oak') or m.name.startswith('Tour | Brushed oak')) for m in o.data.materials)
  if waswood:
   for slot in o.material_slots:
    if slot.material and slot.material.name.startswith(('Natural oak','Tour | Brushed oak')):slot.material=wood
   oak_uv(o,('shelf' in original(o).lower() and 'oak' in original(o).lower() and o.dimensions.z<.06))
  for slot in o.material_slots:
   if slot.material and slot.material.name.startswith(('Brushed chrome','Stainless appliances','Microwave | brushed stainless')):slot.material=steel
   if scene==tour and 'glazing' in original(o).lower():slot.material=glass
  # Kitchen edge radii are small enough to catch highlights without looking inflated.
  if o.parent and (o.parent.name.startswith('Kitchen') or 'Fridge surround' in original(o)):
   for m in o.modifiers:
    if m.type=='BEVEL':m.segments=max(m.segments,3);m.width=min(m.width,.002)
 # Hidden support rods sit entirely within the existing 32 mm boards.
 shelves=[o for o in scene.objects if o.type=='MESH' and any(k in original(o).lower() for k in ['oak floating shelf','sink window shelf | oak board','sink left shelf | oak board','stove shelf | floating oak board'])]
 for shelf in shelves:
  shelf['construction']='Floating shelf with concealed wall fixing; no exposed brackets';shelf['edge_radius_mm']=1.2
  shelf['source_revision']=16
 # West counter: real drawers/doors, a recessed plinth and 3 mm reveals.
 west=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='c08078d4-006c-4eba-8032-0bf18c432cec')
 for body in list(west.children):
  if 'base cabinets' not in original(body).lower():continue
  lo=-body.location.y-body.dimensions.y/2;hi=lo+body.dimensions.y
  body.dimensions.x=.606;body.location.x=.303;body.dimensions.z=.758;body.location.z=.509
  body.data.materials.clear();body.data.materials.append(shadow)
  box('Joinery | west recessed oak plinth',(.548,-(lo+hi)/2,.068),(.025,hi-lo,.116),wood,west)
  count=max(1,round((hi-lo)/.55));pitch=(hi-lo)/count
  for i in range(count):
   station=lo+(i+.5)*pitch;width=pitch-.003
   box('Joinery | west lower oak door',(.624,-station,.422),(.022,width,.574),wood,west)
   box('Joinery | west cutlery drawer',(.624,-station,.803),(.022,width,.181),wood,west)
   for z in [.673,.846]:
    tube('Joinery | west nickel pull',[(.645,-station-.105,z),(.669,-station-.105,z),(.669,-station+.105,z),(.645,-station+.105,z)],.0035,steel,west)
  for station in [lo+.009,hi-.009]:box('Joinery | oak range end panel',(.303,-station,.509),(.606,.018,.758),wood,west)
 # North front layout respects dishwasher and sink boundaries exactly.
 north=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a')
 for o in list(north.children):
  if 'Cabinet seam' in original(o):bpy.data.objects.remove(o,do_unlink=True)
  elif 'base cabinets' in original(o).lower():
   for v in o.data.vertices:
    if v.co.y*o.scale.y+o.location.y<-.61:v.co.y+=.014/o.scale.y
    if v.co.z*o.scale.z+o.location.z<.13:v.co.z=(.13-o.location.z)/o.scale.z
   o.data.materials.clear();o.data.materials.append(shadow)
 box('Joinery | north recessed oak plinth',(1.1816,-.554,.068),(2.3632,.025,.116),wood,north)
 def northdoor(a,b,bottom,top,pull=True):
  x=(a+b)/2;box('Joinery | north oak cabinet front',(x,-.624,(bottom+top)/2),(b-a-.003,.022,top-bottom),wood,north)
  if pull:
   z=top-.045;tube('Joinery | north nickel pull',[(x-.09,-.642,z),(x-.09,-.665,z),(x+.09,-.665,z),(x+.09,-.642,z)],.0035,steel,north)
 northdoor(0,.1529,.135,.893,False)
 northdoor(.1529,.7625,.135,.443,False) # Fixed lower face beneath the integrated dishwasher drawer.
 for a,b in [(.7625,1.1816),(1.1816,1.6007)]:northdoor(a,b,.135,.663)
 for a,b in [(1.6007,1.98195),(1.98195,2.3632)]:
  northdoor(a,b,.135,.709);northdoor(a,b,.713,.893)
 for o in scene.objects:
  if o.name.startswith(('Dishwasher oak integrated front','Dishwasher recessed pull')):o.location.y+=.024
  elif o.name.startswith('Dishwasher drawer reveal'):o.location.y=-.606
 # Rounded tubular tap replaces the rectangular placeholder faucet.
 sink=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='4be42708-ac78-437e-8895-9042270f0235')
 for o in list(sink.children):
  if original(o).startswith(('Kitchen tap','Kitchen spout')):bpy.data.objects.remove(o,do_unlink=True)
 x=.4191;y=-.036
 cyl('Faucet | deck escutcheon',(x,y,.94),.028,.012,steel,sink)
 cyl('Faucet | mixer body',(x,y,1.018),.019,.15,steel,sink)
 points=[(x,y,z) for z in [1.08,1.16,1.225]]
 for i in range(1,33):
  a=math.pi*i/32;points.append((x,y-.095+.095*math.cos(a),1.225+.095*math.sin(a)))
 points.extend([(x,y-.19,1.19),(x,y-.19,1.17)])
 tube('Faucet | continuous gooseneck',points,.011,steel,sink)
 cyl('Faucet | pull down aerator',(x,y-.19,1.165),.015,.04,steel,sink)
 tube('Faucet | mixer lever',[(x+.024,y,1.04),(x+.07,y,1.04),(x+.07,y,1.10)],.005,steel,sink)
 # Range details: cast grates, burner caps and turned control knobs.
 stove=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a')
 for o in list(stove.children):
  if o.type=='MESH' and original(o).startswith('Torus'):bpy.data.objects.remove(o,do_unlink=True)
 for u in [.19812,.56388]:
  for v in [-.1778,-.4572]:
   cyl('Range | burner cap',(u,v,.96),.055,.012,iron,stove)
   for du,dv in [(-.092,0),(.092,0),(0,-.092),(0,.092)]:
    dx=.075 if du else .013;dy=.013 if du else .075
    box('Range | cast iron grate',(u+du*.70,v+dv*.70,.984),(dx,dy,.014),iron,stove,.002)
 box('Range | satin control fascia',(.381,-.643,.827),(.741,.022,.106),steel,stove)
 for u in [.11,.245,.381,.517,.652]:
  cyl('Range | turned control knob',(u,-.668,.83),.022,.022,steel,stove,(math.pi/2,0,0))
  box('Range | knob index',(u,-.681,.844),(.002,.001,.008),iron,stove,.0003)
 hinge=next(o for o in stove.children if o.name.startswith('Operation | Oven'))
 box('Range | oven door metal surround',(0,.013,.253),(.738,.024,.51),steel,hinge,.004)
 # Soften existing ceramics with a restrained glaze and fine surface variation.
 for m in [m for m in bpy.data.materials if m.name.startswith('Shelf styling |') and any(t in m.name for t in ['porcelain','glaze','terracotta'])]:
  p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Coat Weight'].default_value=.2 if 'terracotta' not in m.name else .04
 scene['source_revision']=16;scene['kitchen_finish_notes']='Photographed white oak PBR with real-scale grain, recessed cabinet plinths, separate slab doors/drawers, 3 mm reveals, satin nickel, honed soapstone, concealed shelf supports.'
 assert not any('bracket' in original(o).lower() and any(original(o).lower().startswith(prefix) for prefix in ['wall shelf |','microwave upper shelf |','stove shelf |','sink window shelf |','sink left shelf |']) for o in scene.objects)
 if scene==source:scene.name='Full House | Drawing Revision 16'
 print(scene.name,'removed exposed support pieces:',len(removed),'floating boards:',len(shelves))
# Contextual daylight gives the windows and reflections a photographed outdoor environment.
bpy.context.window.scene=tour
world=tour.world;nodes=world.node_tree.nodes;links=world.node_tree.links
bg=next(n for n in nodes if n.type=='BACKGROUND');bg.inputs['Strength'].default_value=.55
tex=nodes.new('ShaderNodeTexEnvironment');tex.image=bpy.data.images.load(str(textures/'residential_garden_2k.hdr'),check_existing=True);tex.image.pack()
coords=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Rotation'].default_value[2]=1.2
links.new(coords.outputs['Generated'],mapping.inputs['Vector']);links.new(mapping.outputs[0],tex.inputs['Vector']);links.new(tex.outputs['Color'],bg.inputs['Color'])
for o in tour.objects:
 if o.type=='LIGHT':
  if o.data.type=='SUN':o.data.energy=.7;o.data.angle=.08
  if o.name=='Tour | Kitchen':o.data.energy=55;o.data.color=(1,.92,.80)
  if o.name=='Tour | Kitchen window daylight':o.data.energy=65;o.data.size=1.0;o.data.color=(.95,.97,1)
tour.view_settings.view_transform='AgX';tour.view_settings.exposure=0
# Cycles quality settings apply to final stills; EEVEE remains responsive for movement.
tour.cycles.samples=192;tour.cycles.use_denoising=True;tour.cycles.adaptive_threshold=.025;tour.cycles.max_bounces=10;tour.cycles.transmission_bounces=8;tour.cycles.transparent_max_bounces=8
prefs=bpy.context.preferences.addons['cycles'].preferences
try:prefs.compute_device_type='METAL';prefs.refresh_devices();tour.cycles.device='GPU'
except Exception:tour.cycles.device='CPU'
for d in prefs.devices:d.use=(d.type=='METAL')
def camera(name,eye,target,lens):
 d=bpy.data.cameras.new(name);d.lens=lens;d.clip_start=.025;d.clip_end=100;d.dof.use_dof=True;d.dof.focus_distance=(Vector(target)-Vector(eye)).length;d.dof.aperture_fstop=8
 o=bpy.data.objects.new(name,d);tour.collection.objects.link(o);o.location=eye;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
cam=camera('Photo | Sink and floating shelves',(.10,6.35,1.61),(-.12,8.46,1.27),25)
camera('Photo | Fridge and microwave shelves',(-1.12,7.65,1.65),(.1,5.36,1.40),27)
camera('Photo | Stove and floating prep shelf',(.42,6.22,1.62),(-1.9,6.55,1.25),27)
tour.camera=cam;tour.frame_set(1);tour.render.resolution_x=1800;tour.render.resolution_y=1300;tour.render.resolution_percentage=100;tour.render.filepath=str(base/'walkthrough/07-photoreal-kitchen.png')
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='RENDERED'
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
print('Revision 16 saved; textures packed; both models have floating shelves and detailed kitchen joinery.')
