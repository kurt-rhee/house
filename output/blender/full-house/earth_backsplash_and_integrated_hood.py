"""Earth-tone tile and an oak integrated extractor enclosure extending to the ceiling."""
import bpy,json,uuid,random,math
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=20
fid='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a';hoodid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/ceiling-height-integrated-hood'))
stove=doc['fixtures'][fid]
doc['fixtures'][hoodid]={'id':hoodid,'kind':'OverheadCabinet','origin':dict(stove['origin']),'width':762,'depth':440,'rotation':270,'layer':stove['layer'],'style':'integrated_extractor_in_oak_cabinet_bottom_1805mm_top_2438.4mm_ceiling_height','material':'Natural white oak enclosure, concealed satin nickel extractor'}
labelid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/backsplash-finish-note'))
doc['room_labels'][labelid]['name']='Backsplash: earth-toned clay / taupe ceramic tile'
labelid2=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/ceiling-height-hood-note'))
doc['room_labels'][labelid2]={'id':labelid2,'name':'Integrated hood: oak enclosure to ceiling','position':{'x':22400,'y':6100}}
(base/'floor-plan.house.json').write_text(json.dumps(doc,indent=2)+'\n')
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin'];metal=bpy.data.materials['Finish | Satin brushed nickel'];dark=bpy.data.materials['Finish | Deep cabinet reveals']
colors=[(.315,.223,.157),(.34,.245,.175),(.365,.267,.193),(.335,.248,.188),(.38,.285,.21)]
for i,c in enumerate(colors):
 m=bpy.data.materials['Backsplash | Warm white glaze '+str(i)];p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.31+i*.012;p.inputs['Coat Weight'].default_value=.17
 # Keep material identifiers stable for editing and record the revised finish explicitly.
 m['finish']='Earth tone: muted clay, taupe and sand glazed ceramic';m.diffuse_color=(*c,1)
m=bpy.data.materials['Backsplash | Warm pale grout'];p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.245,.205,.16,1);m['finish']='Warm taupe grout'
led=bpy.data.materials.get('Hood | Warm LED diffuser') or bpy.data.materials.new('Hood | Warm LED diffuser');led.use_nodes=True
p=next(n for n in led.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(.9,.83,.65,1);p.inputs['Emission Color'].default_value=(1,.83,.57,1);p.inputs['Emission Strength'].default_value=2
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 old=[o for o in root.children if o.get('walkthrough_source_name',o.name).startswith('Range hood')]
 for o in old:bpy.data.objects.remove(o,do_unlink=True)
 col=bpy.data.collections.new('Kitchen | Ceiling-height oak integrated hood');scene.collection.children.link(col)
 hood=bpy.data.objects.new('Kitchen | Ceiling-height integrated hood',None);col.objects.link(hood);hood.parent=root
 hood['source_fixture_id']=hoodid;hood['source_revision']=20;hood['plan_footprint_mm']=[762,440];hood['drawing_style']=doc['fixtures'][hoodid]['style'];hood['drawing_material']=doc['fixtures'][hoodid]['material'];hood['bottom_mm']=1805;hood['top_mm']=2438.4;hood['extractor_type']='Concealed integrated insert with underside filters and warm task lighting'
 def uv(o):
  layer=o.data.uv_layers.active or o.data.uv_layers.new(name='Oak | physical grain scale');rng=random.Random(o.name);a,b=rng.random()*.6,rng.random()*.4
  for p in o.data.polygons:
   axis=max(range(3),key=lambda i:abs(p.normal[i]))
   for li in p.loop_indices:
    v=o.data.vertices[o.data.loops[li].vertex_index].co;x,y,z=[v[i]*o.scale[i] for i in range(3)]
    u,vv=((x/1.2,y/1.6) if axis==2 else ((y/1.2,z/1.6) if axis==0 else (x/1.2,z/1.6)))
    layer.data[li].uv=(u+a,vv+b)
 def box(name,loc,dims,ma=wood,bevel=.001):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=hood;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  if bevel:
   b=o.modifiers.new('Fine cabinet edge highlights','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
  if ma==wood:uv(o)
  return o
 low=1.805;high=2.4384;h=high-low
 for x in [.009,.753]:box('Integrated hood | oak side panel',(x,-.211,(low+high)/2),(.018,.422,h))
 box('Integrated hood | oak cabinet top to ceiling',(.381,-.211,high-.009),(.726,.422,.018))
 box('Integrated hood | cabinet back',(.381,-.006,(low+high)/2),(.726,.012,h),dark)
 box('Integrated hood | shadow reveal behind fronts',(.381,-.418,(low+high)/2),(.726,.012,h-.02),dark)
 for x in [.1905,.5715]:box('Integrated hood | handleless oak front',(x,-.431,(low+high)/2),(.377,.018,h-.003))
 # Oak perimeter conceals the extractor frame; two inset metal filters remain underneath.
 for x in [.0405,.7215]:box('Integrated hood | oak underside perimeter',(x,-.22,low+.009),(.081,.44,.018))
 for y in [-.035,-.405]:box('Integrated hood | oak underside perimeter',(.381,y,low+.009),(.60,.07,.018))
 box('Integrated hood | concealed extractor chassis',(.381,-.22,low+.035),(.598,.298,.065),metal)
 for x in [.232,.530]:
  box('Integrated hood | inset grease filter',(x,-.22,low-.001),(.278,.272,.004),dark,.001)
  for i in range(13):box('Integrated hood | fine filter slat',(x,-.344+i*.020,low-.0035),(.266,.004,.002),metal,.0005)
 for x in [.105,.657]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.013,depth=.002)
  o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name='Integrated hood | warm task light';o.parent=hood;o.location=(x,-.375,low-.002);o.data.materials.append(led)
  data=bpy.data.lights.new('Integrated hood | concealed downlight','AREA');data.energy=2.5;data.shape='DISK';data.size=.06;data.color=(1,.88,.70)
  light=bpy.data.objects.new(data.name,data);col.objects.link(light);light.parent=hood;light.location=(x,-.34,low-.008);light.visible_camera=False;light.visible_glossy=False;light.visible_transmission=False
 for o in scene.objects:
  if o.name.startswith('Backsplash |') and o.type=='EMPTY':o['finish']='Earth-toned clay / taupe glazed ceramic, 100 x 200 mm running bond, 2 mm warm taupe grout';o['source_revision']=20
 scene['source_revision']=20;scene['backsplash_notes']='Earth-toned clay, taupe and sand glazed ceramic tiles with warm taupe grout; running bond; existing backsplash extents retained.'
 scene['hood_notes']='Integrated extractor concealed within handleless white oak cabinetry; enclosure bottom 1805 mm, top 2438.4 mm flush with ceiling, nominal 762 x 440 mm footprint.'
 if scene==source:scene.name='Full House | Drawing Revision 20'
 bpy.context.view_layer.update()
 top=next(o for o in hood.children if 'cabinet top' in o.name)
 assert abs(max((top.matrix_world@__import__('mathutils').Vector(v)).z for v in top.bound_box)-2.4384)<1e-5
 assert len(old)==1
 print(scene.name,'earth-tone backsplash; hood top 2438.4 mm at ceiling; integrated extractor hidden beneath oak.')
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/14-earth-backsplash-integrated-hood.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
