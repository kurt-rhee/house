"""Recess microwave upper cabinets and clad the back wall in full-height soapstone."""
import bpy,json,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=34
fid='e1928df0-155f-546e-b491-516387590509';f=doc['fixtures'][fid];f['depth']=350;f['origin']['y']=5217.75;f['style']='two_stacked_recessed_oak_uppers_depth_350mm_bottom_1444mm_top_2438.4mm_ceiling_height_recessed_edge_grips';f['material']='Natural white oak, concealed edge grips, full-height soapstone behind'
for label in doc['room_labels'].values():
 if label['name'].startswith('Microwave:'):label['name']='Microwave: recessed uppers / full-height soapstone'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough'];stone=bpy.data.materials['Kitchen | Honed charcoal soapstone']
def oak_uv(o):
 uv=o.data.uv_layers.active;rng=random.Random(o.name);off=(rng.random()*.6,rng.random()*.4)
 for p in o.data.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]))
  for li in p.loop_indices:
   x,y,z=o.data.vertices[o.data.loops[li].vertex_index].co;u,v=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)));uv.data[li].uv=(u+off[0],v+off[1])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 base_root=root.parent;door=next(o for o in root.children if 'closed slab door' in o.name)
 oldfront=door.location.y+max(v.co.y for v in door.data.vertices);delta=.35-oldfront
 for o in root.children:
  if 'side' in o.name or 'base or top' in o.name:
   oldsize=max(v.co.y for v in o.data.vertices)-min(v.co.y for v in o.data.vertices)
   for v in o.data.vertices:v.co.y*=(oldsize+delta)/oldsize
   o.location.y+=delta/2;o.data.update();oak_uv(o)
  elif 'closed slab door' in o.name or 'pull' in o.name:o.location.y+=delta
 root.location.y=.021
 root['source_revision']=34;root['depth_mm']=350;root['plan_footprint_mm']=[622.1125,350];root['drawing_style']=f['style'];root['counter_front_clearance_mm']=289.4
 col=bpy.data.collections.new('Kitchen | Full-height microwave soapstone');scene.collection.children.link(col)
 bpy.ops.mesh.primitive_cube_add(size=1);slab=bpy.context.object
 for c in list(slab.users_collection):c.objects.unlink(slab)
 col.objects.link(slab);slab.name='Backsplash | Full-height microwave soapstone';slab.parent=base_root;slab.location=(.31105625,.011,(.9325+2.4384)/2);slab.dimensions=(.6221125,.020,2.4384-.9325)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);slab.data.materials.append(stone)
 b=slab.modifiers.new('Eased soapstone edges','BEVEL');b.width=.0012;b.segments=3;slab.modifiers.new('Weighted slab normals','WEIGHTED_NORMAL');slab['source_revision']=34;slab['bottom_mm']=932.5;slab['top_mm']=2438.4;slab['finish']='Continuous honed soapstone from countertop to ceiling, behind recessed upper cabinetry'
 bpy.context.view_layer.update()
 front=max((root.matrix_world.inverted()@door.matrix_world@Vector(v)).y for v in door.bound_box);assert abs(front-.35)<1e-5
 top=max((slab.matrix_world@Vector(v)).z for v in slab.bound_box);assert abs(top-2.4384)<1e-5
 scene['source_revision']=34;scene['microwave_wall_cabinet_notes']='Microwave upper cabinets recessed to 350 mm depth, on 21 mm stone finish offset; front plane 371 mm from rear wall, 289.4 mm behind counter front. Original microwave and base cabinet depth retained. Soapstone back wall from countertop 932.5 mm continuously to ceiling 2438.4 mm, behind upper cabinets.'
 if scene==source:scene.name='Full House | Drawing Revision 34'
 print(scene.name,'upper cabinet depth 350 mm; counter setback 289.4 mm; soapstone verified to ceiling')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Fridge and microwave shelves'];tour.render.filepath=str(base/'walkthrough/34-recessed-microwave-uppers-soapstone.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 33','revision 34');text+='\nRevision 34: microwave upper cabinets recessed to 350 mm depth, mounted over 21 mm rear stone finish offset; front 289.4 mm behind counter edge. Full-height 20 mm soapstone rear-wall slab runs from countertop 932.5 mm to ceiling 2438.4 mm, continuing behind upper cabinets. Base and microwave remain at fridge depth.\n';p.write_text(text)
