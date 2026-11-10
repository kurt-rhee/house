import bpy,json,math
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output/blender/full-house');doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text());s=bpy.context.scene
ident='0a136254-797b-44fe-b369-8f6e98f33bc0';f=doc['fixtures'][ident]
old=next(o for o in s.objects if o.type=='EMPTY' and o.get('source_fixture_id')==ident);col=old.users_collection[0]
wood=next(o for o in s.objects if o.name.startswith('Oak base cabinets') and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a').data.materials[0]
stone=next(o for o in s.objects if o.type=='MESH' and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a' and 'countertop' in o.name.lower()).data.materials[0]
metal=bpy.data.materials.get('Brushed chrome') or wood
for o in list(old.children_recursive):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.objects.remove(old,do_unlink=True)
def xyz(x,y,z=0):return ((x-19383.1)/1000,(10783-y)/1000,z)
r=bpy.data.objects.new('Kitchen | Left-facing appliance garage',None);col.objects.link(r);r.location=xyz(f['origin']['x'],f['origin']['y']);r.rotation_euler.z=-math.radians(f['rotation']);r['source_fixture_id']=ident;r['opening_direction']='West / left into kitchen aisle';r['shutter_pose']='Raised to demonstrate side access';r['overall_height_mm']=2260
w,d,H=f['width']/1000,f['depth']/1000,2.26
def box(name,loc,dims,ma=wood,bev=.003):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=r;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
 if bev:b=o.modifiers.new('Soft cabinet edges','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
for x in [.009,w-.009]:box('Appliance garage end panel',(x,-d/2,H/2),(.018,d,H))
box('Appliance garage back',(w/2,-.009,H/2),(w,.018,H))
box('Appliance garage top',(w/2,-d/2,H-.009),(w,d,.018))
box('Appliance garage plinth',(w/2,-d/2,.05),(w-.036,d-.035,.1))
box('Appliance garage base shelf',(w/2,-d/2,.12),(w-.036,d-.018,.018))
box('Appliance garage lower cabinet top',(w/2,-d/2,.905),(w-.036,d,.025))
box('Appliance garage soapstone worktop',(w/2,-d/2,.935),(w-.036,d,.035),stone)
for i in range(2):
 cx=w*(.25+i*.5)
 box('Appliance garage lower oak front',(cx,-d+.012,.50),(w/2-.022,.024,.76))
 box('Appliance garage lower pull',(cx,-d-.006,.80),(.14,.012,.012),metal)
box('Appliance garage upper bay ceiling',(w/2,-d/2,1.67),(w-.036,d-.018,.025))
box('Appliance garage upper storage front',(w/2,-d+.012,1.975),(w-.036,.024,.55))
# Raised tambour curtain leaves the west-facing appliance bay visibly accessible.
for i in range(8):
 box('Appliance garage raised tambour slat '+str(i),(w/2,-d+.012,1.49+i*.021),(w-.047,.018,.019),wood,.0015)
box('Appliance garage shutter lift pull',(w/2,-d-.004,1.482),(.16,.016,.014),metal)
r['bay_clear_width_mm']=(w-.036)*1000;r['bay_depth_mm']=(d-.018)*1000
for o in s.objects:
 fid=o.get('source_fixture_id')
 if fid in doc['fixtures']:
  src=doc['fixtures'][fid];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[src['width'],src['depth']]
  for key in ['material','style']:
   if src.get(key):o['drawing_'+key]=src[key]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision']);s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')});(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
cam=next((o for o in s.objects if o.name=='Current | Appliance garage'),None)
if cam is None:
 data=bpy.data.cameras.new('Current | Appliance garage');data.type='ORTHO';cam=bpy.data.objects.new(data.name,data);col.objects.link(cam)
cam.location=xyz(17200,3400,3.7);target=Vector(xyz(19400,5200,1.05));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.6
main=next(o for o in s.objects if o.name=='Current | Main house');s.camera=main;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for name,file,w,h in [('Current | Appliance garage','08-appliance-garage.png',1400,1400),('Current | Kitchen','04-kitchen.png',1600,1600),('Current | Main house','02-main-house.png',2000,1800)]:
 s.camera=next(o for o in s.objects if o.name==name);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=main;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'02-main-house.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Left-facing garage aligned to fridge and saved at revision',doc['revision'])
