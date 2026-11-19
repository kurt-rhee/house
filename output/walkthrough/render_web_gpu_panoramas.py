import bpy,math,time,sys
from pathlib import Path
s=bpy.data.scenes['House | Interior walkthrough'];bpy.context.window.scene=s;s.frame_set(1);s.render.engine='CYCLES'
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.refresh_devices()
for d in p.devices:d.use=(d.type=='METAL')
s.cycles.device='GPU';s.cycles.samples=80;s.cycles.adaptive_threshold=.035;s.cycles.use_denoising=True
s.render.resolution_x=4096;s.render.resolution_y=2048;s.render.resolution_percentage=100;s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=94
camdata=bpy.data.cameras.new('Web | GPU panorama');camdata.type='PANO';camdata.panorama_type='EQUIRECTANGULAR';cam=bpy.data.objects.new(camdata.name,camdata);s.collection.objects.link(cam);s.camera=cam
selected=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
for name,loc in [('kitchen',(.30,5.98,1.62)),('fridge',(-1.12,7.65,1.65)),('dining',(3.7,6.85,1.65))]:
 if selected and name not in selected:continue
 cam.location=loc;cam.rotation_euler=(math.pi/2,0,0);s.render.filepath='/Users/kurt/Programs/house/sites/house-walkthrough/public/assets/panorama-'+name+'.jpg';print('GPU rendering',name,time.strftime('%H:%M:%S'),flush=True);bpy.ops.render.render(scene=s.name,write_still=True);print('GPU saved',name,time.strftime('%H:%M:%S'),flush=True)
