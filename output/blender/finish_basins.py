import bpy
s=bpy.context.scene;col=bpy.data.collections['Bathrooms from drawing']
for cabinet in [o for o in list(col.objects) if o.name.startswith('Floating oak vanity')]:
 root=cabinet.parent
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=1,depth=.28)
 cutter=bpy.context.object;cutter.name='Sink recess cutter';cutter.parent=root;cutter.location=(.6096/2,-.4572/2,.76);cutter.scale=(.212,.147,1)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=cabinet.modifiers.new('Recess for inset washbasin','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
 bpy.context.view_layer.objects.active=cabinet
 bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
s.cycles.samples=16
for frame,cam,file in [(1,'01 | Both bathrooms','01-both-bathrooms.png'),(2,'02 | Bathroom 1','02-bathroom-1.png'),(3,'03 | Bathroom 2','03-bathroom-2.png')]:
 s.frame_set(frame);s.camera=bpy.data.objects[cam];s.render.filepath='/Users/kurt/Programs/house/output/blender/'+file;bpy.ops.render.render(write_still=True)
s.frame_set(1);s.camera=bpy.data.objects['01 | Both bathrooms'];s.render.filepath='/Users/kurt/Programs/house/output/blender/01-both-bathrooms.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/kurt/Programs/house/output/blender/two-bathrooms.blend')
print('Basin recesses corrected; all renders saved')
