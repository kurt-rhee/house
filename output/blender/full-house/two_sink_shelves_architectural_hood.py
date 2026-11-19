"""Two full-span sink shelves and a ceiling-integrated tapered plaster extractor hood."""
import bpy,bmesh,json,uuid
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=30
sid='90d62899-1317-5cc7-a110-a6c6b9d14fbb';uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/second-full-span-sink-shelf'));hid='cc99b809-cb08-51b4-a631-7c1eae3d9db0'
f=dict(doc['fixtures'][sid]);f['id']=uid;f['origin']=dict(f['origin']);f['style']='upper_floating_shelf_window_trim_to_right_wall_top_1800mm_concealed_supports';doc['fixtures'][uid]=f
hood=doc['fixtures'][hid];hood['width']=850;hood['depth']=480;hood['origin']['y']=4395.925;hood['style']='architectural_tapered_plaster_hood_bottom_1805mm_top_2438.4mm_ceiling_height_concealed_extractor';hood['material']='Warm ivory mineral plaster, concealed satin nickel extractor'
for label in doc['room_labels'].values():
 if label['name'].startswith('Integrated hood:'):label['name']='Architectural hood: tapered plaster to ceiling'
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
plaster=bpy.data.materials.get('Hood | Warm mineral plaster')
if plaster is None:
 plaster=bpy.data.materials['Tour | Warm ivory plaster'].copy();plaster.name='Hood | Warm mineral plaster'
 p=next(n for n in plaster.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Roughness'].default_value=.76
 noise=plaster.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=95;noise.inputs['Detail'].default_value=2
 bump=plaster.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.00025
 plaster.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);plaster.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==sid)
 board=next(o for o in root.children if o.type=='MESH')
 upper=bpy.data.objects.new('Kitchen | Upper full-span sink floating shelf',None);root.users_collection[0].objects.link(upper);upper.location=root.location.copy()
 upper['source_fixture_id']=uid;upper['source_revision']=30;upper['shelf_top_mm']=1800;upper['plan_footprint_mm']=[1273.7,280];upper['drawing_style']=f['style']
 shelf=board.copy();shelf.data=board.data.copy();board.users_collection[0].objects.link(shelf);shelf.name='Sink upper shelf | floating oak board';shelf.parent=upper;shelf.location=board.location.copy();shelf.location.z+=.35
 shelf['construction']='Floating shelf, concealed supports';shelf['source_fixture_id']=uid
 for o in scene.objects:
  if o.type=='EMPTY' and o.name.startswith('Shelf accessories | Long sink shelf canisters and herbs'):o.location.z=1.8
 h=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==hid)
 for o in list(h.children):
  if any(k in o.name for k in ['oak','cabinet back','shadow reveal behind fronts']):bpy.data.objects.remove(o,do_unlink=True)
 # Tapered plaster shell, open below for the retained extractor insert.
 x0,x1=-.044,.806;tx0,tx1=.081,.681;z0,z1=1.805,2.4384
 verts=[(x0,0,z0),(x1,0,z0),(x1,-.48,z0),(x0,-.48,z0),(tx0,0,z1),(tx1,0,z1),(tx1,-.30,z1),(tx0,-.30,z1),(.08,-.065,z0),(.682,-.065,z0),(.682,-.365,z0),(.08,-.365,z0)]
 faces=[(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),(4,7,6,5),(0,1,9,8),(1,2,10,9),(2,3,11,10),(3,0,8,11)]
 mesh=bpy.data.meshes.new('Architectural tapered mineral plaster hood');mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 shell=bpy.data.objects.new('Architectural hood | tapered plaster shell',mesh);h.users_collection[0].objects.link(shell);shell.parent=h;mesh.materials.append(plaster)
 bevel=shell.modifiers.new('Soft plaster arrises','BEVEL');bevel.width=.003;bevel.segments=3;shell.modifiers.new('Weighted plaster normals','WEIGHTED_NORMAL')
 h['source_revision']=30;h['plan_footprint_mm']=[850,480];h['drawing_style']=hood['style'];h['drawing_material']=hood['material']
 scene['source_revision']=30;scene['kitchen_shelf_notes']='Two full-span sink floating oak shelves, each 1273.7 x 280 x 32 mm, tops 1450 and 1800 mm; concealed supports. Stove-side shelf retained. Two enclosed cabinets above microwave retained.'
 scene['hood_notes']='Ceiling-integrated warm ivory plaster hood: tapered 850 x 480 mm base to 600 x 300 mm ceiling top. Bottom 1805 mm, ceiling 2438.4 mm. Concealed extractor, metal filters and warm task lights retained.'
 if scene==source:scene.name='Full House | Drawing Revision 30'
 print(scene.name,'second full-span floating shelf and tapered architectural plaster hood created')
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/28-architectural-plaster-hood.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 29','revision 30');text+='\nRevision 30: reference-inspired architectural tapered ivory plaster hood to ceiling replaces oak enclosure, with concealed extractor and lights retained. Two full-span oak sink shelves, tops 1450 / 1800 mm; canisters and plant styling moved to upper shelf. Microwave enclosed cabinets remain.\n';p.write_text(text)
