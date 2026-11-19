"""Revision 36: taller awning sash with recessed roller shade, preserving sill and width."""
import bpy,json,math,uuid
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=36
wid='746ae532-71e5-438a-bc40-f8907c28fcae';winid='9b44bb93-1dea-42b1-98cd-26466e14a447'
for label in doc['room_labels'].values():
 if label['name'].startswith('Sink window:'):label['name']='Sink window: 2389 x 561 mm / sill 1476 / head 2037 / awning + concealed shade / 1 ft ends'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def original(o):return o.get('walkthrough_source_name',o.name)
def xyz(x,y,z):return ((x-19383.1)/1000,(10783-y)/1000,z)
fabric=bpy.data.materials.get('Shade | Natural warm linen') or bpy.data.materials.new('Shade | Natural warm linen');fabric.use_nodes=True
p=next(n for n in fabric.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.72,.66,.53,1);p.inputs['Roughness'].default_value=.92
noise=fabric.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=380
bump=fabric.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.0003;fabric.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);fabric.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 old=[o for o in scene.objects if original(o).startswith('Main north') and o.type=='MESH']
 plaster=next(o.data.materials[0] for o in old if '| wall' in original(o));glass=next(o.data.materials[0] for o in old if '| glazing' in original(o));trim=next(o.data.materials[0] for o in old if 'jamb' in original(o))
 for o in old:bpy.data.objects.remove(o,do_unlink=True)
 col=bpy.data.collections.new('Kitchen | Taller awning window and concealed shade');scene.collection.children.link(col)
 def box(name,loc,dims,ma,parent=None,bev=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  if bev:b=o.modifiers.new('Soft edges','BEVEL');b.width=bev;b.segments=3;o.modifiers.new('Face normals','WEIGHTED_NORMAL')
  return o
 wall=doc['walls'][wid];start=wall['start']['x'];y=wall['start']['y'];thick=wall['thickness']/1000;H=2.4384
 def block(a,b,z1,z2,ma=plaster,name='wall'):
  if b-a<.1 or z2-z1<.001:return
  o=box('Main north | '+name,xyz(start+(a+b)/2,y,(z1+z2)/2),((b-a)/1000,thick,z2-z1),ma,bev=0 if ma==plaster else .001);o['source_wall_id']=wid;return o
 cursor=0
 for w in sorted((w for w in doc['windows'].values() if w['wall']==wid),key=lambda w:w['position']):
  target=w['id']==winid;lo=w['position']-w['width']/2;hi=w['position']+w['width']/2;sill,head=(1.476,2.037) if target else (1.,2.1)
  block(cursor,lo,0,H);block(lo,hi,0,sill);header=block(lo,hi,head,H)
  for station in [lo,hi]:
   o=box('Main north opening jamb',xyz(start+station,y,(sill+head)/2),(.024,thick+.045,head-sill+.024),trim);o['source_window_id']=w['id']
  for z in [sill,head]:block(lo-12,hi+12,z-.012,z+.012,trim,'opening trim')
  center=xyz(start+w['position'],y,0);width=w['width']/1000
  if target:
   hinge=bpy.data.objects.new('Operation | Sink awning window - frame 60 open',None);col.objects.link(hinge);hinge.location=(center[0],center[1]+.01,head-.018);hinge['source_window_id']=winid;hinge['operation']='Top hinged outward/upward awning sash; frame 1 closed, frame 60 open';hinge['opening_degrees']=32
   sashh=head-sill-.036;sashw=width-.036
   for x in [-sashw/2+.012,sashw/2-.012]:box('Awning sash | side stile',(x,0,-sashh/2),(.024,.036,sashh),trim,hinge)
   for z in [-.012,-sashh+.012]:box('Awning sash | horizontal rail',(0,0,z),(sashw,.036,.024),trim,hinge)
   pane=box('Main north | glazing',(0,0,-sashh/2),(sashw-.048,.012,sashh-.048),glass,hinge,.0005)
   pane['source_window_id']=winid;pane['clear_width_mm']=w['width'];pane['sill_mm']=1476;pane['head_mm']=2037;pane['height_mm']=561;pane['source_revision']=36
   for frame,angle in [(1,0),(40,0),(60,math.radians(32)),(80,0),(100,0)]:hinge.rotation_euler.x=angle;hinge.keyframe_insert(data_path='rotation_euler',frame=frame)
   # Concealed roller cavity is cut into the header; only a narrow downward slot is exposed.
   cut=box('Temporary recessed shade pocket',(center[0],8.537,2.085),(width-.06,.091,.074),plaster,bev=0)
   bpy.context.view_layer.objects.active=header;mod=header.modifiers.new('Concealed roller pocket','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
   box('Concealed shade | flush plaster pocket fascia',(center[0],8.494,2.085),(width-.06,.014,.074),plaster,bev=0)
   bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.024,depth=width-.08,location=(center[0],8.537,2.085),rotation=(0,math.pi/2,0));roller=bpy.context.object;roller.name='Concealed shade | recessed linen roller';roller.data.materials.append(fabric)
   # Fabric travels through a slim slot on the room side, clear of the outward-opening sash.
   cloth=box('Concealed shade | linen drop - frame 100 lowered',(center[0],8.478,2.031-.006),(width-.065,.0015,.012),fabric,bev=0)
   hem=box('Concealed shade | slim weighted hem',(center[0],8.478,2.019),(width-.065,.008,.010),fabric,bev=.002)
   for frame,length in [(1,.012),(60,.012),(80,.012),(100,.535)]:
    cloth.scale.z=length/.012;cloth.location.z=2.031-length/2;cloth.keyframe_insert(data_path='scale',frame=frame);cloth.keyframe_insert(data_path='location',frame=frame);hem.location.z=2.031-length;hem.keyframe_insert(data_path='location',frame=frame)
   cloth['operation']='Concealed roller blind: frame 1 retracted, frame 100 lowered'
  else:
   pane=box('Main north | glazing',(center[0],center[1],(sill+head)/2),(width,.018,head-sill),glass);pane['source_window_id']=w['id'];pane['sill_mm']=1000;pane['head_mm']=2100
   block(w['position']-12,w['position']+12,sill,head,trim,'mullion')
  cursor=hi
 block(cursor,wall['end']['x']-start,0,H)
 # Keep the appliance clearance animation at frame 40; close appliances for the window/shade demonstrations.
 for o in scene.objects:
  if original(o).startswith('Operation | Oven door hinge'):
   for frame in [60,100]:o.rotation_euler.x=0;o.keyframe_insert(data_path='rotation_euler',frame=frame)
  if original(o).startswith('Operation | Integrated dishwasher drawer'):
   for frame in [60,100]:o.location.y=0;o.keyframe_insert(data_path='location',frame=frame)
 for frame,name in [(60,'AWNING WINDOW OPEN'),(100,'CONCEALED SHADE LOWERED')]:
  mark=scene.timeline_markers.new(name,frame=frame)
 scene.frame_end=max(scene.frame_end,100);scene.frame_set(1);scene['source_revision']=36;scene['sink_window_notes']='2388.6 x 561 mm; sill 1476 / head 2037; top-hinged outward/upward awning sash; concealed linen roller shade. One foot of wall at each end retained. Frame 60 airflow; frame 100 shade.'
 if scene==source:scene.name='Full House | Drawing Revision 36'
 print(scene.name,'window 1.5x height, awning rig and concealed shade added')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Kitchen lantern and daylight'];tour.render.filepath=str(base/'walkthrough/36-taller-awning-window.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+'\nRevision 36: window height increased 1.5x, 374 to 561 mm, keeping sill at 1476 and raising head to 2037. Width 2388.6 and one-foot wall margins retained. Top-hinged outward/upward awning sash animated open at frame 60 (32 degrees); concealed recessed linen roller shade lowered at frame 100. Frame 1 closed/retracted. Full-wall shelf remains.\n')
