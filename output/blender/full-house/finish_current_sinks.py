import bpy,bmesh
s=bpy.context.scene
for o in s.objects:
 if o.name.startswith('Inset washbasin'):
  bm=bmesh.new();bm.from_mesh(o.data)
  for f in list(bm.faces):
   if len(f.verts)>32 and all(abs(v.co.z-.8)<.00001 for v in f.verts):bm.faces.remove(f)
  bm.to_mesh(o.data);bm.free();o.data.update()
bpy.context.view_layer.update()
# Cut the north kitchen countertop at its saved sink footprint.
x=(19174.6-19383.1)/1000;y=(10783-2605.6)/1000
bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,.88));c=bpy.context.object;c.dimensions=(.7282,.4542,.30);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for o in list(s.objects):
 if o.name.startswith('Quartz countertop') and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a':
  mod=o.modifiers.new('Kitchen sink opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=c;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(c,do_unlink=True)
main=s.camera
s.cycles.samples=24
for camera,file,w,h in [(next(o for o in s.objects if o.name.startswith('Current | Whole property')),'01-whole-property.png',2400,1500),(main,'02-main-house.png',2000,1800)]:
 s.camera=camera;s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath='/Users/kurt/Programs/house/output/blender/full-house/'+file;bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath='/Users/kurt/Programs/house/output/blender/full-house/full-house.blend')
print('Corrected basin openings and saved both full-house renders.')
