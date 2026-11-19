"""Reference-inspired panoramic sink window, continuous lit shelf, and recessed grips."""
import bpy,json,uuid,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=31
wid='746ae532-71e5-438a-bc40-f8907c28fcae';winid='9b44bb93-1dea-42b1-98cd-26466e14a447';sid='90d62899-1317-5cc7-a110-a6c6b9d14fbb';uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/second-full-span-sink-shelf'))
win=doc['windows'][winid];win['position']=1578.0;win['width']=2798.2
f=doc['fixtures'][sid];f['origin']={'x':17358,'y':2288.1};f['width']=2998.2;f['depth']=220;f['style']='single_wall_to_wall_floating_oak_shelf_top_1476mm_below_panoramic_window_warm_LED';doc['fixtures'].pop(uid,None)
for fid in ['c0c93320-283f-4d94-bc6e-b11ec56a989a','c08078d4-006c-4eba-8032-0bf18c432cec','0a136254-797b-44fe-b369-8f6e98f33bc0','e1928df0-155f-546e-b491-516387590509','9795d0d2-7db7-411f-91b8-ecbebec3fb30','d7fa9c10-7151-51e9-ac2f-0f54d81ddcef']:
 fx=doc['fixtures'][fid];fx['style']=fx.get('style','').replace('_recessed_edge_grips','')+'_recessed_edge_grips';fx['material']=fx.get('material','').replace('satin nickel pulls','concealed edge grips')
labelid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/panoramic-window-shelf-note'))
doc['room_labels'][labelid]={'id':labelid,'name':'Sink window: 2798 x 374 mm / sill 1476 / head 1850','position':{'x':22550,'y':6400}}
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin']
def original(o):return o.get('walkthrough_source_name',o.name)
def xyz(x,y,z):return ((x-19383.1)/1000,(10783-y)/1000,z)
def oak_uv(o,shelf=False):
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co
   if shelf:u,v=((y/.7,x/1.6) if axis==2 else ((z/.7,x/1.6) if axis==1 else (y/.7,z/1.6)))
   else:u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],v+off[1])
