import bpy,json,math
from mathutils import Vector
from pathlib import Path
s=bpy.context.scene
base=Path('/Users/kurt/Programs/house/output/blender/full-house')
doc=json.loads(Path('/Users/kurt/Programs/house/output/floor-plan.house.json').read_text())
# The kitchen-side pocket door is fully retracted; remove the former glass slider.
wid='9d3f5626-ab84-4765-8db3-b1e78aa937d9'
for o in list(s.objects):
 if o.get('source_wall_id')==wid and ('glazing' in o.name or 'mullion' in o.name):bpy.data.objects.remove(o,do_unlink=True)
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision'])
s['pocket_door_state']='Kitchen-side door fully retracted into wall'
root=next(o for o in s.objects if o.get('source_fixture_id')=='4be42708-ac78-437e-8895-9042270f0235' and o.type=='EMPTY')
for o in list(s.objects):
 if o.parent==root and (o.name.startswith('Stainless sink bottom') or o.name.startswith('Sink side') or o.get('farmhouse_sink_part')):bpy.data.objects.remove(o,do_unlink=True)
m=bpy.data.materials.get('Kitchen | White fireclay') or bpy.data.materials.new('Kitchen | White fireclay');m.use_nodes=True;m.diffuse_color=(.92,.91,.87,1)
p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.92,.91,.87,1);p.inputs['Roughness'].default_value=.19
col=root.users_collection[0]
def box(name,loc,size,material,parent=None,bevel=.012):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if material:o.data.materials.append(material)
 if bevel:
  mod=o.modifiers.new('Rounded fireclay edges','BEVEL');mod.width=bevel;mod.segments=5
  o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
# Open the countertop and cabinet to the front, exposing the apron rather than an inset bowl.
bpy.context.view_layer.update()
cut=box('Temporary apron cutout',(root.matrix_world.translation.x+.4191,root.matrix_world.translation.y-.370,.86),(.844,.69,.39),None,bevel=0)
for o in list(s.objects):
 if o.type=='MESH' and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a' and o.name.startswith(('Soapstone kitchen countertop','Oak base cabinets')):
  mod=o.modifiers.new('Farmhouse sink apron opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut,do_unlink=True)
# Hollow single-bowl white fireclay sink, 33 inch wide, apron toward kitchen.
for name,loc,size in [
 ('Farmhouse basin floor',(.4191,-.326,.699),(.8382,.55,.05)),
 ('Farmhouse sink left',(.023,-.326,.805),(.046,.55,.25)),
 ('Farmhouse sink right',(.8152,-.326,.805),(.046,.55,.25)),
 ('Farmhouse sink back',(.4191,-.071,.805),(.8382,.04,.25)),
 ('Farmhouse exposed white apron',(.4191,-.605,.805),(.8382,.064,.25))]:
  o=box(name,loc,size,m,root);o['farmhouse_sink_part']=True
# Drain at bottom of open basin.
metal=bpy.data.materials.get('Brushed chrome')
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.042,depth=.004);o=bpy.context.object;o.name='Farmhouse sink drain';o.parent=root;o.location=(.4191,-.32,.727);o['farmhouse_sink_part']=True
if metal:o.data.materials.append(metal)
root['material']='White fireclay';root['sink_style']='Apron-front farmhouse single bowl'
assign=json.loads(s.get('material_assignments','{}'));assign[root['source_fixture_id']]={'material':'white fireclay','style':'farmhouse apron front'};s['material_assignments']=json.dumps(assign)
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
# Kitchen camera looks back toward the apron front and north-wall sink.
cam=next((o for o in s.objects if o.name=='Current | Kitchen'),None)
if cam is None:
 data=bpy.data.cameras.new('Current | Kitchen');data.type='ORTHO';cam=bpy.data.objects.new('Current | Kitchen',data);col.objects.link(cam)
cam.location=(5,1,9);target=Vector((-0.55,6.7,.65));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=6.9
main=next(o for o in s.objects if o.name=='Current | Main house')
s.camera=main;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for camera,file,w,h in [(cam,'04-kitchen.png',1600,1600),(main,'02-main-house.png',2000,1800),(next(o for o in s.objects if o.name=='Current | Whole property'),'01-whole-property.png',2400,1500)]:
 s.camera=camera;s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=cam;s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.filepath=str(base/'04-kitchen.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Pocket door retracted; white farmhouse sink installed; renders saved.')
