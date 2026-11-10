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

f=next(f for f in doc['fixtures'].values() if f.get('style','').startswith(('low_laundry_supply_cabinet','low_pantry_tambour')))
for old in [o for o in s.objects if o.get('source_fixture_id')==f['id'] and o.type=='EMPTY']:
 for child in list(old.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
 bpy.data.objects.remove(old,do_unlink=True)
r=root_for(f);r['laundry_supply_cabinet']=True;r['overall_height_mm']=932.5
w,d=f['width']/1000,f['depth']/1000
for x in [.009,w-.009]:box('Supply cabinet oak side',(x,-d/2,.49),(.018,d,.85),wood,r)
box('Supply cabinet back',(w/2,-.009,.49),(w,.018,.85),wood,r)
box('Supply cabinet plinth',(w/2,-d/2,.055),(w-.035,d-.04,.11),wood,r)
box('Supply cabinet base',(w/2,-d/2,.13),(w-.036,d-.018,.025),wood,r)
# Three shallow-sided internal pull-outs, with clearance for tambour guides.
trays=[]
for i,z in enumerate([.19,.43,.67]):
 tray=bpy.data.objects.new('Pantry pull-out shelf '+str(i+1),None);col.objects.link(tray);tray.parent=r;tray.location=(0,0,0);trays.append(tray)
 tw=w-.09;td=d-.08;cy=-d/2+.01
 box('Pantry shelf base',(w/2,cy,z),(tw,td,.018),wood,tray,.002)
 for x in [(w-tw)/2,(w+tw)/2]:box('Pantry shelf side',(x,cy,z+.044),(.012,td,.088),wood,tray,.002)
 for y in [cy-td/2,cy+td/2]:box('Pantry shelf end',(w/2,y,z+.044),(tw,.012,.088),wood,tray,.002)
 for x in [.028,w-.028]:box('Pantry full-extension runner',(x,cy,z-.01),(.015,td,.022),metal,tray,.001)
 tray['extension_mm']=350;tray['contents']=['Canned goods and jars','Grains and baking supplies','Snacks and packets'][i]

box('Supply cabinet top rail',(w/2,-d+.01,.877),(w-.036,.03,.047),wood,r)
box('Supply cabinet pale worktop',(w/2,-d/2,.915),(w+.01,d+.01,.035),stone,r)
# Closed horizontal oak slats make the roll-up front legible in the view.
for i in range(35):
 z=.15+(i+.5)*.020
 box('Supply cabinet tambour slat %02d'%i,(w/2,-d-.004,z),(w-.04,.018,.0185),wood,r,.0015)
box('Supply cabinet tambour pull',(w/2,-d-.025,.185),(.16,.025,.013),metal,r,.003)
r['access']='Pantry for dry food; roll-up front and three internal pull-out shelves; laundry pocket door removes swing obstruction'
r['storage_use']='Food pantry'
r['shelf_count']=3
# Preserve source properties on the new assembly and existing fixtures.
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident in doc['fixtures']:
  f2=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f2['width'],f2['depth']]
  for field in ['material','style']:
   if f2.get(field):o['drawing_'+field]=f2[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision'])
s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')})
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
# Save the normal closed-cabinet model before preparing the explanatory cutaway.
main=next(o for o in s.objects if o.name=='Current | Main house')
s.camera=main;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
cutaway=[]
for o in s.objects:
 if o.get('source_wall_id') in ['970ed9db-d98e-400f-8588-d7dbb8c6386f','743fa984-048d-48a9-923a-a99198a7c60e','b88afdbc-83c7-436b-a52b-374da2f48e67'] or (o.parent==r and ('tambour slat' in o.name or 'tambour pull' in o.name)):
  cutaway.append((o,o.hide_render));o.hide_render=True
trays[1].location.y=-.35
cam=next((o for o in s.objects if o.name=='Current | Pantry detail'),None)
if cam is None:
 data=bpy.data.cameras.new('Current | Pantry detail');data.type='ORTHO';cam=bpy.data.objects.new('Current | Pantry detail',data);col.objects.link(cam)
cam.location=xyz(15900,6750,3.0);target=Vector(xyz(16650,4260,.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=2.4
s.camera=cam;s.render.resolution_x=1400;s.render.resolution_y=1400;s.render.filepath=str(base/'06-pantry-open.png');bpy.ops.render.render(write_still=True)
for o,state in cutaway:o.hide_render=state
trays[1].location.y=0
s.camera=main;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'02-main-house.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
assert len(trays)==3 and r['storage_use']=='Food pantry'
print('Three-shelf pantry synchronized at revision',doc['revision'])