led=bpy.data.materials.get('Shelf | Warm concealed LED')
if not led:
 led=bpy.data.materials.new('Shelf | Warm concealed LED');led.use_nodes=True;p=next(n for n in led.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(1,.66,.30,1);p.inputs['Emission Color'].default_value=(1,.57,.22,1);p.inputs['Emission Strength'].default_value=3
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 old=[o for o in scene.objects if original(o).startswith('Main north') and o.type=='MESH']
 plaster=next(o.data.materials[0] for o in old if '| wall' in original(o));glass=next(o.data.materials[0] for o in old if '| glazing' in original(o));trim=next(o.data.materials[0] for o in old if 'jamb' in original(o))
 for o in old:bpy.data.objects.remove(o,do_unlink=True)
 col=bpy.data.collections.new('Kitchen | Panoramic window continuous shelf minimal joinery');scene.collection.children.link(col)
 def box(name,loc,dims,ma,parent=None,bev=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  if bev:
   b=o.modifiers.new('Soft crafted edges','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
  return o
 wall=doc['walls'][wid];start=wall['start']['x'];y=wall['start']['y'];thick=wall['thickness']/1000;H=2.4384
 def block(a,b,z1,z2,ma=plaster,name='wall'):
  if b-a<.1 or z2-z1<.001:return
  o=box('Main north | '+name,xyz(start+(a+b)/2,y,(z1+z2)/2),((b-a)/1000,thick,z2-z1),ma,bev=0 if ma==plaster else .001);o['source_wall_id']=wid;return o
 cursor=0
 for w in sorted((w for w in doc['windows'].values() if w['wall']==wid),key=lambda w:w['position']):
  lo=w['position']-w['width']/2;hi=w['position']+w['width']/2;sill,head=(1.476,1.85) if w['id']==winid else (1.,2.1)
  block(cursor,lo,0,H);block(lo,hi,0,sill);block(lo,hi,head,H)
  for station in [lo,hi]:
   o=box('Main north opening jamb',xyz(start+station,y,(sill+head)/2),(.024,thick+.045,head-sill+.024),trim);o['source_window_id']=w['id']
  for z in [sill,head]:block(lo-12,hi+12,z-.012,z+.012,trim,'opening trim')
  o=box('Main north | glazing',xyz(start+w['position'],y,(sill+head)/2),(w['width']/1000,.018,head-sill),glass);o['source_window_id']=w['id'];o['clear_width_mm']=w['width'];o['sill_mm']=sill*1000;o['head_mm']=head*1000
  if w['id']!=winid:block(w['position']-12,w['position']+12,sill,head,trim,'mullion')
  cursor=hi
 block(cursor,wall['end']['x']-start,0,H)
 for root in [o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id') in [sid,uid]]:
  for child in list(root.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
  bpy.data.objects.remove(root,do_unlink=True)
 root=bpy.data.objects.new('Kitchen | Wall-to-wall panoramic window shelf',None);col.objects.link(root);root.location=xyz((17358+20356.2)/2,2288.1,0)
 root['source_fixture_id']=sid;root['source_revision']=31;root['plan_footprint_mm']=[2998.2,220];root['shelf_top_mm']=1476;root['drawing_style']=f['style']
 board=box('Panoramic shelf | floating white oak board',(0,-.11,1.46),(2.9982,.22,.032),wood,root,.0012);oak_uv(board,True);board['construction']='Floating shelf with concealed wall supports'
 box('Panoramic shelf | recessed warm LED diffuser',(0,-.175,1.442),(2.85,.008,.003),led,root,.0005)
 data=bpy.data.lights.new('Panoramic shelf | warm task wash','AREA');data.energy=14;data.color=(1,.70,.43);data.shape='RECTANGLE';data.size=2.8;data.size_y=.055
 light=bpy.data.objects.new(data.name,data);col.objects.link(light);light.parent=root;light.location=(0,-.155,1.437);light.visible_camera=False;light.visible_glossy=False;light.visible_transmission=False
 for o in scene.objects:
  if o.type=='EMPTY' and o.name.startswith('Shelf accessories | Long sink shelf tableware'):o.location=Vector((-1.3,8.3849,1.476))
  if o.type=='EMPTY' and o.name.startswith('Shelf accessories | Long sink shelf canisters and herbs'):o.location=Vector((.35,8.3849,1.476))
 # Replace all kitchen cabinet bar pulls with top-edge recessed finger grips.
 removed=0
 for o in list(scene.objects):
  n=original(o)
  if n.startswith(('Joinery | west nickel pull','Joinery | north nickel pull','Dishwasher recessed pull','Base cabinet | horizontal pull','Fridge surround | upper cabinet pull')) or (n.startswith('Microwave wall cabinets |') and 'pull' in n):bpy.data.objects.remove(o,do_unlink=True);removed+=1
 fronts=[o for o in scene.objects if o.type=='MESH' and original(o).startswith(('Joinery | west lower oak door','Joinery | west cutlery drawer','Joinery | north oak cabinet front','Dishwasher oak integrated front','Base cabinet | lower storage drawer','Microwave wall cabinets |'))]
 count=0
 for o in fronts:
  n=original(o)
  if n.startswith('Microwave wall cabinets |') and 'closed slab door' not in n:continue
  if n.startswith('Joinery | north') and (o.dimensions.x<.2 or o.location.z<.3):continue
  axis,sign=(0,1) if n.startswith('Joinery | west') else (1,1 if n.startswith(('Base cabinet |','Microwave wall cabinets |')) else -1)
  # Remove a small wedge at the front top edge, leaving a full-width concealed grip.
  top=max(v.co.z for v in o.data.vertices);front=max(sign*v.co[axis] for v in o.data.vertices)
  for v in o.data.vertices:
   if abs(v.co.z-top)<1e-5 and abs(sign*v.co[axis]-front)<1e-5:v.co.z-=.010/abs(o.scale.z)
  o.data.update();o['hardware']='Integrated recessed top-edge finger pull, no projecting bar';count+=1
 for o in scene.objects:
  if o.get('source_fixture_id') in doc['fixtures']:
   fx=doc['fixtures'][o['source_fixture_id']];o['source_revision']=31;o['drawing_style']=fx.get('style','')
 scene['source_revision']=31;scene['sink_window_notes']='Panoramic kitchen window 2798.2 mm wide x 374 mm high, sill 1476 mm / head 1850 mm. One 2998.2 x 220 x 32 mm wall-to-wall floating oak shelf directly beneath, top 1476 mm, warm concealed underside LED.'
 scene['kitchen_shelf_notes']='One continuous shelf under panoramic sink window replaces both previous sink shelves. Stove-side floating shelf retained. Minimal recessed finger-pull kitchen fronts; appliance layout retained.'
 if scene==source:scene.name='Full House | Drawing Revision 31'
 print(scene.name,'panoramic window, wall-to-wall lit shelf;',removed,'bar pull parts removed;',count,'recessed edge grips modeled')
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:path.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Sink and floating shelves'];tour.render.filepath=str(base/'walkthrough/30-panoramic-window-continuous-shelf.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 30','revision 31');text+='\nRevision 31: panoramic sink window 2798.2 x 374 mm, sill 1476 / head 1850 mm; one full-wall oak shelf 2998.2 x 220 mm, top 1476 mm, concealed warm underside LED. Both previous sink shelves replaced. Kitchen cabinet bars removed and recessed top-edge grips modeled. Appliance layout and tapered plaster hood retained. Window elevations recorded in 2D room note and Blender properties.\n';p.write_text(text)
