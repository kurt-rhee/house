import bpy,json,math
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output/blender/full-house')
doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text());s=bpy.context.scene
col=next(o for o in s.objects if o.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a' and o.type=='EMPTY').users_collection[0]
def xyz(x,y,z=0):return ((x-19383.1)/1000,(10783-y)/1000,z)
def material(name,color,rough=.5):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;return m
oak=next(o for o in s.objects if o.name.startswith('Oak base cabinets')).data.materials[0]
ivory=material('Wardrobe | Warm ivory lacquer',(.74,.71,.64),.55)
bronze=material('Wardrobe | Recessed bronze pulls',(.13,.10,.065),.3)
wallmat=next(o for o in s.objects if o.get('source_wall_id')=='743fa984-048d-48a9-923a-a99198a7c60e' and o.type=='MESH').data.materials[0]
trim=material('Pocket door | Warm white trim',(.84,.83,.78),.5)
glass=next(o for o in s.objects if o.get('source_wall_id')=='ad218721-76be-4635-81dc-048de2d8bdae' and 'glazing' in o.name).data.materials[0]
def empty(name,location):
 o=bpy.data.objects.new(name,None);col.objects.link(o);o.location=location;return o
def box(name,loc,dims,ma,parent,bevel=.004):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
 if bevel:b=o.modifiers.new('Soft edges','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
# Remove the former overhead storage, keeping the upholstered headboard and bedside pieces.
prefixes=('Continuous concealed cabinet back','Continuous cabinet top','Continuous cabinet underside','Concealed cabinet partition','Flush wardrobe front','Fine oak lower reveal','Concealed LED diffuser','LED screening lip','2700K headboard wash')
for o in [o for o in s.objects if o.name.startswith(prefixes)]:bpy.data.objects.remove(o,do_unlink=True)
for r in [o for o in s.objects if o.get('main_bedroom_storage') or o.name.startswith('Laundry paired French doors') or o.get('laundry_pocket_door')]:
 for child in list(r.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
 bpy.data.objects.remove(r,do_unlink=True)
for f in doc['fixtures'].values():
 if f['kind'] not in ['Wardrobe','QuarterRoundShelves']:continue
 r=empty('Main bedroom | '+f['kind'],xyz(f['origin']['x'],f['origin']['y']));r.rotation_euler.z=-math.radians(f['rotation']);r['source_fixture_id']=f['id'];r['main_bedroom_storage']=True;r['overall_height_mm']=2286
 w,d,H=f['width']/1000,f['depth']/1000,2.286
 if f['kind']=='Wardrobe':
  box('Wardrobe oak back',(w/2,-.009,H/2),(w,.018,H),oak,r)
  for x in [.009,w-.009]:box('Wardrobe ivory side',(x,-d/2,H/2),(.018,d,H),ivory,r)
  for z in [.10,H-.009]:box('Wardrobe oak horizontal',(w/2,-d/2,z),(w-.036,d,.018),oak,r)
  box('Wardrobe oak center partition',(w/2,-d/2,H/2),(.018,d,H-.12),oak,r)
  box('Wardrobe plinth',(w/2,-d/2,.05),(w-.025,d-.04,.1),ivory,r)
  box('Wardrobe upper shelf',(w/2,-d/2,2.02),(w-.036,d-.02,.018),oak,r)
  for i in range(2):
   cx=w*(.25+.5*i);front=-d+.013+.028*i
   box('Wardrobe bypass front '+str(i+1),(cx,front,1.19),(w/2+.018,.024,2.17),ivory,r)
   box('Wardrobe recessed pull '+str(i+1),(cx+(w/4-.055)*(1 if i==0 else -1),front-.014,1.13),(.018,.006,.22),bronze,r,.002)
   box('Wardrobe fixed hanging rail',(cx,-d*.48,1.88),(w/2-.09,.025,.025),bronze,r)
  r['interior']='Two fixed hanging compartments with upper shelf; sliding bypass doors'
 else:
  box('Rounded shelf oak back',(w/2,-.009,H/2),(w,.018,H),oak,r)
  for level,z in enumerate([.12,.55,.98,1.41,1.84,2.262]):
   pts=[(0,0)]+[(w*math.cos(i*math.pi/2/48),-d*math.sin(i*math.pi/2/48)) for i in range(49)]
   verts=[(x,y,z+dz) for dz in [-.012,.012] for x,y in pts];n=len(pts)
   faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
   me=bpy.data.meshes.new('Quarter-round shelf');me.from_pydata(verts,[],[tuple(reversed(face)) for face in faces]);me.update();o=bpy.data.objects.new('Quarter-round oak shelf '+str(level+1),me);col.objects.link(o);o.parent=r;o.data.materials.append(oak)
   b=o.modifiers.new('Rounded shelf edge','BEVEL');b.width=.003;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
  r['shelf_count']=6
# Rebuild the two contiguous partition segments to match the new opening and pocket.
wallids=['ad218721-76be-4635-81dc-048de2d8bdae','743fa984-048d-48a9-923a-a99198a7c60e']
old=[o for o in s.objects if o.get('source_wall_id') in wallids or o.name.startswith(('Laundry French doorway','Kitchen west opening jamb'))]
# Collect all descendants before removing an old assembly.
remove=set(old)
for o in old:remove.update(o.children_recursive)
for o in remove:bpy.data.objects.remove(o,do_unlink=True)
for wid in wallids:
 w=doc['walls'][wid];root=empty(w['name']+' | wall assembly',xyz(w['start']['x'],w['start']['y']));root['source_wall_id']=wid
 length=(w['end']['y']-w['start']['y'])/1000;t=w['thickness']/1000
 def part(name,a,b,z1,z2,ma=wallmat,thickness=None):
  if b-a<.00001 or z2-z1<.00001:return
  o=box(name,(0,-(a+b)/2,(z1+z2)/2),(thickness or t,b-a,z2-z1),ma,root,.001);o['source_wall_id']=wid;return o
 ops=[]
 for cat in ['windows','doors']:
  for op in doc[cat].values():
   if op['wall']==wid:ops.append(((op['position']-op['width']/2)/1000,(op['position']+op['width']/2)/1000,cat,op))
 cursor=0
 for a,b,cat,op in sorted(ops):
  z1,z2=(1.0,2.1) if cat=='windows' else (0,2.032)
  part(w['name']+' solid wall',cursor,a,0,2.4384);part(w['name']+' sill wall',a,b,0,z1);part(w['name']+' opening header',a,b,z2,2.4384)
  for station in [a,b]:part(w['name']+' jamb',station-.012,station+.012,z1,z2,trim)
  part(w['name']+' head trim',a,b,z2-.012,z2+.012,trim)
  if cat=='windows':
   part(w['name']+' glazing',a,b,z1,z2,glass,.012);part(w['name']+' window sill',a,b,z1-.012,z1+.012,trim)
   part(w['name']+' mullion',(a+b)/2-.012,(a+b)/2+.012,z1,z2,trim)
  cursor=b
 part(w['name']+' solid wall',cursor,length,0,2.4384)
# The single laundry leaf is shown fully retracted north, with its leading edge at the jamb.
door=doc['doors']['9150da68-b336-4060-bdae-30eb0d80deca'];w=doc['walls'][door['wall']];a=w['start']['y']+door['position']-door['width']/2
r=empty('Laundry | Retracted pocket door',xyz(w['start']['x'],a));r['laundry_pocket_door']=True;r['source_door_id']=door['id'];r['door_pose']='Fully retracted north into partition';r['opening_width_mm']=door['width']
box('Pocket door concealed leaf',(0,door['width']/2000,1.016),(.038,door['width']/1000,2.032),ivory,r)
box('Pocket door exposed leading edge',(0,-.008,1.016),(.038,.016,2.032),ivory,r,.001)
box('Pocket door recessed edge pull',(.020,-.01,1.0),(.003,.012,.10),bronze,r,.001)
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident in doc['fixtures']:
  f=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f['width'],f['depth']]
  for field in ['material','style']:
   if f.get(field):o['drawing_'+field]=f[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision']);s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')})
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
cam=next((o for o in s.objects if o.name=='Current | Main bedroom wardrobe'),None)
if cam is None:
 data=bpy.data.cameras.new('Current | Main bedroom wardrobe');data.type='ORTHO';cam=bpy.data.objects.new(data.name,data);col.objects.link(cam)
cam.location=xyz(20100,14900,6.4);target=Vector(xyz(17600,11000,.95));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.6
main=next(o for o in s.objects if o.name=='Current | Main house');s.camera=main;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Wardrobe, quarter-round shelves and laundry pocket door saved at revision',doc['revision'])
