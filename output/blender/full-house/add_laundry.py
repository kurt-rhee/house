import bpy,json,math
from pathlib import Path
from mathutils import Vector
s=bpy.context.scene;base=Path('/Users/kurt/Programs/house/output/blender/full-house')
doc=json.loads(Path('/Users/kurt/Programs/house/output/floor-plan.house.json').read_text())
col=next(o for o in s.objects if o.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a' and o.type=='EMPTY').users_collection[0]
def mat(name,color,rough=.45,metal=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
def xyz(x,y,z=0):return ((x-19383.1)/1000,(10783-y)/1000,z)
white=mat('Laundry | Warm white enamel',(.78,.79,.76),.26)
dark=mat('Laundry | Dark glass',(.018,.025,.028),.16,.3)
black=mat('Laundry | Rubber seal',(.012,.014,.014),.8)
metal=mat('Laundry | Brushed stainless',(.45,.49,.49),.26,.85)
blue=mat('Laundry | Recycling bin',(.06,.17,.25),.6)
gray=mat('Laundry | Trash bin',(.17,.18,.17),.6)
wood=next(o for o in s.objects if o.name.startswith('Oak base cabinets') and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a').data.materials[0]
stone=mat('Laundry | Pale worktop',(.76,.74,.67),.35)
for root in [o for o in s.objects if o.get('laundry_assembly')]:
 if root.get('laundry_assembly'):
  for o in list(root.children_recursive):bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.objects.remove(root,do_unlink=True)
def root_for(f):
 o=bpy.data.objects.new('Laundry | '+f['kind'],None);col.objects.link(o);o.location=xyz(f['origin']['x'],f['origin']['y']);o.rotation_euler.z=-math.radians(f['rotation']);o['source_fixture_id']=f['id'];o['laundry_assembly']=True;return o
def box(name,loc,size,ma,parent,bev=.006):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
 if bev:b=o.modifiers.new('Soft edges','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def cylinder(name,loc,radius,depth,ma,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.rotation_euler.x=math.pi/2;o.data.materials.append(ma)
 b=o.modifiers.new('Rounded rim','BEVEL');b.width=.005;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
for f in doc['fixtures'].values():
 if f['kind']=='WasherDryer':
  r=root_for(f);w,d=f['width']/1000,f['depth']/1000
  box('All-in-one washer-dryer body',(w/2,-d/2,.4953),(w,d,.9906),white,r,.018)
  box('Washer control panel',(w/2,-d-.008,.906),(w-.035,.018,.115),dark,r)
  cylinder('Washer selector',(w*.22,-d-.026,.907),.031,.016,metal,r)
  cylinder('Washer door rubber',(w/2,-d-.013,.505),.247,.027,black,r)
  cylinder('Washer door steel ring',(w/2,-d-.033,.505),.23,.025,metal,r)
  cylinder('Washer drum glass',(w/2,-d-.048,.505),.204,.012,dark,r)
  box('Washer door handle',(w*.81,-d-.062,.52),(.021,.025,.13),metal,r)
  box('Detergent drawer',(w*.17,-d-.022,.91),(.16,.016,.065),white,r)
  r['reference_dimensions']='27 x 39 x 33 1/8 inch all-in-one concept; LG WM6998 envelope'
 if f['kind']=='WasteCabinet':
  r=root_for(f);w,d=f['width']/1000,f['depth']/1000
  # Open carcass supports real bins behind the two fronts.
  for u in [.009,w-.009]:box('Waste cabinet side',(u,-d/2,.47),(.018,d,.87),wood,r)
  box('Waste cabinet back',(w/2,-.009,.47),(w,.018,.87),wood,r)
  box('Waste cabinet base',(w/2,-d/2,.11),(w,d,.04),wood,r)
  box('Waste worktop',(w/2,-d/2,.915),(w+.01,d+.01,.035),stone,r)
  box('Waste cabinet top rail',(w/2,-d-.012,.855),(w-.006,.023,.084),wood,r)
  for i,(label,ma) in enumerate([('Trash',gray),('Recycling',blue)]):
   u=w*(.25+.5*i)
   box(label+' pull-out oak front',(u,-d-.012,.46),(w/2-.006,.023,.70),wood,r)
   box(label+' pull handle',(u,-d-.04,.74),(.13,.025,.013),metal,r)
   # Hollow bin: four walls and bottom.
   bw=w/2-.055;bd=.48;z=.43;cy=-d+.28
   box(label+' bin bottom',(u,cy,.20),(bw,bd,.014),ma,r)
   for x in [u-bw/2,u+bw/2]:box(label+' bin wall',(x,cy,z),(.01,bd,.47),ma,r)
   for y in [cy-bd/2,cy+bd/2]:box(label+' bin wall',(u,y,z),(bw,.01,.47),ma,r)
  r['contents']='Separate pull-out trash and recycling bins'
# Associate the previously modeled kitchen drawer with its newly saved CAD fixture.
f=next(f for f in doc['fixtures'].values() if f['kind']=='DishwasherDrawer')
r=next(o for o in s.objects if o.get('design_element')=='dishwasher_drawer');r['source_fixture_id']=f['id']
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision']);(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
cam=next((o for o in s.objects if o.name=='Current | Laundry'),None)
if not cam:
 data=bpy.data.cameras.new('Current | Laundry');data.type='ORTHO';cam=bpy.data.objects.new('Current | Laundry',data);col.objects.link(cam)
cam.location=xyz(19700,10300,7.6);target=Vector(xyz(16100,5100,.65));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.0
# Hide only front cutaway walls in the laundry detail to see the appliance fronts.
cutaway=[]
for o in s.objects:
 if o.get('source_wall_id') in ['970ed9db-d98e-400f-8588-d7dbb8c6386f','743fa984-048d-48a9-923a-a99198a7c60e','b88afdbc-83c7-436b-a52b-374da2f48e67']:
  cutaway.append((o,o.hide_render));o.hide_render=True
s.camera=cam;s.render.resolution_x=1600;s.render.resolution_y=1400;s.render.filepath=str(base/'05-laundry.png');bpy.ops.render.render(write_still=True)
for o,state in cutaway:o.hide_render=state
s.camera=next(o for o in s.objects if o.name=='Current | Main house');s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'02-main-house.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Laundry and saved drawing fixtures synchronized; detail and main-house renders saved.')
