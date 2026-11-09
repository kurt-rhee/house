import bpy, bmesh, math
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender'
scene=bpy.context.scene
col=bpy.data.collections['Bathrooms from drawing']
for o in col.objects:
 if o.type=='MESH' and o.name.startswith(('Inset washbasin','Oval toilet seat')) and not o.get('open_basin_fixed'):
  bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();fs=[bm.faces[-2]]
  if o.name.startswith('Oval toilet seat'):fs.append(bm.faces[-1])
  bmesh.ops.delete(bm,geom=fs,context='FACES');bm.to_mesh(o.data);bm.free();o['open_basin_fixed']=True
ceilings=[]
for i,(xx,w) in enumerate([(0,1.59115),(1.69635,1.59115)],1):
 name='Bathroom '+str(i)+' ceiling';o=bpy.data.objects.get(name)
 if not o:
  bpy.ops.mesh.primitive_cube_add(size=1,location=(xx+w/2,-1.177,2.47));o=bpy.context.object;o.name=name;o.dimensions=(w,2.354,.06)
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.data.materials.append(bpy.data.materials['Warm white plaster'])
 ceilings.append(o)
scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.65
scene.render.resolution_x=1500;scene.render.resolution_y=1500;scene.cycles.samples=64
camera=bpy.data.objects['01 | Both bathrooms'];camera.location=(3.8,2.5,10.5);camera.rotation_euler=(Vector((1.64,-1.18,.3))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=4.85
# Keyframe roof and front wall visibility so each camera view is reproducible.
front=[o for o in col.objects if o.name.startswith('Hallway south')]
for frame,cam,file in [(1,'01 | Both bathrooms','01-both-bathrooms.png'),(2,'02 | Bathroom 1','02-bathroom-1.png'),(3,'03 | Bathroom 2','03-bathroom-2.png')]:
 for o in ceilings+front:
  o.hide_render=(frame==1);o.keyframe_insert(data_path='hide_render',frame=frame)
 marker=scene.timeline_markers.get(cam) or scene.timeline_markers.new(cam,frame=frame);marker.camera=bpy.data.objects[cam]
 scene.frame_set(frame);scene.camera=bpy.data.objects[cam];scene.render.filepath=OUT+'/'+file
 bpy.ops.render.render(write_still=True)
scene.frame_start=1;scene.frame_end=3;scene.frame_set(1);scene.camera=camera;scene.render.filepath=OUT+'/01-both-bathrooms.png'
for o in ceilings+front:o.hide_set(True)
scene['render_views']='Frame 1 overview cutaway; frame 2 Bathroom 1; frame 3 Bathroom 2. Camera markers and render visibility keyed.'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/two-bathrooms.blend')
print('Saved final blend and three 1500px renders')
