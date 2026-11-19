import bpy
from pathlib import Path
s=bpy.data.scenes.new('Web soapstone bake');bpy.context.window.scene=s;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1
bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object
mat=bpy.data.materials['Kitchen | Honed charcoal soapstone'].copy();plane.data.materials.append(mat)
p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL');source=p.inputs['Base Color'].links[0].from_socket
em=mat.node_tree.nodes.new('ShaderNodeEmission');mat.node_tree.links.new(source,em.inputs['Color']);mat.node_tree.links.new(em.outputs[0],output.inputs['Surface'])
im=bpy.data.images.new('Web soapstone texture',width=2048,height=2048);im.colorspace_settings.name='sRGB';tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;mat.node_tree.nodes.active=tex
bpy.context.view_layer.objects.active=plane;plane.select_set(True);bpy.ops.object.bake(type='EMIT')
im.filepath_raw='/Users/kurt/Programs/house/sites/house-walkthrough/public/assets/soapstone.jpg';im.file_format='JPEG';im.save();print('Soapstone material baked',flush=True)
