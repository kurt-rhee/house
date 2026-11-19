import bpy,json
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house');out=base/'sites/house-walkthrough/public/assets'
s=bpy.data.scenes['House | Interior walkthrough'];bpy.context.window.scene=s;s.frame_set(1)
rigs=[(next(o for o in s.objects if o.name.startswith('Operation | Sink awning')),'window'),(next(o for o in s.objects if o.name.startswith('Concealed shade | linen drop')),'blind'),(next(o for o in s.objects if o.name.startswith('Concealed shade | slim weighted')),'hem')]
def pose(o):
 q=o.rotation_euler.to_quaternion();return dict(position=[o.location.x,o.location.z,-o.location.y],quaternion=[q.x,q.z,-q.y,q.w],scale=[o.scale.x,o.scale.z,o.scale.y])
for o,role in rigs:
 o['tour_role']=role;s.frame_set(1);o['tour_closed']=json.dumps(pose(o));s.frame_set(60 if role=='window' else 100);o['tour_open']=json.dumps(pose(o))
s.frame_set(1)
for o in bpy.context.view_layer.objects:o.select_set(False)
for o in s.objects:
 if o.type in {'MESH','CURVE','EMPTY'} and not o.hide_render:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'house.glb'),export_format='GLB',use_active_scene=True,use_selection=True,export_cameras=False,export_lights=False,export_extras=True,export_apply=True,export_animations=False)
# Export genuine material images for web surface detail.
for name,file in [('white_oak_veneer_diff_2k.jpg','oak.jpg'),('white_oak_veneer_rough_2k.jpg','oak-rough.jpg'),('white_oak_veneer_nor_gl_2k.jpg','oak-normal.jpg')]:
 im=bpy.data.images.get(name)
 if im and im.packed_file:(out/file).write_bytes(im.packed_file.data)
(out/'tour.json').write_text(json.dumps(dict(revision=s.get('source_revision',50),window='Top-hinged awning',blind='Concealed linen roller blind')))
print('EXPORTED CURRENT TOUR',flush=True)
# Bake the warm backsplash procedural color, without changing the source material.
bake=bpy.data.scenes.new('Web material bake');bpy.context.window.scene=bake;bake.render.engine='CYCLES';bake.cycles.samples=1
bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object
mat=bpy.data.materials['Backsplash | Warm greige honed stone'].copy();plane.data.materials.append(mat)
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL');src=p.inputs['Base Color'].links[0].from_socket
em=mat.node_tree.nodes.new('ShaderNodeEmission');mat.node_tree.links.new(src,em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],output.inputs['Surface'])
im=bpy.data.images.new('Warm stone baked',width=2048,height=2048);im.colorspace_settings.name='sRGB';tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;mat.node_tree.nodes.active=tex
bpy.context.view_layer.objects.active=plane;plane.select_set(True);bpy.ops.object.bake(type='EMIT')
im.filepath_raw=str(out/'warm-stone.jpg');im.file_format='JPEG';im.save()
print('FINISHED EXPORT AND MATERIAL BAKE',flush=True)
