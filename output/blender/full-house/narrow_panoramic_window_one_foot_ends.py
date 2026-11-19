"""Leave one foot of wall at either end of the centered kitchen window."""
import bpy,json
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=35
winid='9b44bb93-1dea-42b1-98cd-26466e14a447';wid='746ae532-71e5-438a-bc40-f8907c28fcae';win=doc['windows'][winid];oldwidth=win['width'];win['width']=2388.6
for label in doc['room_labels'].values():
 if label['name'].startswith('Sink window:'):label['name']='Sink window: 2389 x 374 mm / 1 ft wall each end'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
center=(doc['walls'][wid]['start']['x']+win['position']-19383.1)/1000
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 glass=next(o for o in scene.objects if o.type=='MESH' and o.get('source_window_id')==winid and 'glazing' in o.name)
 old=glass.dimensions.x;new=win['width']/1000;glass.dimensions.x=new;glass['clear_width_mm']=win['width'];glass['source_revision']=35
 jambs=[o for o in scene.objects if o.type=='MESH' and o.get('source_window_id')==winid and 'jamb' in o.name]
 for o in jambs:o.location.x=center+(-1 if o.location.x<center else 1)*new/2
 for o in scene.objects:
  if o.type=='MESH' and o.name.startswith('Main north | opening trim') and abs(o.location.x-center)<.001 and (abs(o.location.z-1.476)<.001 or abs(o.location.z-1.85)<.001):o.dimensions.x=new+.024
 plaster=next(o.data.materials[0] for o in scene.objects if o.name.startswith('Main north | wall'))
 col=bpy.data.collections.new('Kitchen | One-foot window end walls');scene.collection.children.link(col)
 for sign in [-1,1]:
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name='Main north | window end plaster infill';o.location=(center+sign*(old+new)/4,8.5738,(1.476+1.85)/2);o.dimensions=((old-new)/2,.1578,1.85-1.476);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(plaster);o['source_wall_id']=wid;o['source_revision']=35
 bpy.context.view_layer.update();left=center-new/2;right=center+new/2
 assert abs((left-(-2.0251))-.3048)<1e-5
 assert abs((.9731-right)-.3048)<1e-5
 scene['source_revision']=35;scene['sink_window_notes']='Centered kitchen window 2388.6 x 374 mm, sill 1476 / head 1850 mm; 304.8 mm (one foot) wall from opening to each end of kitchen wall. Sink remains centered; continuous wall-to-wall oak shelf unchanged.'
 if scene==source:scene.name='Full House | Drawing Revision 35'
 print(scene.name,'window narrowed to 2388.6 mm; verified one foot of wall each end')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Kitchen lantern and daylight'];tour.render.filepath=str(base/'walkthrough/35-window-one-foot-wall-ends.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 34','revision 35').replace('2798.2 mm wide x 374 mm high','2388.6 mm wide x 374 mm high');text+='\nRevision 35: centered horizontal kitchen window narrowed to 2388.6 mm to leave 304.8 mm (one foot) wall at each end of kitchen wall. Sill, head, centered sink and wall-to-wall shelf retained.\n';p.write_text(text)
