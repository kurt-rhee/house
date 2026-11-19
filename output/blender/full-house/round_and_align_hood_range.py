"""Round rectangular hood more, align stone width and range, refit base joinery."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());rev=doc['revision']+1
assert rev==49
backup=base/'blender'/f'before-aligned-rounded-hood-revision-{rev}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'));tour=bpy.data.scenes['House | Interior walkthrough']
sid='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a';cid='c08078d4-006c-4eba-8032-0bf18c432cec'
cy=6.712075
for sc in [source,tour]:
 bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
 stove=next(o for o in sc.objects if o.type=='EMPTY' and o.get('source_fixture_id')==sid)
 hood=next(o for o in sc.objects if o.name.startswith('Kitchen | Ceiling-height integrated hood'))
 shell=next(o for o in sc.objects if o.name.startswith('Architectural hood | rectangular rounded plaster shell'))
 hood_world=hood.matrix_world.copy()
 m=stove.matrix_world.copy();m.translation.y-=.1;stove.matrix_world=m
 bpy.context.view_layer.update();hood.matrix_world=hood_world;bpy.context.view_layer.update()
 stove['source_revision']=rev
 for mod in shell.modifiers:
  if mod.type=='BEVEL':mod.width=.15;mod.segments=16;mod.name='Broad 150 mm rounded plaster corners'
 shell['profile']='Rectangular plaster hood with broad 150 mm rounded corners';shell['source_revision']=rev
 shell['corner_radius_mm']=150;shell['offset_left_mm']=0
 hood['source_revision']=rev;hood['drawing_style']='rectangular_plaster_hood_broad_150mm_rounded_corners_centered_range_1250mm'
 slab=next(o for o in sc.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
 inv=slab.matrix_world.inverted()
 for v in slab.data.vertices:
  w=slab.matrix_world@v.co;w.y=cy+(w.y-6.812075)*(1.25/1.2);v.co=inv@w
 slab.data.update();slab['width_mm']=1250;slab['source_revision']=rev;slab.parent['source_revision']=rev
 # Stretch each cabinet segment around the shifted range opening, including doors, grips and end panels.
 counter=next(o for o in sc.objects if o.type=='EMPTY' and o.get('source_fixture_id')==cid)
 count=0
 for ob in counter.children_recursive:
  if ob.type!='MESH':continue
  bb=[ob.matrix_world@Vector(c) for c in ob.bound_box]
  lo=min(w.y for w in bb);hi=max(w.y for w in bb)
  if lo>=5.6315 and hi<=6.4313:a,b,aa,bbnew=5.6316495,6.431075,5.6316495,6.331075
  elif lo>=7.1928 and hi<=8.4951:a,b,aa,bbnew=7.193075,8.4949,7.093075,8.4949
  else:continue
  inv=ob.matrix_world.inverted()
  for v in ob.data.vertices:
   w=ob.matrix_world@v.co;w.y=aa+(w.y-a)*(bbnew-aa)/(b-a);v.co=inv@w
  ob.data.update();ob['source_revision']=rev;count+=1
 sc['source_revision']=rev;sc['hood_notes']='1250 mm rectangular hood, broad 150 mm rounded corners; backsplash and range share centerline'
 sc['backsplash_notes']='1250 mm arched warm stone panel, same width and centerline as hood'
 bpy.context.view_layer.update()
 # Width and alignment validation in world coordinates.
 def yc(o):
  b=[o.matrix_world@Vector(c) for c in o.bound_box];return (min(w.y for w in b)+max(w.y for w in b))/2
 body=next(o for o in stove.children if o.type=='MESH' and o.name.startswith('Range.'))
 assert abs(yc(body)-cy)<.00001,(body.name,yc(body))
 assert abs(yc(shell)-cy)<.00001
 assert abs(yc(slab)-cy)<.00001
 print(sc.name,'centerline',cy,'refitted joinery meshes',count)
f=doc['fixtures'][sid];f['origin']['y']+=100
f['clearance_note']='Range centered under hood; shifted another 100 mm left, increasing dishwasher clearance.'
h=doc['fixtures']['cc99b809-cb08-51b4-a631-7c1eae3d9db0'];h['style']='rectangular_plaster_hood_150mm_rounded_corners_centered_range_matching_1250mm_backsplash';h['material']='Warm ivory mineral plaster, broad 150 mm rounded corners'
for l in doc['room_labels'].values():
 if l['name'].startswith('Arched warm stone:'):l['name']='Arched warm stone: 1250 mm / same width as hood'
 elif l['name'].startswith('Rectangular plaster hood:'):l['name']='Rounded rectangular hood: 150 mm corners / range centered'
doc['revision']=rev
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {rev}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {rev}: broadened hood corner radius from 50 to 150 mm. Arched backsplash widened to 1250 mm and centered under hood. Range moved 100 mm left to same centerline; adjoining base cabinets, door fronts, end panels and stone counters refitted to new range opening.\n')
