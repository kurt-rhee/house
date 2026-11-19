"""Extend the sink-side floating shelf to the window jamb and perpendicular wall."""
import bpy,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=25
fid='90d62899-1317-5cc7-a110-a6c6b9d14fbb'
left=-.3006;right=.9731;width=right-left;mid=(left+right)/2
f=doc['fixtures'][fid];f['origin']['x']=19082.5;f['width']=round(width*1000,3);f['style']='single_floating_shelf_window_trim_to_right_wall_top_1450mm_concealed_supports'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid);board=next(o for o in root.children if o.type=='MESH')
 oldwidth=max(v.co.x for v in board.data.vertices)-min(v.co.x for v in board.data.vertices)
 for v in board.data.vertices:v.co.x*=width/(oldwidth*abs(board.scale.x))
 board.data.update();root.location.x=mid
 # Preserve physical veneer scale on the wider board.
 uv=board.data.uv_layers.active;off=(.18,.24)
 for p in board.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=[a*b for a,b in zip(board.data.vertices[board.data.loops[li].vertex_index].co,board.scale)]
   u,v=((y/.7,x/1.6) if axis==2 else ((z/.7,x/1.6) if axis==1 else (y/.7,z/1.6)))
   uv.data[li].uv=(u+off[0],v+off[1])
 root['source_revision']=25;root['plan_footprint_mm']=[f['width'],280];root['drawing_style']=f['style'];root['shelf_width_mm']=f['width'];root['placement']='Continuous floating shelf from sink window right jamb to perpendicular wall; top remains 1450 mm.'
 bpy.context.view_layer.update();pts=[board.matrix_world@Vector(v) for v in board.bound_box]
 assert abs(min(p.x for p in pts)-left)<1e-5
 assert abs(max(p.x for p in pts)-right)<1e-5
 assert abs(max(p.z for p in pts)-1.45)<1e-5
 scene['source_revision']=25;scene['sink_window_notes']='Sink window centered over sink; right-side floating shelf spans from window trim to perpendicular wall, 1273.7 x 280 mm, top 1450 mm.'
 if scene==source:scene.name='Full House | Drawing Revision 25'
 print(scene.name,'sink shelf verified: window trim to wall, 1273.7 mm wide, top 1450 mm')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Sink and floating shelves'];tour.render.filepath=str(base/'walkthrough/23-sink-shelf-window-to-wall.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 24','revision 25').replace('1100 x 280 mm shelf','1273.7 x 280 mm shelf');text+='\nRevision 25: sink shelf extended to meet right window jamb and perpendicular wall, 1273.7 mm wide; depth 280 mm and top 1450 mm retained.\n';p.write_text(text)
