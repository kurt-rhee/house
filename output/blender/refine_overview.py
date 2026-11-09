import bpy
scene=bpy.context.scene
scene.frame_set(1);scene.camera=bpy.data.objects['01 | Both bathrooms'];scene.camera.data.ortho_scale=5.5
# Remove mirror backs in cutaway only, so vanities remain visible.
for o in bpy.data.collections['Bathrooms from drawing'].objects:
 if o.name.startswith(('Oak mirror frame','Vanity mirror','Vanity light bar')):
  for frame in [1,2,3]:
   o.hide_render=frame==1;o.keyframe_insert(data_path='hide_render',frame=frame)
scene.frame_set(1)
scene.render.filepath='/Users/kurt/Programs/house/output/blender/01-both-bathrooms.png'
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='/Users/kurt/Programs/house/output/blender/two-bathrooms.blend')
print('Overview framing finished')
