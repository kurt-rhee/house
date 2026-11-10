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

door=doc['doors']['ea47a63a-2d6e-42df-a4fd-5672d8c2b2fc'];wall=doc['walls'][door['wall']]
assert door['hinge_at_end'] and door['swing']=='Right'
r=bpy.data.objects.new('Bedroom 3 | East-hinged hallway door',None);col.objects.link(r)
r['source_door_id']=door['id'];r['door_pose']='Fully open into bedroom against east wall';r['hinge_at_end']=True;r['source_revision']=doc['revision']
x=wall['start']['x']+door['position']+door['width']/2;y=wall['start']['y']
r.location=xyz(x,y)
# Full-open leaf extends north into Bedroom 3, beside its east wall.
paint=mat('Bedroom 3 | Warm ivory door',(.74,.71,.64),.5)
L=door['width']/1000
box('Bedroom 3 hallway door leaf',(0,L/2,1.016),(.035,L,2.032),paint,r,.003)
for side in [-1,1]:box('Bedroom 3 door lever',(side*.03,L-.085,1.0),(.06,.11,.018),metal,r,.003)
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

s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Bedroom 3 hallway door synchronized, east jamb hinge, drawing revision',doc['revision'])
