import bpy,json,math
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text())
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
sid='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a';cid='c08078d4-006c-4eba-8032-0bf18c432cec'
def original(o):return o.get('walkthrough_source_name',o.name)
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 stove=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==sid);stove.location.y-=.35;stove['source_revision']=15
 counter=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==cid)
 # The continuous concept cabinet run is split around the range so oak/stone do not occupy the appliance.
 for o in list(counter.children):
  n=original(o)
  if 'Cabinet seam' in n:bpy.data.objects.remove(o,do_unlink=True)
  elif 'base cabinets' in n.lower() or 'countertop' in n.lower():
   old=o.copy();old.data=o.data.copy();scene.collection.objects.link(old)
   # Local y runs south. Range occupies stations 1301.825..2063.825 mm.
   for ob,a,b in [(o,0,1.301825),(old,2.063825,3.01565)]:
    ob.location.y=-(a+b)/2;ob.dimensions.y=b-a;ob['source_revision']=15
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.select_set(False)
 counter['plan_footprint_mm']=[635,3015.65];counter['source_revision']=15
 rack=next(o for o in scene.objects if original(o).startswith('Kitchen | Stove-side shelf and magnetic knife bar'));rack.location.y-=.35;rack['source_revision']=15
 rack['placement']='Prep counter south of shifted stove; 151 mm clear of cooktop footprint'
 a=next(o for o in scene.objects if o.name.startswith('Shelf accessories | stove prep shelf'));a.location.y-=.35
 # Parent the visible oven door to a hinge; frame 1 closed, frame 40 both appliances open.
 col=stove.users_collection[0]
 hinge=bpy.data.objects.new('Operation | Oven door hinge',None);col.objects.link(hinge);hinge.parent=stove;hinge.location=(.381,-.642,.235)
 bpy.context.view_layer.update()
 for o in list(stove.children):
  if original(o).startswith(('Oven glass','Oven handle')):
   world=o.matrix_world.copy();o.parent=hinge;o.matrix_world=world
 hinge.rotation_euler.x=0;hinge.keyframe_insert(data_path='rotation_euler',frame=1)
 hinge.rotation_euler.x=math.pi/2;hinge.keyframe_insert(data_path='rotation_euler',frame=40)
 dw=next(o for o in scene.objects if o.get('design_element')=='dishwasher_drawer')
 drawer=bpy.data.objects.new('Operation | Integrated dishwasher drawer',None);col.objects.link(drawer);drawer.parent=dw
 bpy.context.view_layer.update()
 for o in list(dw.children):
  if original(o).startswith(('Dishwasher oak','Dishwasher recessed')):
   world=o.matrix_world.copy();o.parent=drawer;o.matrix_world=world
 # A stainless inner drawer makes the open position legible.
 def box(name,loc,dims,mat):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.parent=drawer;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);b=o.modifiers.new('Rounded drawer edges','BEVEL');b.width=.004;b.segments=3
  return o
 metal=bpy.data.materials.get('Brushed chrome')
 box('Dishwasher | inner tub base',(.3048,-.34,.46),(.55,.55,.018),metal)
 for x in [.03,.5796]:box('Dishwasher | inner tub side',(x,-.34,.56),(.018,.55,.20),metal)
 for y in [-.065,-.615]:box('Dishwasher | inner tub end',(.3048,y,.56),(.55,.018,.20),metal)
 drawer.location.y=0;drawer.keyframe_insert(data_path='location',frame=1)
 drawer.location.y=-.5588;drawer.keyframe_insert(data_path='location',frame=40)
 dw['clearance_note']='Range shifted 350 mm south (left facing stove). 75.0 mm plan clearance between full-width oven envelope and dishwasher pull at 558.8 mm extension.'
 scene['dishwasher_layout_note']=dw['clearance_note'];scene['source_revision']=15
 scene.frame_start=1;scene.frame_end=40
 scene.timeline_markers.new('CLOSED | normal view',frame=1);scene.timeline_markers.new('OPEN | oven + dishwasher clearance',frame=40)
 scene.frame_set(40);bpy.context.view_layer.update()
 oven_ymax=stove.location.y+.762;dw_ymin=dw.location.y-.668-.5588
 gap=dw_ymin-oven_ymax;assert gap>.075,(scene.name,gap)
 scene['oven_dishwasher_open_clearance_mm']=round(gap*1000,1)
 data=bpy.data.cameras.new('Detail | Oven and dishwasher open');data.lens=28
 cam=bpy.data.objects.new(data.name,data);scene.collection.objects.link(cam);cam.location=(.4,6.1,2.7);cam.rotation_euler=(Vector((-1.15,7.45,.65))-cam.location).to_track_quat('-Z','Y').to_euler()
 if scene==tour:open_cam=cam
 scene.frame_set(1)
 if scene==source:scene.name='Full House | Drawing Revision 15'
 print(scene.name,'open envelope gap',round(gap*1000,1),'mm')
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=open_cam;tour.frame_set(40);tour.render.filepath=str(base/'walkthrough/06-oven-and-dishwasher-open.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
