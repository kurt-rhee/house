"""Lower both remaining kitchen floating shelves to 1450 mm; remove knife rack."""
import bpy,json
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=23
stove_id='33ac9591-fe96-5361-867e-89318d0ce11c';sink_id='90d62899-1317-5cc7-a110-a6c6b9d14fbb'
doc['fixtures'].pop('79ecafe0-f099-56ad-8288-22aecafe777d',None)
for fid in [stove_id,sink_id]:doc['fixtures'][fid]['style']=doc['fixtures'][fid]['style'].replace('1750mm','1450mm').replace('1650mm','1450mm')
for label in doc['room_labels'].values():
 if label['name']=='Shelf + knife bar below':label['name']='Floating shelf: top 1450 mm'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def original(o):return o.get('walkthrough_source_name',o.name)
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 for o in list(scene.objects):
  if original(o).startswith('Knife bar |'):bpy.data.objects.remove(o,do_unlink=True)
 for fid,delta,prefix in [(stove_id,-.3,'Shelf accessories | stove prep shelf'),(sink_id,-.2,'Shelf accessories | Long sink shelf')]:
  root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
  # Move the physical board; retain the root at the plan datum.
  boards=[o for o in root.children if o.type=='MESH'];assert len(boards)==1
  board=boards[0];board.location.z+=delta
  root['shelf_top_mm']=1450;root['source_revision']=23;root['drawing_style']=doc['fixtures'][fid]['style']
  for k in ['knife_bar_center_mm','knife_bar_width_mm']:
   if k in root:del root[k]
  if fid==stove_id:
   root.name='Kitchen | Stove-side floating shelf';root['walkthrough_source_name']='Kitchen | Stove-side floating shelf'
  for o in scene.objects:
   if o.parent is None and original(o).startswith(prefix):o.location.z+=delta
  bpy.context.view_layer.update()
  top=max((board.matrix_world@Vector(v)).z for v in board.bound_box);assert abs(top-1.45)<.00001,top
 assert not any(original(o).startswith('Knife bar |') for o in scene.objects)
 scene['source_revision']=23;scene['kitchen_shelf_notes']='Stove-side and sink-side floating shelf tops both 1450 mm above floor. Knife bar and all knives removed. Two stacked closed cabinets above microwave.'
 scene['sink_window_notes']='Sink left, integrated dishwasher to its right; 1000 mm window centered on sink; single 1100 x 280 mm floating shelf to right, top 1450 mm.'
 if scene==source:scene.name='Full House | Drawing Revision 23'
 print(scene.name,'both shelf tops verified 1450 mm; knife bar and knives removed')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/19-lowered-stove-shelf.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 22','revision 23');text+='\nRevision 23: both stove and sink floating shelf tops lowered to 1450 mm above floor (stove -300 mm, sink -200 mm), with accessories moved together. Knife bar and all knives removed from both scenes and 2D plan.\n';p.write_text(text)
