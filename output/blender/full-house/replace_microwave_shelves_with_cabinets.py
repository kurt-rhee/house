"""Replace the microwave's two open shelves with stacked enclosed oak wall cabinets."""
import bpy,json,random
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=22
fid='e1928df0-155f-546e-b491-516387590509'
f=doc['fixtures'][fid];f['style']='two_stacked_enclosed_oak_wall_cabinets_bottom_1444mm_top_2144mm_depth_280mm';f['material']='Natural white oak, satin finish, satin nickel pulls'
for label in doc['room_labels'].values():
 if label.get('name')=='Microwave cabinet + two deeper oak shelves':label['name']='Microwave + two stacked oak wall cabinets'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin'];metal=bpy.data.materials['Finish | Satin brushed nickel']
def original(o):return o.get('walkthrough_source_name',o.name)
def oak_uv(o):
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co
   u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
   uv.data[li].uv=(u+off[0],v+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 cabinet=next(o for o in scene.objects if original(o)=='Kitchen | Counter-height cabinet beside fridge')
 old=[o for o in scene.objects if original(o).startswith(('Wall shelf |','Microwave upper shelf |')) or (o.type=='EMPTY' and original(o).lower().startswith('shelf accessories | microwave'))]
 for o in old:
  for child in list(o.children_recursive):bpy.data.objects.remove(child,do_unlink=True)
  bpy.data.objects.remove(o,do_unlink=True)
 for key in ['shelf_depth_mm','shelf_top_heights_mm','shelf_count']:
  if key in cabinet:del cabinet[key]
 col=bpy.data.collections.new('Kitchen | Stacked microwave wall cabinets');scene.collection.children.link(col)
 root=bpy.data.objects.new('Kitchen | Two stacked oak cabinets above microwave',None);col.objects.link(root);root.parent=cabinet
 root['source_fixture_id']=fid;root['source_revision']=22;root['plan_footprint_mm']=[622.1125,280];root['drawing_style']=f['style'];root['cabinet_count']=2;root['bottom_mm']=1444;root['top_mm']=2144
 def box(name,loc,dims,ma=wood):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name='Microwave wall cabinets | '+name;o.parent=root;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  mod=o.modifiers.new('Soft joinery edges','BEVEL');mod.width=.001;mod.segments=3;o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
  if ma==wood:oak_uv(o)
  return o
 w=.6221125;t=.018
 for i in range(2):
  bottom=1.444+i*.35;top=bottom+.35;mid=(bottom+top)/2
  for x in [t/2,w-t/2]:box(f'{i+1} side',(x,.131,mid),(t,.262,.35))
  for z in [bottom+t/2,top-t/2]:box(f'{i+1} base or top',(w/2,.131,z),(w-2*t,.262,t))
  box(f'{i+1} back',(w/2,.006,mid),(w-2*t,.012,.35-2*t))
  door=box(f'{i+1} closed slab door',(w/2,.271,mid),(w-.003,.018,.347));door['construction']='Closed white oak door, concealed hinges, 3 mm reveals'
  # Slim satin nickel horizontal pull, mounted above lower door edge.
  box(f'{i+1} pull',(w/2,.309,bottom+.062),(.128,.012,.009),metal)
  for x in [w/2-.05,w/2+.05]:box(f'{i+1} pull post',(x,.291,bottom+.062),(.009,.026,.009),metal)
 scene['source_revision']=22;scene['microwave_wall_cabinet_notes']='Two stacked enclosed white oak wall cabinets above microwave; total 622.1125 x 280 x 700 mm, bottom 1444 and top 2144 mm; matching satin nickel pulls.'
 scene['kitchen_shelf_notes']='One long floating shelf right of sink and one stove-side floating shelf with knife bar. Microwave shelves replaced with two stacked enclosed oak wall cabinets.'
 assert not any(original(o).startswith(('Wall shelf |','Microwave upper shelf |')) for o in scene.objects)
 if scene==source:scene.name='Full House | Drawing Revision 22'
 print(scene.name,'two enclosed cabinets created, open shelves and styling removed')
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:path.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Fridge and microwave shelves'];tour.render.filepath=str(base/'walkthrough/18-microwave-wall-cabinets.png')
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
notes=base/'walkthrough/RENDER-NOTES.txt';text=notes.read_text().replace('revision 21','revision 22').replace('Four floating shelves: one 1100 x 280 mm shelf to the right of sink/window, two above microwave and one beside stove.','Two floating shelves: one 1100 x 280 mm shelf to the right of sink/window and one beside stove. Above the microwave: two stacked enclosed oak cabinets, 622.1125 mm wide x 280 mm deep, bottom 1444 mm / top 2144 mm, closed slab doors and satin nickel pulls.')
notes.write_text(text)
