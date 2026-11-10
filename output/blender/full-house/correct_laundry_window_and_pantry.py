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
# Resize the low pantry while preserving its pull-out carriage and shelves.
f=doc['fixtures']['d3200e76-5060-41a2-b8c6-527fa6d33ef1']
low=next(o for o in s.objects if o.type=='EMPTY' and o.get('source_fixture_id')==f['id'])
old_width=low.get('plan_footprint_mm',[228.6,889])[0];ratio=f['width']/old_width
for o in low.children_recursive:
 if o.type=='MESH':o.location.x*=ratio;o.dimensions.x*=ratio
for o in low.children:
 if o.name.startswith('Pantry oak filler') or o.name.startswith('Pantry filler worktop'):
  o.location.x=f['width']/1000+.00635;o.dimensions.x=.0127
low['source_revision']=doc['revision'];low['plan_footprint_mm']=[f['width'],f['depth']]
# Rebuild the north wall around the measured window edge; trim extends 18mm.
wid='57466920-cd09-4ba8-ada2-1cce4354061f';wall=doc['walls'][wid]
old=[o for o in s.objects if o.get('source_wall_id')==wid]
wallmat=next(o.data.materials[0] for o in old if o.type=='MESH' and 'wall' in o.name.lower())
trim=next(o.data.materials[0] for o in old if o.type=='MESH' and 'trim' in o.name.lower())
glass=next(o.data.materials[0] for o in old if o.type=='MESH' and 'glazing' in o.name.lower())
for o in old:bpy.data.objects.remove(o,do_unlink=True)
rw=bpy.data.objects.new('Laundry north | Measured window wall',None);col.objects.link(rw);rw.location=xyz(wall['start']['x'],wall['start']['y']);rw['source_wall_id']=wid
L=(wall['end']['x']-wall['start']['x'])/1000;t=wall['thickness']/1000
op=doc['windows']['baf7ae37-de75-40d6-a38e-37af2a50ad15'];a=(op['position']-op['width']/2)/1000;b=(op['position']+op['width']/2)/1000
for name,x1,x2,z1,z2 in [('solid wall',0,a,0,2.4384),('sill wall',a,b,0,1),('header wall',a,b,2.1,2.4384),('solid wall',b,L,0,2.4384)]:
 o=box('Laundry north '+name,((x1+x2)/2,0,(z1+z2)/2),(x2-x1,t,z2-z1),wallmat,rw,.001);o['source_wall_id']=wid;o['view_wall_opacity']=.2
for z in [1,2.1]:box('Laundry north window trim',((a+b)/2,0,z),(b-a+.036,t,.036),trim,rw,.001)
for x in [a,b]:box('Laundry north window jamb',(x,0,1.55),(.036,t,1.136),trim,rw,.001)
box('Laundry north glazing',((a+b)/2,0,1.55),(b-a,.018,1.1),glass,rw,.001)
box('Laundry north mullion',((a+b)/2,0,1.55),(.024,t,1.1),trim,rw,.001)
for o in rw.children:o['source_wall_id']=wid
s['laundry_wall_to_north_window_trim_mm']=711.2
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident not in doc['fixtures']:continue
 f=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f['width'],f['depth']]
 for field in ['material','style']:
  if f.get(field):o['drawing_'+field]=f[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision'])
s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')})
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
active=next(o for o in s.objects if o.name=='Current | Transparent walls');s.camera=active;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for camera,file,w,h in [('Current | Laundry','05-laundry.png',1400,1400),('Current | Transparent walls','09-transparent-walls.png',2000,1800)]:
 s.camera=next(o for o in s.objects if o.name==camera);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=active;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Measured 28 inch wall-to-window clearance and wider pantry synchronized')
