import bpy,json,math
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house');out=base/'sites/house-walkthrough/public/assets'
s=bpy.data.scenes['House | Interior walkthrough'];bpy.context.window.scene=s;s.frame_set(1)
# Export only the current tour, evaluated modifiers, embedded photographed textures, and animation rigs.
for o in bpy.context.view_layer.objects:o.select_set(False)
objects=[o for o in s.objects if o.type in {'MESH','CURVE','EMPTY'} and not o.hide_render]
for o in objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'house.glb'),export_format='GLB',use_active_scene=True,use_selection=True,export_cameras=False,export_lights=False,export_extras=True,export_apply=True,export_animations=True,export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True)
# Lighting is translated separately to preserve named lights without invisible camera fill geometry.
lights=[]
for o in s.objects:
 if o.type!='LIGHT' or o.hide_render:continue
 d=o.data;direction=o.matrix_world.to_quaternion()@Vector((0,0,-1));loc=o.matrix_world.translation
 lights.append(dict(name=o.name,type=d.type,position=[loc.x,loc.z,-loc.y],direction=[direction.x,direction.z,-direction.y],energy=d.energy,color=list(d.color),size=getattr(d,'size',.2),size_y=getattr(d,'size_y',.2)))
(out/'lighting.json').write_text(json.dumps({'revision':36,'lights':lights},indent=2))
print('Revision 36 model and lighting exported',flush=True)
# Blender-rendered 360 views provide full photographic quality on every device.
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=80;s.cycles.adaptive_threshold=.035;s.cycles.use_denoising=True
s.render.resolution_x=4096;s.render.resolution_y=2048;s.render.resolution_percentage=100;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=94
camdata=bpy.data.cameras.new('Web | Photographic panorama');camdata.type='PANO';camdata.panorama_type='EQUIRECTANGULAR'
cam=bpy.data.objects.new(camdata.name,camdata);s.collection.objects.link(cam);s.camera=cam
views=[('kitchen',(.30,5.98,1.62)),('fridge',(-1.12,7.65,1.65)),('dining',(3.7,6.85,1.65))]
for name,loc in views:
 cam.location=loc;cam.rotation_euler=(math.pi/2,0,0);s.render.filepath=str(out/f'panorama-{name}.jpg');print('Rendering panorama',name,flush=True);bpy.ops.render.render(scene=s.name,write_still=True)
print('Photographic panoramas finished',flush=True)
