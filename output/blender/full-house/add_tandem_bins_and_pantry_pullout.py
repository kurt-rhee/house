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

ids=['48ec0675-2eeb-408b-8963-b812d1d37be3','d3200e76-5060-41a2-b8c6-527fa6d33ef1']
for old in [o for o in s.objects if o.type=='EMPTY' and o.get('source_fixture_id') in ids]:
 for child in list(old.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
 bpy.data.objects.remove(old,do_unlink=True)
assemblies=[]
for ident in ids:
 f=doc['fixtures'][ident];r=root_for(f);w,d=f['width']/1000,f['depth']/1000
 waste=f['kind']=='WasteCabinet';r.name='Laundry | '+('Tandem recycling and trash' if waste else '9 inch pantry pullout')
 for x in [.009,w-.009]:box('Pullout cabinet oak side',(x,-d/2,.49),(.018,d,.85),wood,r)
 box('Pullout cabinet back',(w/2,-.009,.49),(w,.018,.85),wood,r)
 box('Pullout cabinet base',(w/2,-d/2,.12),(w-.036,d-.018,.025),wood,r)
 box('Pullout cabinet plinth',(w/2,-d/2,.055),(w-.035,d-.04,.11),wood,r)
 box('Pullout cabinet pale worktop',(w/2,-d/2,.915),(w+.01,d+.01,.035),stone,r)
 box('Pullout cabinet top rail',(w/2,-d+.01,.877),(w-.036,.03,.047),wood,r)
 tray=bpy.data.objects.new('Recycling first, trash behind | sliding carriage' if waste else 'Narrow pantry | sliding carriage',None);col.objects.link(tray);tray.parent=r
 tray['extension_mm']=610;assemblies.append(tray)
 box('Single pullout oak front',(w/2,-d-.012,.49),(w-.006,.023,.76),wood,tray)
 box('Single pullout handle',(w/2,-d-.04,.76),(min(.13,w-.06),.025,.013),metal,tray,.003)
 cy=-d+.31
 for x in [.028,w-.028]:box('Full extension runner',(x,cy,.15),(.015,.60,.025),metal,tray,.001)
 if waste:
  box('Tandem waste carriage base',(w/2,cy,.18),(w-.065,.60,.02),wood,tray)
  for label,ma,y in [('Recycling',blue,-d+.16),('Trash',gray,-d+.46)]:
   bw,bd=.28,.28
   box(label+' bin bottom',(w/2,y,.21),(bw,bd,.012),ma,tray)
   for x in [w/2-bw/2,w/2+bw/2]:box(label+' bin side',(x,y,.42),(.01,bd,.42),ma,tray)
   for yy in [y-bd/2,y+bd/2]:box(label+' bin end',(w/2,yy,.42),(bw,.01,.42),ma,tray)
  r['contents']='Recycling in front, trash behind, both on one sliding carriage';r['bin_order_front_to_back']='Recycling, Trash'
 else:
  for z in [.21,.44,.67]:
   box('Pantry pullout shelf',(w/2,cy,z),(w-.065,.60,.018),wood,tray,.002)
   for x in [.04,w-.04]:box('Pantry shelf retaining rail',(x,cy,z+.055),(.012,.60,.09),wood,tray,.002)
   for y in [cy-.30,cy+.30]:box('Pantry shelf end',(w/2,y,z+.055),(w-.065,.012,.09),wood,tray,.002)
  # Fill the pre-existing 3-inch space below the window beside the tall pantry.
  box('Pantry oak filler',(w+.0381,-d-.004,.49),(.0762,.018,.85),wood,r,.001)
  box('Pantry filler worktop',(w+.0381,-d/2,.915),(.0762,d+.01,.035),stone,r)
  r['storage_use']='Dry food pantry below north window';r['shelf_count']=3

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
# Show the recycling bin closest to the room and the trash bin behind it.
assemblies[0].location.y=-.610
s.camera=next(o for o in s.objects if o.name=='Current | Laundry');s.render.resolution_x=1600;s.render.resolution_y=1400;s.render.filepath=str(base/'10-tandem-bins-open.png');bpy.ops.render.render(write_still=True)
assemblies[0].location.y=0
s.camera=active;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
assert len(assemblies)==2
print('Recycling-first tandem bins and three-shelf narrow pantry synchronized at revision',doc['revision'])
