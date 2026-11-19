"""Center the sink on the panoramic window; move dishwasher to its immediate right."""
import bpy,json,random
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=32
sid='4be42708-ac78-437e-8895-9042270f0235';did='9795d0d2-7db7-411f-91b8-ecbebec3fb30';nid='c0c93320-283f-4d94-bc6e-b11ec56a989a'
w=doc['windows']['9b44bb93-1dea-42b1-98cd-26466e14a447'];wall=doc['walls'][w['wall']];center=wall['start']['x']+w['position'];sf=doc['fixtures'][sid];df=doc['fixtures'][did];nf=doc['fixtures'][nid]
sf['origin']['x']=center-sf['width']/2;df['origin']['x']=sf['origin']['x']+sf['width'];sf['style']='farmhouse_apron_sink_centered_on_panoramic_window';df['clearance_note']='Immediately right of centered sink; open drawer remains clear of oven.'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin'];stone=bpy.data.materials['Kitchen | Honed charcoal soapstone'];shadow=bpy.data.materials['Finish | Deep cabinet reveals']
def oak_uv(o):
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co;u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)));uv.data[li].uv=(u+off[0],v+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 sink=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==sid)
 dw=next(o for o in scene.objects if o.get('design_element')=='dishwasher_drawer')
 sink.location.x=(sf['origin']['x']-19383.1)/1000;dw.location.x=(df['origin']['x']-19383.1)/1000
 sink['source_revision']=32;dw['source_revision']=32;dw['placement']='Immediately right of sink centered on panoramic window'
 north=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==nid)
 for o in list(north.children):
  for c in list(o.children_recursive):bpy.data.objects.remove(c,do_unlink=True)
  bpy.data.objects.remove(o,do_unlink=True)
 col=bpy.data.collections.new('Kitchen | Centered sink and right-hand dishwasher');scene.collection.children.link(col)
 def box(name,loc,dims,ma,bev=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=north;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  if ma:o.data.materials.append(ma)
  if bev:
   b=o.modifiers.new('Machined soft edges','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
  if ma==wood:oak_uv(o)
  return o
 body=box('Oak base cabinets | centered sink run',(1.1816,-.311,.509),(2.3632,.598,.758),shadow)
 top=box('Soapstone kitchen countertop | centered sink run',(1.1816,-.3175,.915),(2.3682,.645,.035),stone,.002)
 sx=(sf['origin']['x']-nf['origin']['x'])/1000
 cutter=box('Temporary | centered apron sink cutout',(sx+.4191,-.365,.87),(.8422,.69,.39),None,0)
 for ob in [body,top]:
  mod=ob.modifiers.new('Centered sink apron opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
 box('Joinery | north recessed oak plinth',(1.1816,-.554,.068),(2.3632,.025,.116),wood)
 def door(a,b,z1,z2,grip=True):
  o=box('Joinery | north oak cabinet front',((a+b)/2,-.624,(z1+z2)/2),(b-a-.003,.022,z2-z1),wood)
  if grip:
   z=max(v.co.z for v in o.data.vertices);y=min(v.co.y for v in o.data.vertices)
   for v in o.data.vertices:
    if abs(v.co.z-z)<1e-5 and abs(v.co.y-y)<1e-5:v.co.z-=.01
   o.data.update();o['hardware']='Integrated recessed top-edge finger pull, no projecting bar'
  return o
 se=sx+.8382;de=se+.6096
 # 445 mm storage to left; two under-sink doors; dishwasher; 470.4 mm storage right.
 door(0,sx,.135,.709);door(0,sx,.713,.893)
 door(sx,sx+.4191,.135,.663);door(sx+.4191,se,.135,.663)
 door(se,de,.135,.443,False)
 door(de,2.3632,.135,.709);door(de,2.3632,.713,.893)
 north['source_revision']=32;north['layout']='Left storage 445 mm; centered sink base 838.2 mm; dishwasher 609.6 mm immediately right; right storage 470.4 mm'
 bpy.context.view_layer.update();assert abs(sink.matrix_world.translation.x+.4191-(center-19383.1)/1000)<1e-5
 assert abs(dw.matrix_world.translation.x-(sink.matrix_world.translation.x+.8382))<1e-5
 scene['source_revision']=32;scene['sink_layout_notes']='Sink centered on panoramic window and full-wall shelf, plan X18857.1 mm; integrated dishwasher immediately right. Sink origin X18438 mm; dishwasher origin X19276.2 mm. Cabinet fronts and soapstone cutout rebuilt with recessed finger grips.'
 if scene==source:scene.name='Full House | Drawing Revision 32'
 print(scene.name,'sink center verified X',center,'dishwasher to right X',df['origin']['x'])
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Sink and floating shelves'];tour.render.filepath=str(base/'walkthrough/32-centered-sink-dishwasher-right.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 31','revision 32').replace('Sink and dishwasher locations unchanged.','Sink centered on panoramic window, dishwasher immediately to right.');text+='\nRevision 32: sink center X18857.1 mm matches panoramic window and full-wall shelf; sink origin X18438 mm, dishwasher origin X19276.2 mm. North cabinet and soapstone cutout rebuilt. 445 mm left storage and 470.4 mm right storage; recessed grips retained.\n';p.write_text(text)
