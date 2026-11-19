import bpy,bmesh,math,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text())
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin'];steel=bpy.data.materials['Finish | Satin brushed nickel'];shadow=bpy.data.materials['Finish | Deep cabinet reveals'];stone=bpy.data.materials['Kitchen | Honed charcoal soapstone']
def original(o):return o.get('walkthrough_source_name',o.name)
def oakuv(o,shelf=False):
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   v=o.data.vertices[o.data.loops[li].vertex_index].co;x,y,z=[v[i]*o.scale[i] for i in range(3)]
   if shelf:u,vv=((y/.7,x/1.6) if axis==2 else ((z/.7,x/1.6) if axis==1 else (y/.7,z/1.6)))
   else:u,vv=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],vv+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 col=bpy.data.collections.new('Kitchen | Swapped sink dishwasher and long floating shelf');scene.collection.children.link(col)
 def box(name,loc,dims,ma,parent=None,bevel=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  if ma:o.data.materials.append(ma)
  if bevel:
   b=o.modifiers.new('Machined soft edges','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
  if ma==wood:oakuv(o)
  return o
 def tube(name,points,radius,ma,parent=None):
  d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=radius;d.bevel_resolution=4;p=d.splines.new('POLY');p.points.add(len(points)-1)
  for a,b in zip(p.points,points):a.co=(*b,1)
  o=bpy.data.objects.new(name,d);col.objects.link(o);o.parent=parent;d.materials.append(ma);return o
 sink=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='4be42708-ac78-437e-8895-9042270f0235')
 dw=next(o for o in scene.objects if o.get('design_element')=='dishwasher_drawer')
 sink.location.x=(18145.9-19383.1)/1000;dw.location.x=(18984.1-19383.1)/1000
 sink['source_revision']=17;dw['source_revision']=17;dw['placement']='Right of sink, north countertop'
 dw['clearance_note']='Dishwasher moved to right of sink, away from stove. Open dishwasher and oven have separate plan footprints.'
 # Retain one 1100 mm shelf on the interior right; the left shelf is removed.
 left=next(o for o in scene.objects if original(o).startswith('Kitchen | Oak shelf left of sink window'))
 for o in list(left.children):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.objects.remove(left,do_unlink=True)
 right=next(o for o in scene.objects if original(o).startswith('Kitchen | Oak shelf right of sink window'))
 right.location.x=.2977;right['plan_footprint_mm']=[1100,280];right['source_revision']=17;right['placement']='Single long floating shelf to right of the shifted sink window, viewed from inside kitchen'
 board=next(o for o in right.children if 'oak board' in original(o));board.dimensions.x=1.1;oakuv(board,True)
 la=next(o for o in scene.objects if o.name.startswith('Shelf accessories | left sink shelf'));la.location.x=0;la.name='Shelf accessories | Long sink shelf tableware'
 ra=next(o for o in scene.objects if o.name.startswith('Shelf accessories | right sink shelf'));ra.location.x=.50;ra.name='Shelf accessories | Long sink shelf canisters and herbs'
 # Seamless fireclay shell with rounded corners and a gently sloping basin.
 porcelain=bpy.data.materials['Kitchen | White fireclay']
 for o in list(sink.children):
  if original(o).startswith(('Farmhouse basin floor','Farmhouse exposed white apron','Farmhouse sink left','Farmhouse sink right','Farmhouse sink back')):bpy.data.objects.remove(o,do_unlink=True)
 def ring(w,d,r,z,cx=.4191,cy=-.344):
  pts=[]
  for ox,oy,start in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
   for i in range(13):
    a=math.radians(start+90*i/12);pts.append((cx+ox+r*math.cos(a),cy+oy+r*math.sin(a),z))
  return pts
 profiles=[(.8242,.572,.025,.68,-.344),(.8382,.586,.025,.70,-.344),(.8382,.586,.025,.92,-.344),(.8282,.576,.026,.93,-.344),(.7562,.492,.05,.93,-.332),(.7462,.482,.048,.92,-.332),(.7012,.437,.065,.756,-.332),(.6662,.402,.075,.727,-.332),(.6362,.372,.075,.722,-.332)]
 verts=[]
 for w,d,r,z,y in profiles:verts+=ring(w,d,r,z,cy=y)
 N=52;faces=[]
 for j in range(len(profiles)-1):
  for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
 faces.extend([tuple(range(N-1,-1,-1)),tuple((len(profiles)-1)*N+i for i in range(N))])
 data=bpy.data.meshes.new('Seamless rounded fireclay shell');data.from_pydata(verts,[],faces);data.update()
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(data);bm.free()
 basin=bpy.data.objects.new('Farmhouse | seamless rounded fireclay basin',data);col.objects.link(basin);basin.parent=sink;data.materials.append(porcelain)
 for p in data.polygons:p.use_smooth=(len(p.vertices)==4)
 # Rebuild the north cabinet/counter with the new apron opening, healing the previous cutout.
 north=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a')
 for o in list(north.children):bpy.data.objects.remove(o,do_unlink=True)
 body=box('Oak base cabinets | revised sink run',(1.1816,-.311,.509),(2.3632,.598,.758),shadow,north)
 top=box('Soapstone kitchen countertop | revised sink run',(1.1816,-.3175,.915),(2.3682,.645,.035),stone,north,.002)
 # Opening measured to the ceramic outer shell, leaving a small installation joint.
 bpy.context.view_layer.update();sx=sink.location.x-north.location.x
 cutter=box('Temporary | apron opening',(sx+.4191,-.365,.87),(.8422,.69,.39),None,north,0)
 for ob in [body,top]:
  mod=ob.modifiers.new('New sink apron opening','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
 box('Joinery | north recessed oak plinth',(1.1816,-.554,.068),(2.3632,.025,.116),wood,north)
 def door(a,b,z1,z2,pull=True):
  x=(a+b)/2;box('Joinery | north oak cabinet front',(x,-.624,(z1+z2)/2),(b-a-.003,.022,z2-z1),wood,north)
  if pull:
   z=z2-.045;tube('Joinery | north nickel pull',[(x-.09,-.642,z),(x-.09,-.665,z),(x+.09,-.665,z),(x+.09,-.642,z)],.0035,steel,north)
 door(0,.1529,.135,.893,False)
 for a,b in [(.1529,.572),(.572,.9911)]:door(a,b,.135,.663)
 door(.9911,1.6007,.135,.443,False)
 for a,b in [(1.6007,1.98195),(1.98195,2.3632)]:door(a,b,.135,.709);door(a,b,.713,.893)
 # Move only the sink window's geometry: rebuild the three openings on its host wall.
 wid='746ae532-71e5-438a-bc40-f8907c28fcae';wall=doc['walls'][wid]
 old=[o for o in scene.objects if original(o).startswith('Main north') and o.type=='MESH']
 plaster=next(o.data.materials[0] for o in old if '| wall' in original(o));glass=next(o.data.materials[0] for o in old if '| glazing' in original(o));trim=next(o.data.materials[0] for o in old if 'jamb' in original(o))
 for o in old:bpy.data.objects.remove(o,do_unlink=True)
 start=wall['start']['x'];y=wall['start']['y'];thick=wall['thickness']/1000;H=2.4384
 def xyz(x,y,z):return ((x-19383.1)/1000,(10783-y)/1000,z)
 def block(a,b,z1,z2,ma=plaster,name='wall'):
  if b-a<.1:return
  ob=box('Main north | '+name,xyz(start+(a+b)/2,y,(z1+z2)/2),((b-a)/1000,thick,z2-z1),ma,bevel=0 if ma==plaster else .001)
  ob['source_wall_id']=wid;return ob
 cursor=0
 for win in sorted((w for w in doc['windows'].values() if w['wall']==wid),key=lambda w:w['position']):
  lo=win['position']-win['width']/2;hi=win['position']+win['width']/2
  block(cursor,lo,0,H);block(lo,hi,0,1);block(lo,hi,2.1,H)
  for station in [lo,hi]:
   ob=box('Main north opening jamb',xyz(start+station,y,1.55),(.035,thick+.045,1.135),trim);ob['source_window_id']=win['id']
  for z in [1,2.1]:block(lo-18,hi+18,z-.018,z+.018,trim,'opening trim')
  ob=box('Main north | glazing',xyz(start+win['position'],y,1.55),(win['width']/1000,.018,1.1),glass);ob['source_window_id']=win['id'];ob['clear_width_mm']=win['width']
  block(win['position']-12,win['position']+12,1,2.1,trim,'mullion');cursor=hi
 block(cursor,wall['end']['x']-start,0,H)
 # Area lights illuminate the model without appearing as fake softboxes through the windows.
 if scene==tour:
  for o in scene.objects:
   if o.type=='LIGHT' and o.data.type=='AREA':
    o.visible_camera=False;o.visible_transmission=False;o.visible_glossy=False
 scene['source_revision']=17;scene['dishwasher_layout_note']=dw['clearance_note'];scene['sink_window_notes']='Sink left, integrated dishwasher to its right; 1000 mm window centered on sink; single 1100 x 280 mm floating oak shelf to interior right, top 1650 mm.'
 if scene==source:scene.name='Full House | Drawing Revision 17'
 bpy.context.view_layer.update()
 assert abs((sink.location.x+.4191)-((18565-19383.1)/1000))<1e-5
 assert abs(dw.location.x-(18984.1-19383.1)/1000)<1e-5
 scene.frame_set(40);bpy.context.view_layer.update()
 stove=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')=='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a')
 assert dw.location.x>stove.location.x+.635+.60
 scene['oven_dishwasher_clearance_verified']='Full-width oven 600 mm projection and dishwasher 558.8 mm extension have disjoint plan rectangles after sink/dishwasher swap.'
 scene.frame_set(1)
 print(scene.name,'sink X18145.9; dishwasher X18984.1; centered window X18565; single shelf1100x280')
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=tour
cam=bpy.data.objects['Photo | Sink and floating shelves'];cam.location=(.12,6.15,1.65);target=Vector((-.33,8.48,1.30));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=25;cam.data.dof.focus_distance=(target-cam.location).length
tour.camera=cam;tour.render.filepath=str(base/'walkthrough/10-swapped-sink-and-long-shelf.png')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
