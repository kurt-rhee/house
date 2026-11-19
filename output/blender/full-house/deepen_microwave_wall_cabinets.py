"""Extend the ceiling-height microwave cabinets to the microwave's front plane."""
import bpy,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=28
fid='e1928df0-155f-546e-b491-516387590509';depth=.6864
f=doc['fixtures'][fid];f['depth']=686.4;f['origin']['y']=4902.35;f['style']='two_stacked_enclosed_oak_wall_cabinets_bottom_1444mm_top_2438.4mm_ceiling_height_depth_686.4mm_flush_to_microwave_front'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
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
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 door=next(o for o in root.children if 'closed slab door' in o.name)
 oldfront=door.location.y+max(v.co.y for v in door.data.vertices);delta=depth-oldfront
 for o in root.children:
  if 'side' in o.name or 'base or top' in o.name:
   oldsize=max(v.co.y for v in o.data.vertices)-min(v.co.y for v in o.data.vertices)
   for v in o.data.vertices:v.co.y*=(oldsize+delta)/oldsize
   o.location.y+=delta/2;o.data.update();oak_uv(o)
  elif 'closed slab door' in o.name or 'pull' in o.name:o.location.y+=delta
 root['source_revision']=28;root['plan_footprint_mm']=[622.1125,686.4];root['drawing_style']=f['style'];root['depth_mm']=686.4
 bpy.context.view_layer.update()
 for o in root.children:
  if 'closed slab door' in o.name:
   front=max((root.matrix_world.inverted()@o.matrix_world@Vector(v)).y for v in o.bound_box);assert abs(front-depth)<1e-5,front
 scene['source_revision']=28;scene['microwave_wall_cabinet_notes']='Two stacked oak cabinets above microwave, bottom 1444 mm and ceiling top 2438.4 mm. Full 686.4 mm depth to microwave door/fascia front plane; 622.1125 mm width, matching satin nickel pulls.'
 if scene==source:scene.name='Full House | Drawing Revision 28'
 print(scene.name,'upper cabinet door fronts verified flush to microwave at 686.4 mm depth')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Fridge and microwave shelves'];tour.render.filepath=str(base/'walkthrough/26-full-depth-microwave-cabinets.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 27','revision 28').replace('622.1125 mm wide x 280 mm deep','622.1125 mm wide x 686.4 mm deep');text+='\nRevision 28: ceiling-height cabinets above microwave deepened to 686.4 mm; door fronts align with microwave door/fascia plane. Width and vertical positions retained.\n';p.write_text(text)
