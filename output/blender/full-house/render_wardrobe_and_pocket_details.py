import bpy
from pathlib import Path
from mathutils import Vector
s=bpy.context.scene;base=Path('/Users/kurt/Programs/house/output/blender/full-house')
def xyz(x,y,z=0):return ((x-19383.1)/1000,(10783-y)/1000,z)
for o in s.objects:
 if o.name=='Pocket door concealed leaf':o.hide_render=True
 if o.get('laundry_supply_cabinet'):o['access']='Food pantry with three internal pull-outs; laundry pocket door removes the former swing obstruction'
def render(name,file,w,h,hidewalls=()):
 hidden=[]
 for o in s.objects:
  if o.get('source_wall_id') in hidewalls:hidden.append((o,o.hide_render));o.hide_render=True
 s.camera=next(o for o in s.objects if o.name==name);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
 for o,v in hidden:o.hide_render=v
cam=next(o for o in s.objects if o.name=='Current | Main bedroom wardrobe');cam.location=xyz(19000,14350,5.3);target=Vector(xyz(17600,11100,1.0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=4.9
render('Current | Main bedroom wardrobe','07-main-bedroom-wardrobe.png',1600,1600,['33407ad6-ccf9-441a-850c-218fe8112e4c','95a31876-8718-4029-aee7-31665058e3d2'])
render('Current | Laundry','05-laundry.png',1600,1400,['970ed9db-d98e-400f-8588-d7dbb8c6386f','743fa984-048d-48a9-923a-a99198a7c60e','b88afdbc-83c7-436b-a52b-374da2f48e67'])
render('Current | Main house','02-main-house.png',2000,1800)
s.camera=next(o for o in s.objects if o.name=='Current | Main house');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Updated bedroom, laundry and main-house views saved.')
