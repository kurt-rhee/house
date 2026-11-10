import bpy,os
OUT='/Users/kurt/Programs/house/output/blender/overhead-wardrobe'
assert bpy.context.scene.name=='Main Bedroom | Integrated Headboard Design'
bpy.ops.scene.new(type='FULL_COPY');s=bpy.context.scene;s.name='Main Bedroom | Cabinet Open'
front=next(o for o in s.objects if o.name.startswith('Flush wardrobe front 3'))
front.location.x-=.9652
gear=('Rail pivot','Pull-down pivot arm','Hanging rail','Pull-down handle','Grip','Hanging shirt','Clothes hanger','Hanger hook','Shirt placket')
revealed=[]
for o in s.objects:
 if o.name.startswith(gear) and o.location.x>1.545125:
  o.hide_render=False;o.hide_set(False);revealed.append(o.name)
 if o.get('cutaway_hidden'):o.hide_render=True;o.hide_set(True)
assert len(revealed)>20
s['cabinet_pose']='Right central panel slid left over adjacent panel; right hanging bay exposed with raised rail. Track clearances illustrative.'
s.render.filepath=OUT+'/04-integrated-cabinet-open.png'
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=OUT+'/main-bedroom-integrated-open.blend')
bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
print('Saved open-cabinet render:',s.render.filepath)
