"""Keep hood top and bottom flat; round only its vertical side edges."""
import bpy,json,shutil
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());rev=doc['revision']+1
backup=base/'blender'/f'before-vertical-only-hood-revision-{rev}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'));tour=bpy.data.scenes['House | Interior walkthrough']
for sc in [source,tour]:
 bpy.context.window.scene=sc;bpy.context.view_layer.update()
 o=next(o for o in sc.objects if o.name.startswith('Architectural hood | rectangular rounded plaster shell'))
 attr=o.data.attributes.get('bevel_weight_edge') or o.data.attributes.new('bevel_weight_edge','FLOAT','EDGE')
 count=0
 for e in o.data.edges:
  a,b=[o.matrix_world@o.data.vertices[i].co for i in e.vertices]
  vertical=abs(a.x-b.x)<1e-6 and abs(a.y-b.y)<1e-6 and abs(a.z-b.z)>.5
  attr.data[e.index].value=1.0 if vertical else 0.0;count+=int(vertical)
 assert count==4
 bevel=next(m for m in o.modifiers if m.type=='BEVEL')
 enums=[i.identifier for i in bevel.bl_rna.properties['limit_method'].enum_items]
 assert 'WEIGHT' in enums
 bevel.limit_method='WEIGHT';bevel.width=.15;bevel.segments=16;bevel.name='Rounded vertical sides only | flat top and bottom'
 bevel.harden_normals=True
 o['profile']='Flat horizontal top and bottom; only vertical side corners rounded 150 mm'
 o['source_revision']=rev
 o.parent['source_revision']=rev;o.parent['drawing_style']='rectangular_plaster_hood_vertical_side_rounding_150mm_flat_top_bottom'
 sc['source_revision']=rev;sc['hood_notes']='1250 mm wide, 150 mm rounding on vertical side edges only; flat top and bottom; range and backsplash centered'
 print(sc.name,'rounded vertical edges',count)
doc['revision']=rev
h=doc['fixtures']['cc99b809-cb08-51b4-a631-7c1eae3d9db0']
h['style']='rectangular_plaster_hood_150mm_vertical_side_edges_only_flat_top_bottom'
h['material']='Warm ivory mineral plaster, rounded vertical sides, flat top and bottom'
for l in doc['room_labels'].values():
 if l['name'].startswith('Rounded rectangular hood:'):l['name']='Plaster hood: rounded vertical sides / flat top and bottom'
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {rev}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {rev}: corrected hood to round only the four vertical side edges (150 mm radius), leaving horizontal top and bottom edges flat. Width and centered range/backsplash retained.\n')
