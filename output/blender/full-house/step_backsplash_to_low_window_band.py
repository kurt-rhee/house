"""Retain the stove splash and continue a low soapstone band under both windows."""
import bpy,bmesh,json
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=26
for label in doc['room_labels'].values():
 if label['name'].startswith('Backsplash:'):label['name']='Soapstone: stove splash + low band to window sills'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
stone=bpy.data.materials['Kitchen | Honed charcoal soapstone']
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 slab=next(o for o in scene.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
 # At the window's stove-side jamb, step down to a 53.5 mm upstand.
 outline=[(0,.9325),(3.01565,.9325),(3.01565,1.45),(.974525,1.45),(.974525,.986),(0,.986)]
 N=len(outline);verts=[(u,y,z) for y in [.001,.021] for u,z in outline]
 faces=[tuple(range(N-1,-1,-1)),tuple(N+i for i in range(N))]+[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)]
 mesh=bpy.data.meshes.new('Stove splash stepping down to window sill band');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();mesh.materials.append(stone);slab.data=mesh
 slab.parent['source_revision']=26;slab.parent['low_band_top_mm']=986;slab.parent['low_band_height_mm']=53.5;slab.parent['location']='Stove splash steps down at west window; low band continues around north/sink counter'
 for o in list(scene.objects):
  if o.name.startswith('Backsplash | Low sink-wall soapstone band'):bpy.data.objects.remove(o,do_unlink=True)
 bpy.ops.mesh.primitive_cube_add(size=1);band=bpy.context.object;band.name='Backsplash | Low sink-wall soapstone band'
 band.location=((-2.0251+.9731)/2,8.4839,(.9325+.986)/2);band.dimensions=(2.9982,.020,.0535)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);band.data.materials.append(stone)
 b=band.modifiers.new('Eased soapstone edges','BEVEL');b.width=.0012;b.segments=3;band.modifiers.new('Weighted slab normals','WEIGHTED_NORMAL')
 band['source_revision']=26;band['top_mm']=986;band['height_mm']=53.5;band['finish']='Honed soapstone, matches countertops and stove backsplash'
 scene['source_revision']=26;scene['backsplash_notes']='Honed soapstone: stove/prep splash top 1450 mm ends at west window. Beyond that, a continuous 53.5 mm low upstand wraps corner and follows entire sink countertop to right wall. Top 986 mm, immediately beneath window sill/trim. 20 mm thickness; painted plaster above low band.'
 if scene==source:scene.name='Full House | Drawing Revision 26'
 print(scene.name,'stove splash retained; low sill-height soapstone band continuous around corner and sink run')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Sink and floating shelves'];tour.render.filepath=str(base/'walkthrough/24-low-window-sill-soapstone-band.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text();text=text.replace('revision 25','revision 26');text+='\nRevision 26: stove splash steps down at west window to a continuous low 53.5 mm soapstone band (top 986 mm beneath sill/trim), running around corner and across entire sink countertop to right wall. Stove and prep splash top remains 1450 mm.\n';p.write_text(text)
