import bpy,math,json,time
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house');out=base/'sites/house-walkthrough/public/assets'
s=bpy.data.scenes['House | Interior walkthrough'];bpy.context.window.scene=s;s.frame_set(1)
for o in s.objects:o.select_set(False)
meshes=[]
for o in s.objects:
 if o.type!='MESH' or o.hide_render:continue
 bb=[o.matrix_world@Vector(c) for c in o.bound_box]
 lo=[min(v[i] for v in bb) for i in range(3)];hi=[max(v[i] for v in bb) for i in range(3)]
 # Only permanent indoor surfaces. Moving glass and the blind retain dynamic materials.
 if lo[0]<-4.5 or hi[0]>7.0 or lo[1]<-2.7 or hi[1]>9.0:continue
 if any(x in o.name.lower() for x in ['glaz','shade | linen','shade | slim','awning sash','lantern |','induction | printed']):continue
 if not o.data.polygons:continue
 if any(m and (('glass' in m.name.lower()) or ('glazing' in m.name.lower())) for m in o.data.materials):continue
 o.data=o.data.copy();
 if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
 layer=o.data.uv_layers.get('Lightmap') or o.data.uv_layers.new(name='Lightmap');o.data.uv_layers.active=layer
 o['baked_lighting']=True;o.select_set(True);meshes.append(o)
print('JOINING STATIC SURFACES',len(meshes),time.strftime('%H:%M:%S'),flush=True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.join()
joined=bpy.context.object;joined.name='House | Baked architectural surfaces';joined['baked_lighting']=True
meshes=[joined]
print('UNWRAPPING',len(meshes),'meshes',time.strftime('%H:%M:%S'),flush=True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,area_weight=1);bpy.ops.object.mode_set(mode='OBJECT')
print('UV FINISHED',time.strftime('%H:%M:%S'),flush=True)
im=bpy.data.images.new('Web | Indirect and direct irradiance',width=4096,height=4096,float_buffer=True);im.colorspace_settings.name='Linear Rec.709'
seen={};normal_links=[];color_defaults=[]
for o in meshes:
 for i,slot in enumerate(o.material_slots):
  if not slot.material:continue
  orig=slot.material
  if orig.name not in seen:
   mat=orig.copy();mat.name=orig.name+' | web lightmap';seen[orig.name]=mat
   if not mat.use_nodes:mat.use_nodes=True
   for n in mat.node_tree.nodes:
    if n.type=='BSDF_PRINCIPLED':
     socket=n.inputs['Base Color'];color_defaults.append((socket,tuple(socket.default_value)))
     for link in list(socket.links):normal_links.append((mat.node_tree,link.from_socket,link.to_socket));mat.node_tree.links.remove(link)
     name=mat.name.lower()
     if 'oak' in name:socket.default_value=(.43,.30,.18,1)
     elif 'soapstone' in name:socket.default_value=(.065,.09,.075,1)
     elif 'warm greige' in name:socket.default_value=(.34,.30,.24,1)
     elif any(x in name for x in ['plaster','wall','ceiling','ceramic','fireclay']):socket.default_value=(.76,.74,.68,1)
     for link in list(n.inputs['Normal'].links):
      normal_links.append((mat.node_tree,link.from_socket,link.to_socket));mat.node_tree.links.remove(link)
   tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;mat.node_tree.nodes.active=tex
  o.material_slots[i].material=seen[orig.name]
 # Source UV remains the texture coordinate system for the surface material.
 if len(o.data.uv_layers)>1:o.data.uv_layers[0].active_render=True
s.render.engine='CYCLES';p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.refresh_devices()
for d in p.devices:d.use=(d.type=='METAL')
s.cycles.device='GPU';s.cycles.samples=48;s.cycles.use_denoising=True;s.cycles.max_bounces=7
s.render.bake.use_pass_direct=True;s.render.bake.use_pass_indirect=True;s.render.bake.use_pass_color=False;s.render.bake.margin=8;s.render.bake.use_clear=True
print('BAKING LIGHT',time.strftime('%H:%M:%S'),flush=True)
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'DIRECT','INDIRECT'},uv_layer='Lightmap')
im.scale(2048,2048)
s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';s.render.image_settings.exr_codec='PIZ'
im.save_render(str(out/'lighting.exr'),scene=s)
for socket,color in color_defaults:socket.default_value=color
for tree,src,dst in normal_links:tree.links.new(src,dst)
print('BAKE FINISHED',time.strftime('%H:%M:%S'),flush=True)
# Preserve independent kitchen controls using the existing current exporter tagging.
rigs=[(next(o for o in s.objects if o.name.startswith('Operation | Sink awning')),'window'),(next(o for o in s.objects if o.name.startswith('Concealed shade | linen drop')),'blind'),(next(o for o in s.objects if o.name.startswith('Concealed shade | slim weighted')),'hem')]
def pose(o):
 q=o.rotation_euler.to_quaternion();return dict(position=[o.location.x,o.location.z,-o.location.y],quaternion=[q.x,q.z,-q.y,q.w],scale=[o.scale.x,o.scale.z,o.scale.y])
for o,role in rigs:
 o['tour_role']=role;s.frame_set(1);o['tour_closed']=json.dumps(pose(o));s.frame_set(60 if role=='window' else 100);o['tour_open']=json.dumps(pose(o))
s.frame_set(1)
for o in s.objects:o.select_set(o.type in {'MESH','CURVE','EMPTY'} and not o.hide_render)
props=bpy.ops.export_scene.gltf.get_rna_type().properties
kw=dict(filepath=str(out/'house-lit.glb'),export_format='GLB',use_active_scene=True,use_selection=True,export_cameras=False,export_lights=False,export_extras=True,export_apply=True,export_animations=False)
if 'export_all_uvs' in props:kw['export_all_uvs']=True
bpy.ops.export_scene.gltf(**kw)
print('LIGHTMAPPED MODEL EXPORTED',time.strftime('%H:%M:%S'),flush=True)
