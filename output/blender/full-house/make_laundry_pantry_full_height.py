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

f=doc['fixtures']['e291dd5c-2063-4410-bae0-dbe79733ffe6']
for old in [o for o in s.objects if o.get('source_fixture_id')==f['id'] and o.type=='EMPTY']:
 for child in list(old.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
 bpy.data.objects.remove(old,do_unlink=True)
r=root_for(f);r.name='Laundry | Floor-to-ceiling pantry';r['laundry_supply_cabinet']=True;r['overall_height_mm']=2438.4;r['storage_use']='Food pantry';r['shelf_count']=7
w,d,H=f['width']/1000,f['depth']/1000,2.4384
for x in [.009,w-.009]:box('Tall pantry oak side',(x,-d/2,H/2),(.018,d,H),wood,r)
box('Tall pantry back',(w/2,-.009,H/2),(w-.036,.018,H),wood,r)
box('Tall pantry recessed plinth',(w/2,-d/2,.05),(w-.04,d-.04,.10),wood,r)
for z in [.12,.42,.72,1.02,1.32,1.62,1.92,2.22,H-.009]:box('Tall pantry shelf',(w/2,-d/2,z),(w-.036,d-.035,.018),wood,r,.002)
fronts=[]
for i in range(2):
 x=(i+.5)*w/2
 fronts.append(box('Tall pantry paired oak door '+str(i+1),(x,-d-.01,(H+.10)/2),(w/2-.004,.022,H-.10-.006),wood,r,.003))
 fronts.append(box('Tall pantry vertical pull '+str(i+1),(w/2+(-.025 if i==0 else .025),-d-.033,1.10),(.012,.025,.24),metal,r,.003))
r['access']='Paired narrow hinged fronts; adjustable shelves; ceiling-height carcass; clears north window trim and laundry pocket door'
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident in doc['fixtures']:
  f2=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f2['width'],f2['depth']]
  for field in ['material','style']:
   if f2.get(field):o['drawing_'+field]=f2[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision'])
s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')})
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
active=next(o for o in s.objects if o.name=='Current | Transparent walls');s.camera=active
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for camera,file,wid,hei in [('Current | Laundry','05-laundry.png',1400,1400),('Current | Transparent walls','09-transparent-walls.png',2000,1800)]:
 s.camera=next(o for o in s.objects if o.name==camera);s.render.resolution_x=wid;s.render.resolution_y=hei;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
# An interior view with the paired doors hidden reveals the shelf spacing.
for o in fronts:o.hide_render=True
cam=next(o for o in s.objects if o.name=='Current | Pantry detail');cam.location=xyz(15900,7000,3.4);target=Vector(xyz(16850,4200,1.2));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.3
s.camera=cam;s.render.resolution_x=1400;s.render.resolution_y=1600;s.render.filepath=str(base/'06-pantry-open.png');bpy.ops.render.render(write_still=True)
for o in fronts:o.hide_render=False
s.camera=active;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
assert abs(r['overall_height_mm']-2438.4)<.01
print('Existing pantry replaced with ceiling-height oak pantry, drawing revision',doc['revision'])
