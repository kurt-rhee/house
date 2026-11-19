"""Keep backsplash on the stove wall only; replace tile with a continuous soapstone slab."""
import bpy,bmesh,json,uuid,math
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=21
lid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/backsplash-finish-note'))
doc['room_labels'][lid]['name']='Backsplash: honed soapstone / stove wall only'
(base/'floor-plan.house.json').write_text(json.dumps(doc,indent=2)+'\n')
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
stone=bpy.data.materials['Kitchen | Honed charcoal soapstone']
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 old=[o for o in scene.objects if o.type=='EMPTY' and o.name.startswith('Backsplash |')]
 for root in old:
  for o in list(root.children):bpy.data.objects.remove(o,do_unlink=True)
  bpy.data.objects.remove(root,do_unlink=True)
 col=bpy.data.collections.new('Kitchen | Stove-wall soapstone backsplash');scene.collection.children.link(col)
 root=bpy.data.objects.new('Backsplash | Stove wall soapstone slab',None);col.objects.link(root);root.location=(-2.0251,8.4949,0);root.rotation_euler.z=-math.pi/2
 root['source_revision']=21;root['finish']='Honed charcoal soapstone matching countertops; continuous slab, no tile or grout';root['thickness_mm']=20;root['location']='Stove wall only; sink wall and microwave wall painted plaster'
 # Slab outline incorporates the west window notch and the taller section beneath the hood.
 outline=[(0,.9365),(3.01565,.9365),(3.01565,1.75),(2.063825,1.75),(2.063825,1.805),(1.301825,1.805),(1.301825,1.75),(.974525,1.75),(.974525,.986),(.167675,.986),(.167675,1.75),(0,1.75)]
 N=len(outline);verts=[(u,y,z) for y in [.001,.021] for u,z in outline]
 faces=[tuple(range(N-1,-1,-1)),tuple(N+i for i in range(N))]
 faces.extend((i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N))
 data=bpy.data.meshes.new('Continuous soapstone slab with window notch');data.from_pydata(verts,[],faces);data.update()
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free()
 ob=bpy.data.objects.new('Backsplash | Honed soapstone slab',data);col.objects.link(ob);ob.parent=root;data.materials.append(stone)
 b=ob.modifiers.new('Eased soapstone edges','BEVEL');b.width=.0012;b.segments=3;ob.modifiers.new('Weighted slab normals','WEIGHTED_NORMAL')
 scene['source_revision']=21;scene['backsplash_notes']='Honed charcoal soapstone slab on stove wall only, matching countertops; 20 mm thick, top 1750 mm with hood section to 1805 mm. West window remains clear. Sink/north and microwave walls have no backsplash.'
 assert len([o for o in scene.objects if o.type=='EMPTY' and o.name.startswith('Backsplash |')])==1
 assert not any(o.get('backsplash_tile') for o in scene.objects)
 if scene==source:scene.name='Full House | Drawing Revision 21'
 print(scene.name,'stove-wall soapstone only; all tile, grout, sink-wall and microwave-wall backsplash removed.')
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/16-stove-wall-soapstone.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
