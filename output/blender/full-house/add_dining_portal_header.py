"""Connect the two dining opening piers with a flush plaster header."""
import bpy,bmesh,json,shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());rev=doc['revision']+1
assert rev==51
backup=base/'blender'/f'before-dining-portal-revision-{rev}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'));tour=bpy.data.scenes['House | Interior walkthrough']
for sc in [source,tour]:
 bpy.context.window.scene=sc;bpy.context.view_layer.update()
 left=next(o for o in sc.objects if o.type=='MESH' and o.get('source_wall_id')=='03c0d967-f904-48cc-b581-56eb4b700823')
 right=next(o for o in sc.objects if o.type=='MESH' and o.get('source_wall_id')=='3a1045bf-ee6c-4c4c-9b53-7398fb585b9c')
 def bounds(o):
  b=[o.matrix_world@Vector(c) for c in o.bound_box];return [(min(v[i] for v in b),max(v[i] for v in b)) for i in range(3)]
 a,b=bounds(left),bounds(right)
 x0=a[0][1]-.005;x1=b[0][0]+.005;y0=a[1][0];y1=a[1][1];z1=max(a[2][1],b[2][1]);z0=z1-.3048
 verts=[(x,y,z) for z in [z0,z1] for y in [y0,y1] for x in [x0,x1]]
 faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
 mesh=bpy.data.meshes.new('Dining portal | connecting plaster header mesh');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new('Dining portal | flush plaster header',mesh);sc.collection.objects.link(o)
 for m in left.data.materials:mesh.materials.append(m)
 bevel=o.modifiers.new('Fine plaster edge','BEVEL');bevel.width=.001;bevel.segments=2
 o.modifiers.new('Flat plaster normals','WEIGHTED_NORMAL')
 o['design_role']='Dining living portal: left pier, overhead header, right pier'
 o['source_revision']=rev;o['clear_height_mm']=round(z0*1000,1);o['header_drop_mm']=304.8
 o['source_wall_ids']=['03c0d967-f904-48cc-b581-56eb4b700823','3a1045bf-ee6c-4c4c-9b53-7398fb585b9c']
 sc['source_revision']=rev;sc['dining_portal_note']='Flush plaster header connects existing piers: 304.8 mm drop, 2133.6 mm clear opening'
 print(sc.name,'header',x0,x1,y0,y1,z0,z1,flush=True)
doc['revision']=rev
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {rev}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {rev}: added flush plaster header across existing dining/living opening piers, 304.8 mm deep below ceiling, 2133.6 mm clear height. Forms a continuous three-sided rectangular portal. No floor plan footprint change.\n')
