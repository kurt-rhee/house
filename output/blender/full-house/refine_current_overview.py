import bpy
from mathutils import Vector
s=bpy.context.scene
assert s['source_revision']==25
for o in list(s.objects):
 if o.name.startswith(('Oak mirror frame','Vanity mirror','Vanity light bar')):o.hide_render=True
 if o.name.startswith('Floating oak vanity'):
  root=o.parent
  bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=1,depth=.28)
  cutter=bpy.context.object;cutter.parent=root;cutter.location=(.6096/2,-.4572/2,.76);cutter.scale=(.212,.147,1)
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  mod=o.modifiers.new('Inset basin recess','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
  bpy.data.objects.remove(cutter,do_unlink=True)
c=s.camera;c.location=Vector(((20750-19383.1)/1000,(10783-7700)/1000,30));target=Vector((c.location.x,c.location.y,0));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath='/Users/kurt/Programs/house/output/blender/full-house/02-main-house.png'
bpy.ops.wm.save_as_mainfile(filepath='/Users/kurt/Programs/house/output/blender/full-house/full-house.blend')
bpy.ops.render.render(write_still=True)
print('Main house plan render finished')
