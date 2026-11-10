import bpy,math,json,os,datetime
from mathutils import Vector
OUT='/Users/kurt/Programs/house/output/blender/kitchen-revision-4'
os.makedirs(OUT,exist_ok=True);doc=json.load(open(OUT+'/drawing-snapshot.json'))
bpy.ops.scene.new(type='FULL_COPY');s=bpy.context.scene;s.name='Full House | Kitchen Revision 4'
col=bpy.data.collections.new('Kitchen revision 4');s.collection.children.link(col)
oldids=['183896d6-5d51-4bd2-a620-8d771ae4c6c3','183896d6-5d61-4bd2-a620-8d771ae4c6c3','f59c3e90-5761-4814-978d-baebc0243feb']
for o in list(s.objects):
 if o.get('source_wall_id') in oldids or o.name.startswith(('Kitchen west opening jamb','Laundry east doorway opening jamb')):bpy.data.objects.remove(o,do_unlink=True)
plaster=bpy.data.materials['Warm white plaster'];trim=bpy.data.materials['Window and door trim'];glass=bpy.data.materials['Window frosted glazing'];chrome=bpy.data.materials['Brushed chrome']
def xyz(x,y,z):return ((x-19383.1)/1000,-(y-10783)/1000,z)
def cube(name,loc,dim,ma):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.data.materials.append(ma);mod=o.modifiers.new('Soft edges','BEVEL');mod.width=.003;mod.segments=2;o.modifiers.new('Corner normals','WEIGHTED_NORMAL');return o
# Rebuild both affected host walls with their revision 4 openings.
for wid in ['ad218721-76be-4635-81dc-048de2d8bdae','743fa984-048d-48a9-923a-a99198a7c60e']:
 w=doc['walls'][wid];x,y=w['start']['x'],w['start']['y'];L=w['end']['y']-y;t=w['thickness']/1000
 def part(lo,hi,z1,z2,ma=plaster,label='wall'):
  if hi-lo<.01 or z2-z1<.0001:return
  o=cube(w['name']+' | '+label,xyz(x,y+(lo+hi)/2,(z1+z2)/2),(t,(hi-lo)/1000,z2-z1),ma);o['source_wall_id']=wid;return o
 ops=[]
 for category in ['windows','doors']:
  for op in doc[category].values():
   if op['wall']==wid:ops.append((op['position']-op['width']/2,op['position']+op['width']/2,category,op))
 cursor=0
 for a,b,category,op in sorted(ops):
  z1,z2=(1,2.1) if category=='windows' else (0,2.032)
  part(cursor,a,0,2.4387);part(a,b,0,z1);part(a,b,z2,2.4387);cursor=b
  for station in [a,b]:
   o=cube(w['name']+' | opening jamb',xyz(x,y+station,(z1+z2)/2),(t+.035,.035,z2-z1+.035),trim);o['source_wall_id']=wid
  for z in ([z1,z2] if category=='windows' else [z2]):part(a-18,b+18,z-.018,z+.018,trim,'trim')
  if category=='windows':
   o=part(a,b,z1,z2,glass,'glazing');o.dimensions.x=.018
   part((a+b)/2-12,(a+b)/2+12,z1,z2,trim,'window mullion')
  else:
   # Closed double French glass doors show the newly widened opening.
   for i in range(2):
    lo=a+i*(b-a)/2;hi=a+(i+1)*(b-a)/2
    for station in [lo+22.5,hi-22.5]:
     o=cube('French door vertical stile',xyz(x,y+station,1.016),(.045,.045,2.014),trim);o['source_door_id']=op['id']
    for z in [.065,1.015,1.97]:
     o=cube('French door rail',xyz(x,y+(lo+hi)/2,z),(.045,(hi-lo)/1000-.065,.07),trim);o['source_door_id']=op['id']
    for za,zb in [(.105,.98),(1.05,1.935)]:
     o=cube('French door glass',xyz(x,y+(lo+hi)/2,(za+zb)/2),(.012,(hi-lo)/1000-.09,zb-za),glass);o['source_door_id']=op['id']
    station=hi-90 if i==0 else lo+90
    cube('French door handle',xyz(x+43,y+station,1.02),(.035,.10,.017),chrome)
 part(cursor,L,0,2.4387)
# Resize the entire west cabinet run and all its cabinet seam details from its root.
f=doc['fixtures']['c08078d4-006c-4eba-8032-0bf18c432cec']
for o in s.objects:
 if o.get('source_fixture_id')==f['id']:
  o.scale.y=f['depth']/3030;o['plan_depth_mm']=f['depth']
f=doc['fixtures']['f6bd213e-4f0b-4b20-8167-2b0e1436cc5a']
for o in s.objects:
 if o.get('source_fixture_id')==f['id']:o.location=xyz(f['origin']['x'],f['origin']['y'],0);o.rotation_euler.z=-math.radians(f['rotation'])
# Make the changed wall and double doors the focus, looking from the dining side.
d=bpy.data.cameras.new('Revision 4 | West kitchen and French doors');d.type='ORTHO';d.ortho_scale=6.1;cam=bpy.data.objects.new(d.name,d);col.objects.link(cam);cam.location=xyz(22700,3550,6.9);target=Vector(xyz(17750,4630,1.0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();d.clip_end=200
s['source_revision']=4;s['revision_4_changes']='Laundry French glass doors 1397.7mm wide; west counter depth 2665.65mm; range moved north 182.175mm.'
for o in s.objects:
 if o.type=='FONT':o.hide_render=True
s.render.resolution_x=1800;s.render.resolution_y=1500;s.cycles.samples=24;s.camera=cam;s.render.filepath=OUT+'/01-changed-kitchen-wall.png'
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=OUT+'/house-kitchen-revision-4.blend')
bpy.ops.render.render(write_still=True)
print('Revision 4 changed-wall render saved',OUT)
