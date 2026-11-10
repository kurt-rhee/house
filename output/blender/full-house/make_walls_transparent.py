import bpy
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output/blender/full-house');s=bpy.context.scene
opacity=.20
original=bpy.data.materials['Warm white plaster']
name='View | Semi-transparent plaster'
m=bpy.data.materials.get(name)
if m is None:
 m=original.copy();m.name=name;m.use_nodes=True
 nodes=m.node_tree.nodes;links=m.node_tree.links
 out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
 source=out.inputs['Surface'].links[0].from_socket
 transparent=nodes.new('ShaderNodeBsdfTransparent');transparent.name='Clear wall component';transparent.inputs[0].default_value=(1,1,1,1)
 mix=nodes.new('ShaderNodeMixShader');mix.name='Wall view opacity';mix.inputs[0].default_value=opacity
 links.new(transparent.outputs[0],mix.inputs[1]);links.new(source,mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])
else:m.node_tree.nodes['Wall view opacity'].inputs[0].default_value=opacity
m.diffuse_color=(*original.diffuse_color[:3],opacity)
if hasattr(m,'surface_render_method'):
 keys=m.bl_rna.properties['surface_render_method'].enum_items.keys()
 if 'DITHERED' in keys:m.surface_render_method='DITHERED'
count=0
for o in s.objects:
 if o.type!='MESH' or not o.get('source_wall_id'):continue
 changed=False
 for slot in o.material_slots:
  if slot.material and slot.material.name in [original.name,name]:slot.material=m;changed=True
 if changed:o['view_wall_opacity']=opacity;count+=1
s['wall_view_opacity']=opacity;s['wall_view_notes']='Semi-transparent plaster for interior visibility; trim, glazing and cabinetry keep their finishes.'
s.cycles.transparent_max_bounces=max(s.cycles.transparent_max_bounces,16)
for screen in [bpy.context.screen] if bpy.context.screen else []:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_perspective='CAMERA'
def xyz(x,y,z=0):return ((x-19383.1)/1000,(10783-y)/1000,z)
cam=next((o for o in s.objects if o.name=='Current | Transparent walls'),None)
if cam is None:
 data=bpy.data.cameras.new('Current | Transparent walls');data.type='ORTHO';cam=bpy.data.objects.new(data.name,data);s.collection.objects.link(cam)
cam.location=xyz(31500,26000,23);target=Vector(xyz(20600,7900,.75));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=16.5
s.camera=cam;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for camera,file,w,h in [('Current | Transparent walls','09-transparent-walls.png',2000,1800),('Current | Whole property','01-whole-property.png',2400,1500),('Current | Main house','02-main-house.png',2000,1800),('House | Plan.002','03-overhead-plan.png',2200,1400)]:
 s.camera=next(o for o in s.objects if o.name==camera);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=cam;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Applied semi-transparent plaster to',count,'wall objects; house views saved.')
