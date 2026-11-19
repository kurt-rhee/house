"""Warm white glazed ceramic backsplash, clipped to window trim and counter runs."""
import bpy,json,math,uuid,random
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=19
ident=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/backsplash-finish-note'))
doc['room_labels'][ident]={'id':ident,'name':'Backsplash: warm white 100 x 200 mm ceramic tile','position':{'x':22400,'y':5850}}
(base/'floor-plan.house.json').write_text(json.dumps(doc,indent=2)+'\n')
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def material(name,color,rough):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
 return m,p
variants=[]
for i in range(5):
 v=(i-2)*.008;m,p=material('Backsplash | Warm white glaze '+str(i),(.75+v,.725+v,.665+v),.24+i*.016)
 p.inputs['Coat Weight'].default_value=.24;p.inputs['Coat Roughness'].default_value=.20
 n=m.node_tree.nodes;l=m.node_tree.links;t=n.new('ShaderNodeTexNoise');t.inputs['Scale'].default_value=110;t.inputs['Detail'].default_value=2
 b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.12;b.inputs['Distance'].default_value=.00012;l.new(t.outputs['Fac'],b.inputs['Height']);l.new(b.outputs['Normal'],p.inputs['Normal']);variants.append(m)
grout,_=material('Backsplash | Warm pale grout',(.43,.415,.37),.9)
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 col=bpy.data.collections.new('Kitchen | Warm white ceramic backsplash');scene.collection.children.link(col)
 def box(name,loc,dims,ma,parent=None,bevel=.0007):
  bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
  if bevel:
   b=o.modifiers.new('Soft glazed tile edges','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
  return o
 def subtract(rect,cut):
  a,b,c,d=rect;x1,x2,z1,z2=cut;lo=max(a,x1);hi=min(b,x2);bottom=max(c,z1);top=min(d,z2)
  if lo>=hi or bottom>=top:return [rect]
  parts=[(a,lo,c,d),(hi,b,c,d),(lo,hi,c,bottom),(lo,hi,top,d)]
  return [r for r in parts if r[1]-r[0]>.0005 and r[3]-r[2]>.0005]
 counts=[]
 def panel(name,origin,angle,length,zmax,holes=(),face=-1,start=0):
  root=bpy.data.objects.new('Backsplash | '+name,None);col.objects.link(root);root.location=origin;root.rotation_euler.z=angle
  root['finish']='Warm off-white glazed ceramic, horizontal running bond, 100 x 200 mm, 2 mm warm pale grout';root['source_revision']=19;root['tile_thickness_mm']=8
  zmin=.9365;rects=[(start,length,zmin,zmax)]
  for hole in holes:rects=[rr for r in rects for rr in subtract(r,hole)]
  for a,b,c,d in rects:box('Backsplash | grout bed',((a+b)/2,face*.0015,(c+d)/2),(b-a,.003,d-c),grout,root,0)
  count=0;row=0;z=zmin
  rng=random.Random(name)
  while z<zmax-.001:
   nextz=min(z+.10,zmax);x=start-(.10 if row%2 else 0)
   while x<length-.001:
    a=max(start,x+.001);b=min(length,x+.199)
    if b-a>.002:
     pieces=[(a,b,z+.001,nextz-.001)]
     for hole in holes:pieces=[rr for r in pieces for rr in subtract(r,hole)]
     for a1,b1,c1,d1 in pieces:
      if b1-a1<.003 or d1-c1<.003:continue
      ob=box('Backsplash | glazed ceramic tile',((a1+b1)/2,face*.006,(c1+d1)/2),(b1-a1,.008,d1-c1),rng.choice(variants),root)
      ob['backsplash_tile']=True;count+=1
    x+=.20
   z+=.10;row+=1
  counts.append(count);return root
 # North face spans the L-shaped counter including its corner. Window trim remains exposed.
 panel('Sink and north counter',(-2.0251,8.4949,0),0,2.9982,1.65,[(.6894,1.7244,.982,2.12)])
 # West counter return; tile runs to 1750 mm and up to the hood behind the range.
 # West window stations are relative to the counter back at drawing Y2288.1.
 west_window=(.165525,.965375,.986,2.12)
 panel('West counter return',(-2.0251,8.4949,0),-math.pi/2,3.01565,1.75,[west_window],face=1)
 panel('Induction range hood infill',(-2.0251,8.4949,0),-math.pi/2,2.063825,1.805,[(1.301825,2.063825,.9365,1.75)],face=1,start=1.301825)
 # Above the counter-height microwave cabinet, below its first floating shelf.
 panel('Microwave counter',(-.4876125,5.19425,0),0,.6221125,1.444,face=1)
 scene['source_revision']=19;scene['backsplash_notes']='Warm off-white glazed 100 x 200 mm ceramic tiles, running bond, 2 mm pale grout. Sink wall to 1650 mm; west wall to 1750 mm, range infill to hood underside at 1805 mm; microwave counter to underside of lower shelf. Openings trimmed clear.'
 if scene==source:scene.name='Full House | Drawing Revision 19'
 assert sum(counts)>200
 print(scene.name,'backsplash tile pieces by surface:',counts)
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Sink and floating shelves'];tour.render.filepath=str(base/'walkthrough/12-kitchen-backsplash.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
