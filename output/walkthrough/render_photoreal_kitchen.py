import bpy,time
from pathlib import Path
out=Path('/Users/kurt/Programs/house/output/walkthrough')
s=bpy.data.scenes['House | Interior walkthrough'];bpy.context.window.scene=s;s.frame_set(1);s.render.engine='CYCLES'
p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.refresh_devices()
for d in p.devices:d.use=(d.type=='METAL')
s.cycles.device='GPU';s.cycles.samples=144;s.cycles.adaptive_threshold=.025;s.cycles.use_denoising=True
s.render.resolution_x=1800;s.render.resolution_y=1300;s.render.resolution_percentage=100
for camera,file in [('Photo | Sink and floating shelves','07-photoreal-kitchen.png'),('Photo | Fridge and microwave shelves','08-photoreal-fridge-and-shelves.png'),('Photo | Stove and floating prep shelf','09-photoreal-stove-and-shelf.png')]:
 print('RENDER START',file,time.strftime('%H:%M:%S'),flush=True)
 s.camera=bpy.data.objects[camera];s.render.filepath=str(out/file);bpy.ops.render.render(scene=s.name,write_still=True)
 print('RENDER SAVED',file,time.strftime('%H:%M:%S'),flush=True)
print('All photographic kitchen views complete.',flush=True)
