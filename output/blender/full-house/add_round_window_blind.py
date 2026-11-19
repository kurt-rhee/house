"""Fitted pleated linen blind for the circular kitchen window, independently operable."""
import bpy,bmesh,math,shutil
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');assets=base.parent/'sites/house-walkthrough/public/assets'
backup=base/'blender/before-round-window-blind';backup.mkdir(exist_ok=True)
for p in [base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'));tour=bpy.data.scenes['House | Interior walkthrough']
export_objects=[]
for sc in [source,tour]:
 bpy.context.window.scene=sc;sc.frame_set(1)
 assert not any(o.name.startswith('Operation | Round window fitted blind') for o in sc.objects)
 root=bpy.data.objects.new('Operation | Round window fitted blind',None);sc.collection.objects.link(root);root.location=(-2.0075,7.83,1.7565)
 root['source_window_id']='c0d5528e-44b1-507c-8696-229d74db36a0';root['design_role']='Fitted circular pleated linen blind';root['clear_diameter_mm']=406
 root['operation']='Independent circular concertina blind; frame 1 open, 150 closed, 180 open'
 segments=128;r=.203;closed=[(.0002,0,0)]
 for i in range(segments+1):
  a=2*math.pi*i/segments;closed.append((.0016*(1 if i%2==0 else -1),r*math.cos(a),r*math.sin(a)))
 opened=[(x,u*.06,-.194+(v+r)*.025) for x,u,v in closed]
 faces=[(0,i+1,i+2) for i in range(segments)]
 mesh=bpy.data.meshes.new('Round blind | fine radial linen pleats');mesh.from_pydata(opened,[],faces);mesh.update()
 ob=bpy.data.objects.new('Round window blind | pleated linen fan',mesh);sc.collection.objects.link(ob);ob.parent=root
 ob['tour_role']='round_blind';ob['source_window_id']=root['source_window_id'];ob['fitted_diameter_mm']=406
 original=next(o for o in sc.objects if o.name.startswith('Concealed shade | linen drop'))
 mat=original.data.materials[0].copy();mat.name='Round blind | warm natural linen'
 p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for link in list(p.inputs['Base Color'].links):mat.node_tree.links.remove(link)
 p.inputs['Base Color'].default_value=(.72,.675,.58,1);p.inputs['Roughness'].default_value=.94
 mesh.materials.append(mat)
 ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='Closed')
 for v,co in zip(key.data,closed):v.co=co
 key.value=0;key.keyframe_insert(data_path='value',frame=1);key.keyframe_insert(data_path='value',frame=120)
 key.value=1;key.keyframe_insert(data_path='value',frame=150)
 key.value=0;key.keyframe_insert(data_path='value',frame=180)
 # A slim guide is housed within the existing bronze window surround.
 verts=[];faces=[];around=128;sides=8
 for i in range(around):
  a=2*math.pi*i/around
  for j in range(sides):
   b=2*math.pi*j/sides;radius=.207+.0018*math.cos(b)
   verts.append((.003+.0018*math.sin(b),radius*math.cos(a),radius*math.sin(a)))
 for i in range(around):
  for j in range(sides):faces.append((i*sides+j,((i+1)%around)*sides+j,((i+1)%around)*sides+(j+1)%sides,i*sides+(j+1)%sides))
 m=bpy.data.meshes.new('Round blind | bronze guide');m.from_pydata(verts,[],faces);m.update()
 bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(m);bm.free()
 guide=bpy.data.objects.new('Round window blind | slim bronze guide',m);sc.collection.objects.link(guide);guide.parent=root
 m.materials.append(bpy.data.materials['Window | Satin warm bronze'])
 for f in m.polygons:f.use_smooth=True
 sc.frame_end=max(sc.frame_end,180);sc.frame_set(1);sc['round_window_blind']='406 mm fitted warm linen pleated blind; independently animated'
 sc.timeline_markers.new('ROUND BLIND | closed',frame=150)
 if sc==tour:export_objects=[root,ob,guide]
 print(sc.name,'round blind added',flush=True)
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
for o in bpy.context.view_layer.objects:o.select_set(False)
for o in export_objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(assets/'round-blind.glb'),export_format='GLB',use_active_scene=True,use_selection=True,export_cameras=False,export_lights=False,export_extras=True,export_animations=False,export_morph=True)
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+'\nAdded fitted 406 mm circular pleated linen blind with slim bronze guide to the small stove-side round window. Independent control; frame 150 closed, frame 1/180 open. Additive web asset round-blind.glb preserves the baked main-house model and lighting.\n')
print('ROUND BLIND SAVED AND EXPORTED',flush=True)
