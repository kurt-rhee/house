"""Reference-style ribbed paper lantern and brighter, clearer window daylight."""
import bpy,json,uuid,math
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=33
lid=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/paper-lantern-pendant'))
doc['room_labels'][lid]={'id':lid,'name':'Ceiling pendant / paper lantern 560 mm','position':{'x':19173.1,'y':3633}}
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def mat(name,color,rough=.5,metal=0,emission=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if emission:p.inputs['Emission Color'].default_value=(1,.70,.40,1);p.inputs['Emission Strength'].default_value=emission
 return m
paper=mat('Pendant | Warm rice paper',(1,.87,.64),.78,emission=.65)
p=next(n for n in paper.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Subsurface Weight'].default_value=.08
noise=paper.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=180;noise.inputs['Detail'].default_value=2;bump=paper.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.00012;paper.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);paper.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
rib=mat('Pendant | Fine bamboo ribs',(.49,.34,.16),.65,emission=.12);bronze=mat('Pendant | Aged bronze canopy',(.14,.10,.055),.3,.8)
glass=bpy.data.materials['Finish | Clear low iron window glass'];p=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(1,1,1,1);p.inputs['Roughness'].default_value=.008;p.inputs['IOR'].default_value=1.42
# Preserve real glazing while reducing reflected-room dominance in the narrow window.
nt=glass.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
transparent=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.22
nt.links.new(p.outputs['BSDF'],mix.inputs[1]);nt.links.new(transparent.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs['Surface'])
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 col=bpy.data.collections.new('Kitchen | Paper lantern ceiling pendant');scene.collection.children.link(col)
 root=bpy.data.objects.new('Kitchen | Ribbed paper lantern pendant',None);col.objects.link(root);root.location=(-.21,7.15,0);root['source_revision']=33;root['diameter_mm']=560;root['shade_height_mm']=300;root['shade_bottom_mm']=2020;root['ceiling_mount_mm']=2438.4
 def link(o,name,ma):
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=root;o.data.materials.append(ma);return o
 def cylinder(name,loc,radius,depth,ma):
  bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth);o=link(bpy.context.object,name,ma);o.location=loc
  b=o.modifiers.new('Soft turned edges','BEVEL');b.width=.001;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
 def curve(name,points,thickness,ma,closed=False):
  d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=thickness;d.bevel_resolution=3;p=d.splines.new('POLY');p.points.add(len(points)-1)
  for a,v in zip(p.points,points):a.co=(*v,1)
  p.use_cyclic_u=closed;o=bpy.data.objects.new(name,d);col.objects.link(o);o.parent=root;d.materials.append(ma);return o
 cylinder('Lantern | bronze ceiling canopy',(0,0,2.4254),.047,.026,bronze)
 cylinder('Lantern | short suspension',(0,0,2.36525),.003, .0943,bronze)
 # Oblate open-ended shade, made from rings rather than a solid opaque sphere.
 rings=40;segments=96;t0=.16;t1=math.pi-.16;verts=[]
 for j in range(rings+1):
  t=t0+(t1-t0)*j/rings;r=.28*math.sin(t);z=2.17+.15*math.cos(t)
  for i in range(segments):a=2*math.pi*i/segments;verts.append((r*math.cos(a),r*math.sin(a),z))
 faces=[]
 for j in range(rings):
  for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
 mesh=bpy.data.meshes.new('Translucent oblate rice paper lantern');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('Lantern | warm rice paper shade',mesh);col.objects.link(o);o.parent=root;mesh.materials.append(paper)
 for poly in mesh.polygons:poly.use_smooth=True
 for j in range(1,22):
  t=t0+(t1-t0)*j/22;r=.2807*math.sin(t);z=2.17+.1505*math.cos(t)
  curve('Lantern | fine horizontal rib',[(r*math.cos(2*math.pi*i/96),r*math.sin(2*math.pi*i/96),z) for i in range(96)],.00065,rib,True)
 for a in [0,math.pi/2,math.pi,3*math.pi/2]:
  curve('Lantern | meridian seam',[(.281*math.sin(t)*math.cos(a),.281*math.sin(t)*math.sin(a),2.17+.151*math.cos(t)) for t in [t0+(t1-t0)*j/60 for j in range(61)]],.00055,rib)
 for t in [t0,t1]:
  r=.28*math.sin(t);z=2.17+.15*math.cos(t);curve('Lantern | opening rim',[(r*math.cos(2*math.pi*i/96),r*math.sin(2*math.pi*i/96),z) for i in range(96)],.0013,rib,True)
 data=bpy.data.lights.new('Lantern | warm diffuse illumination','POINT');data.energy=24;data.color=(1,.77,.52);data.shadow_soft_size=.18
 light=bpy.data.objects.new(data.name,data);col.objects.link(light);light.parent=root;light.location=(0,0,2.14)
 # Brighter outdoor exposure while retaining photographic HDRI surroundings.
 if scene.world and scene.world.use_nodes:
  bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Strength'].default_value=1.65
 if scene==tour:
  scene.objects['Tour | Kitchen'].data.energy=35;scene.objects['Tour | Kitchen window daylight'].data.energy=110
 scene['source_revision']=33;scene['kitchen_lighting_notes']='560 mm ribbed rice paper lantern, 300 mm high, shade bottom 2020 mm, short bronze suspension to ceiling. Warm diffuse 24 W source. HDRI daylight increased 0.55 to 1.65; clear low-haze glazing with reduced reflected-room dominance.'
 if scene==source:scene.name='Full House | Drawing Revision 33'
 print(scene.name,'paper lantern installed; daylight increased and glazing clarified')
# A wider upward-framed kitchen view includes the ceiling pendant and bright window.
name='Photo | Kitchen lantern and daylight';cam=bpy.data.objects.get(name)
if cam is None:
 data=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,data);tour.collection.objects.link(cam)
cam.location=(.30,5.98,1.62);target=Vector((-.55,7.85,1.78));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=19.5;cam.data.clip_start=.025;cam.data.clip_end=100;cam.data.dof.use_dof=False
for path in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:path.write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=cam;tour.render.filepath=str(base/'walkthrough/33-paper-lantern-brighter-windows.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';text=p.read_text().replace('revision 32','revision 33');text+='\nRevision 33: warm ribbed paper lantern pendant added, diameter 560 mm, height 300 mm, bottom 2020 mm. HDRI daylight strength raised from 0.55 to 1.65, low-haze glazing clarified and reflections reduced, kitchen daylight fill 110 W. Wider camera includes ceiling fixture. Pendant location noted in 2D plan.\n';p.write_text(text)
