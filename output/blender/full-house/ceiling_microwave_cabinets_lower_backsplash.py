"""Extend the upper microwave cabinet to ceiling and lower the stove backsplash."""
import bpy,bmesh,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=24
fid='e1928df0-155f-546e-b491-516387590509';doc['fixtures'][fid]['style']='two_stacked_enclosed_oak_wall_cabinets_bottom_1444mm_top_2438.4mm_ceiling_height_depth_280mm'
for label in doc['room_labels'].values():
 if label['name']=='Microwave + two stacked oak wall cabinets':label['name']='Microwave: stacked oak cabinets to ceiling'
 if label['name'].startswith('Backsplash:'):label['name']='Backsplash: soapstone / stove wall / top 1450 mm'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def oak_uv(o):
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co
   u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],v+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 delta=(2438.4-root['top_mm'])/1000
 for o in root.children:
  if not o.name.startswith('Microwave wall cabinets | 2'):continue
  if 'side' in o.name or 'back' in o.name or 'closed slab door' in o.name:
   oldheight=max(v.co.z for v in o.data.vertices)-min(v.co.z for v in o.data.vertices)
   for v in o.data.vertices:v.co.z*=(oldheight+delta)/oldheight
   o.location.z+=delta/2;o.data.update();oak_uv(o)
  elif 'base or top' in o.name and o.location.z>2:o.location.z+=delta
 root['top_mm']=2438.4;root['source_revision']=24;root['drawing_style']=doc['fixtures'][fid]['style']
 bpy.context.view_layer.update()
 top=max((o.matrix_world@Vector(v)).z for o in root.children if o.type=='MESH' for v in o.bound_box)
 assert abs(top-2.4384)<.00001,top
 slab=next(o for o in scene.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
 outline=[(0,.9365),(3.01565,.9365),(3.01565,1.45),(.974525,1.45),(.974525,.986),(.167675,.986),(.167675,1.45),(0,1.45)]
 N=len(outline);verts=[(u,y,z) for y in [.001,.021] for u,z in outline]
 faces=[tuple(range(N-1,-1,-1)),tuple(N+i for i in range(N))]+[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)]
 old=slab.data;mesh=bpy.data.meshes.new('Lower soapstone slab with west window notch');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 for mat in old.materials:mesh.materials.append(mat)
 slab.data=mesh;slab.parent['top_mm']=1450;slab.parent['source_revision']=24
 scene['source_revision']=24;scene['microwave_wall_cabinet_notes']='Two stacked enclosed white oak cabinets above microwave, bottom 1444 mm, top 2438.4 mm flush to ceiling, width 622.1125 mm and depth 280 mm. Upper cabinet extended; lower cabinet retained.'
 scene['backsplash_notes']='Stove wall only: continuous honed charcoal soapstone slab, 20 mm thick, top 1450 mm throughout, aligned with floating shelf tops. Painted plaster above; west window remains clear. No sink-wall backsplash.'
 if scene==source:scene.name='Full House | Drawing Revision 24'
 print(scene.name,'microwave cabinet top verified at ceiling 2438.4 mm; backsplash lowered to 1450 mm')
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:path.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Fridge and microwave shelves'];tour.render.filepath=str(base/'walkthrough/21-ceiling-height-microwave-cabinets.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 23','revision 24').replace('top 1750 mm and hood section to 1805 mm','top 1450 mm throughout, aligned with floating shelves, painted plaster above').replace('top 2144 mm','top 2438.4 mm at ceiling')
text+='\nRevision 24: microwave upper cabinet extended 294.4 mm to the 2438.4 mm ceiling; lower cabinet retained. Stove-wall soapstone backsplash lowered throughout to 1450 mm, aligned with floating shelves.\n';p.write_text(text)
