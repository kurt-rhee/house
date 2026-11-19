"""Align the microwave cabinet run to the refrigerator's 660.4 mm front plane."""
import bpy,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=29
fid='e1928df0-155f-546e-b491-516387590509';bid='0a136254-797b-44fe-b369-8f6e98f33bc0'
f=doc['fixtures'][fid];f['depth']=660.4;f['origin']['y']=4928.35;f['style']='two_stacked_oak_cabinets_bottom_1444mm_top_2438.4mm_ceiling_height_depth_660.4mm_flush_to_fridge'
doc['fixtures'][bid]['style']='counter_height_932.5mm_integrated_microwave_vented_surround_depth_660.4mm_flush_to_fridge'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def original(o):return o.get('walkthrough_source_name',o.name)
def oak_uv(o):
 uv=o.data.uv_layers.active;rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co
   u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],v+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 base_root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==bid)
 fridge=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='34b8ac75-afa6-4ae6-a9b6-db3765c13087')
 body=next(o for o in fridge.children if 'body' in o.name.lower());bpy.context.view_layer.update()
 front=max((body.matrix_world@Vector(v)).y for v in body.bound_box);target=front-base_root.matrix_world.translation.y
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 door=next(o for o in root.children if 'closed slab door' in o.name);oldfront=door.location.y+max(v.co.y for v in door.data.vertices);delta=target-oldfront
 for o in root.children:
  if 'side' in o.name or 'base or top' in o.name:
   size=max(v.co.y for v in o.data.vertices)-min(v.co.y for v in o.data.vertices)
   for v in o.data.vertices:v.co.y*=(size+delta)/size
   o.location.y+=delta/2;o.data.update();oak_uv(o)
  elif 'closed slab door' in o.name or 'pull' in o.name:o.location.y+=delta
 # Move the complete microwave assembly without changing the appliance's proportions.
 face=next(o for o in base_root.children if original(o).startswith('Microwave | dark glass door'))
 facefront=max((base_root.matrix_world.inverted()@face.matrix_world@Vector(v)).y for v in face.bound_box);move=target-facefront
 for o in base_root.children:
  if original(o).startswith(('Microwave |','Microwave built-in |')):o.location.y+=move
 counter=next(o for o in base_root.children if 'soapstone countertop' in original(o).lower())
 # Retract the counter's front edge while retaining its rear position.
 oldsize=max(v.co.y for v in counter.data.vertices)-min(v.co.y for v in counter.data.vertices)
 oldfront=counter.location.y+max(v.co.y for v in counter.data.vertices);change=target-oldfront
 for v in counter.data.vertices:v.co.y*=(oldsize+change)/oldsize
 counter.location.y+=change/2;counter.data.update()
 # Applied drawer face ornament must also remain inside the cabinet front plane.
 detail=next(o for o in base_root.children if original(o).startswith('Base cabinet | drawer panel'))
 detailfront=detail.location.y+max(v.co.y for v in detail.data.vertices);detail.location.y+=target-detailfront
 root['source_revision']=29;root['plan_footprint_mm']=[622.1125,660.4];root['depth_mm']=660.4;root['drawing_style']=f['style']
 base_root['source_revision']=29;base_root['drawing_style']=doc['fixtures'][bid]['style']
 bpy.context.view_layer.update()
 for o in [face,counter]+[c for c in root.children if 'closed slab door' in c.name]:
  actual=max((o.matrix_world@Vector(v)).y for v in o.bound_box);assert abs(actual-front)<1e-5,(o.name,actual,front)
 scene['source_revision']=29;scene['microwave_wall_cabinet_notes']='Microwave face, countertop edge, and upper cabinet doors aligned to refrigerator body front at 660.4 mm depth. Upper cabinets remain ceiling height; handles project normally within fridge handle envelope.'
 if scene==source:scene.name='Full House | Drawing Revision 29'
 print(scene.name,'microwave face, countertop and upper cabinet fronts verified flush to fridge')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Fridge and microwave shelves'];tour.render.filepath=str(base/'walkthrough/27-microwave-cabinets-flush-to-fridge.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 28','revision 29').replace('622.1125 mm wide x 686.4 mm deep','622.1125 mm wide x 660.4 mm deep');text+='\nRevision 29: upper cabinet fronts, microwave face, and countertop front edge aligned to refrigerator body front at 660.4 mm depth; associated lower cabinetry retained at matching depth. Handles remain within fridge handle projection.\n';p.write_text(text)
