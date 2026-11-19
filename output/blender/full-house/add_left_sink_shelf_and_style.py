"""Matching sink shelf and restrained kitchen shelf accessories, revision 14."""
import bpy,json,math,uuid,random
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text())
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'))
tour=bpy.data.scenes['House | Interior walkthrough']
def original(o):return o.get('walkthrough_source_name',o.name)
def material(name,color,rough=.35,metal=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal
 return m
cream=material('Shelf styling | warm porcelain',(.72,.68,.57),.23)
sage=material('Shelf styling | sage glaze',(.19,.28,.22),.23)
clay=material('Shelf styling | terracotta',(.42,.16,.08),.65)
green=material('Shelf styling | herb leaves',(.09,.22,.045),.6)
dark=material('Shelf styling | soil',(.025,.017,.009),.95)
oliv=material('Shelf styling | green olive oil bottle',(.065,.10,.025),.18)
labels=material('Shelf styling | paper labels',(.8,.73,.56),.7)
bookm=[material('Shelf styling | cookbook '+str(i),c,.65) for i,c in enumerate([(.15,.25,.28),(.48,.20,.12),(.68,.59,.38)])]
for scene in [source,tour]:
 bpy.context.window.scene=scene
 right=next(o for o in scene.objects if original(o).startswith('Kitchen | Oak shelf right of sink window'))
 left=right.copy();left.name='Kitchen | Oak shelf left of sink window';scene.collection.objects.link(left);left.location.x=-1.0493
 left['source_fixture_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/sink-window-left-shelf'));left['source_revision']=14;left['placement']='Left of sink window, viewed from inside kitchen';left['drawing_style']='floating_shelf_left_of_sink_window_top_1650mm'
 for child in list(right.children):
  c=child.copy();c.data=child.data.copy();scene.collection.objects.link(c);c.parent=left;c.name=child.name.replace('Sink window shelf','Sink left shelf')
  if 'walkthrough_source_name' in c:del c['walkthrough_source_name']
 col=bpy.data.collections.new('Kitchen | Styled shelf accessories');scene.collection.children.link(col)
 def mesh(name,verts,faces,mat,parent=None):
  d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);col.objects.link(o);o.parent=parent;o.data.materials.append(mat)
  for p in d.polygons:p.use_smooth=True
  return o
 def lathe(name,profile,mat,loc,parent):
  N=64;vs=[(r*math.cos(2*math.pi*i/N),r*math.sin(2*math.pi*i/N),z) for r,z in profile for i in range(N)]
  fs=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(profile)-1) for i in range(N)]
  o=mesh(name,vs,fs,mat,parent);o.location=loc;return o
 def anchor(name,loc,angle=0):
  o=bpy.data.objects.new('Shelf accessories | '+name,None);col.objects.link(o);o.location=loc;o.rotation_euler.z=angle;return o
 def cube(name,loc,dims,mat,parent):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
  b=o.modifiers.new('Rounded edges','BEVEL');b.width=.002;b.segments=3
  return o
 def bowl(parent,x,z=0,r=.095):
  lathe('Styling | ceramic bowl',[(0,.003),(.052,.003),(.060,.012),(r,.063),(r,.068),(r-.006,.068),(.055,.018),(0,.018)],cream,(x,0,z),parent)
 def mug(parent,x,mat=cream):
  lathe('Styling | glazed mug',[(0,0),(.033,0),(.038,.008),(.041,.09),(.04,.096),(.035,.096),(.034,.012),(0,.012)],mat,(x,0,0),parent)
  # Ring handle in a vertical plane with a small tubular cross section.
  vs=[];fs=[];N=48;K=12
  for i in range(N):
   a=i*2*math.pi/N
   for j in range(K):
    b=j*2*math.pi/K;vs.append((x+.044+(.026+.005*math.cos(b))*math.cos(a),.005*math.sin(b),.049+(.026+.005*math.cos(b))*math.sin(a)))
  for i in range(N):
   for j in range(K):fs.append((i*K+j,((i+1)%N)*K+j,((i+1)%N)*K+(j+1)%K,i*K+(j+1)%K))
  mesh('Styling | mug handle',vs,fs,mat,parent)
 def jar(parent,x,h=.17,r=.055,mat=cream):
  lathe('Styling | lidded pantry canister',[(0,0),(r*.85,0),(r,.01),(r,h-.02),(r*.91,h),(0,h)],mat,(x,0,0),parent)
  lathe('Styling | oak canister lid',[(0,0),(r+.002,0),(r+.002,.014),(0,.014)],right.children[0].data.materials[0],(x,0,h),parent)
 def plant(parent,x):
  lathe('Styling | herb pot',[(0,0),(.045,0),(.06,.095),(.063,.10),(.063,.11),(.052,.11),(.05,.095),(0,.095)],clay,(x,0,0),parent)
  lathe('Styling | pot soil',[(0,0),(.05,0)],dark,(x,0,.098),parent)
  random.seed(18)
  for i in range(22):
   a=i*2.4;radius=.02+.035*(i%3)/2;z=.14+.1*(i%5)/4
   bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1)
   o=bpy.context.object
   for c in list(o.users_collection):c.objects.unlink(o)
   col.objects.link(o);o.name='Styling | fresh herb leaf';o.parent=parent;o.location=(x+radius*math.cos(a),radius*math.sin(a),z);o.scale=(.017,.044,.007);o.rotation_euler=(.3,random.uniform(-.7,.7),a);o.data.materials.append(green)
   for p in o.data.polygons:p.use_smooth=True
 a=anchor('left sink shelf',(-1.0493,8.3549,1.65));bowl(a,-.12);bowl(a,-.12,.018);mug(a,.08,sage);mug(a,.19)
 a=anchor('right sink shelf',(.6323,8.3549,1.65));plant(a,.15);jar(a,-.15,.175,.05);jar(a,-.025,.13,.045,sage)
 a=anchor('microwave lower shelf',(-.176556,5.33425,1.476));mug(a,-.21,sage);mug(a,-.08);bowl(a,.14,r=.085)
 a=anchor('microwave upper shelf',(-.176556,5.33425,1.826));jar(a,.16,.18,.055);jar(a,.025,.14,.045,sage)
 for i in range(3):
  x=-.23+i*.035;h=.19+i*.012
  cube('Styling | cookbook pages',(x,0,h/2),(.027,.14,h-.008),labels,a)
  for xx in [x-.016,x+.016]:cube('Styling | cookbook cover',(xx,0,h/2),(.003,.15,h),bookm[i],a)
  cube('Styling | cookbook spine',(x,.075,h/2),(.034,.004,h),bookm[i],a)
 a=anchor('stove prep shelf',(-1.9001,6.305,1.75),math.pi/2)
 lathe('Styling | olive oil bottle',[(0,0),(.035,0),(.038,.01),(.038,.15),(.018,.18),(.014,.19),(.014,.25),(0,.25)],oliv,(-.21,0,0),a)
 lathe('Styling | bottle cap',[(0,0),(.016,0),(.016,.02),(0,.02)],labels,(-.21,0,.25),a)
 jar(a,-.06,.12,.038,sage);jar(a,.05,.13,.038);jar(a,.17,.11,.038,clay)
 scene['source_revision']=14;scene['shelf_styling']='Porcelain bowls and mugs, pantry canisters, herbs, cookbooks and olive oil.'
 if scene==source:scene.name='Full House | Drawing Revision 14'
 bpy.context.view_layer.update()
 assert len(left.children)==len(right.children)
 assert abs(left.location.x+1.0493)<1e-5
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour
tour.camera=bpy.data.objects['Detail | Sink window and right shelf'];tour.render.filepath=str(base/'walkthrough/05-styled-sink-shelves.png')
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='RENDERED'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
print('Revision 14 saved: matching left sink shelf and accessories on all five kitchen shelves, in both scenes.')
