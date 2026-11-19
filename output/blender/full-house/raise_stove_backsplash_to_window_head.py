"""Raise only the tall stove-side soapstone section to the 2100 mm window head."""
import bpy,json
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=27
for label in doc['room_labels'].values():
 if label['name'].startswith('Soapstone:'):label['name']='Soapstone: stove top 2100 mm / low sill band'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 slab=next(o for o in scene.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
 for v in slab.data.vertices:
  if v.co.z>1.1:v.co.z=2.1
 slab.data.update();slab.parent['source_revision']=27;slab.parent['top_mm']=2100
 scene['source_revision']=27;scene['backsplash_notes']='Honed soapstone: tall stove/prep section top 2100 mm, aligned with west window head. At west window it steps down to a continuous 53.5 mm low band, top 986 mm below sill/trim, wrapping the corner and entire sink counter to right wall. 20 mm slab; painted plaster above low band.'
 bpy.context.view_layer.update();assert abs(max((slab.matrix_world@Vector(v)).z for v in slab.bound_box)-2.1)<1e-5
 if scene==source:scene.name='Full House | Drawing Revision 27'
 print(scene.name,'stove backsplash verified at 2100 mm window head; low band retained')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/25-stove-soapstone-to-window-head.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 26','revision 27');paras=text.split('\n\n');paras[1]='Honed charcoal soapstone backsplash: stove/prep section top 2100 mm aligned with west window head, stepping down at west window to a continuous 53.5 mm low band, top 986 mm beneath window sill/trim. Band wraps corner and follows full sink counter to right wall. 20 mm slab, eased edges; painted plaster above low band.';text='\n\n'.join(paras);text+='\nRevision 27: stove-side tall soapstone raised to 2100 mm window head; continuous low window/sink-wall band retained.\n';p.write_text(text)
