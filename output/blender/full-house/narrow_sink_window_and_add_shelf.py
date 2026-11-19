"""Narrow the centered sink window and add an oak shelf to its interior right."""
import bpy,json,uuid
from pathlib import Path
from mathutils import Vector

base=Path('/Users/kurt/Programs/house/output/blender/full-house')
doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text())
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'))
tour=bpy.data.scenes.get('House | Interior walkthrough')
wid='746ae532-71e5-438a-bc40-f8907c28fcae'
shelf_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/sink-window-right-shelf'))
wall=doc['walls'][wid]

def original_name(o):return o.get('walkthrough_source_name',o.name)
def xyz(x,y,z):return ((x-19383.1)/1000,(10783-y)/1000,z)

for scene in [s for s in [source,tour] if s]:
    bpy.context.window.scene=scene
    old=[o for o in scene.objects if original_name(o).startswith('Main north') and o.type=='MESH']
    plaster=next(o.data.materials[0] for o in old if '| wall' in original_name(o))
    glass=next(o.data.materials[0] for o in old if '| glazing' in original_name(o))
    trim=next(o.data.materials[0] for o in old if 'jamb' in original_name(o))
    oak=next(o.data.materials[0] for o in scene.objects if original_name(o).startswith('Wall shelf | oak floating shelf'))
    for o in old:bpy.data.objects.remove(o,do_unlink=True)
    col=bpy.data.collections.new('Kitchen | Narrow sink window and right shelf')
    scene.collection.children.link(col)

    def box(name,loc,dims,mat,parent=None,bevel=.002):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o=bpy.context.object
        for c in list(o.users_collection):c.objects.unlink(o)
        col.objects.link(o);o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(mat)
        if bevel:
            b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=bevel;b.segments=3
            o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
        return o

    start=wall['start']['x'];y=wall['start']['y'];thick=wall['thickness']/1000;H=2.4384
    def block(a,b,z1,z2,mat=plaster,name='wall'):
        if b-a<.1 or z2-z1<.001:return
        o=box('Main north | '+name,xyz(start+(a+b)/2,y,(z1+z2)/2),((b-a)/1000,thick,z2-z1),mat)
        o['source_wall_id']=wid
        if mat==plaster and scene==source:o['view_wall_opacity']=.2
        return o
    openings=sorted((w for w in doc['windows'].values() if w['wall']==wid),key=lambda w:w['position'])
    cursor=0
    for win in openings:
        lo=win['position']-win['width']/2;hi=win['position']+win['width']/2
        block(cursor,lo,0,H);block(lo,hi,0,1.0);block(lo,hi,2.1,H)
        for station in [lo,hi]:
            o=box('Main north opening jamb',xyz(start+station,y,1.55),(.035,thick+.045,1.135),trim)
            o['source_window_id']=win['id']
        for z in [1.0,2.1]:block(lo-18,hi+18,z-.018,z+.018,trim,'opening trim')
        o=box('Main north | glazing',xyz(start+win['position'],y,1.55),(win['width']/1000,.018,1.1),glass)
        o['source_window_id']=win['id'];o['clear_width_mm']=win['width']
        block(win['position']-12,win['position']+12,1,2.1,trim,'mullion')
        cursor=hi
    block(cursor,wall['end']['x']-start,0,H)

    f=doc['fixtures'][shelf_id]
    root=bpy.data.objects.new('Kitchen | Oak shelf right of sink window',None)
    col.objects.link(root);root.location=xyz(f['origin']['x']+f['width']/2,f['origin']['y'],0)
    root['source_fixture_id']=shelf_id;root['source_revision']=doc['revision'];root['plan_footprint_mm']=[550,280]
    root['shelf_top_mm']=1650;root['placement']='Right of the sink window, viewed from inside the kitchen'
    root['drawing_style']=f['style']
    box('Sink window shelf | oak board',(0,-.14,1.634),(.55,.28,.032),oak,root)
    box('Sink window shelf | wall cleat',(0,-.009,1.598),(.515,.018,.04),oak,root)
    metal=bpy.data.materials['Brushed chrome']
    for x in [-.195,.195]:
        box('Sink window shelf | bracket vertical',(x,-.012,1.557),(.018,.024,.122),metal,root)
        box('Sink window shelf | bracket underside',(x,-.11,1.607),(.018,.22,.019),metal,root)
    scene['source_revision']=doc['revision']
    scene['sink_window_notes']='1000 mm-wide window centered over sink; 550 x 280 mm oak shelf to interior right, top at 1650 mm. Existing window sill and head elevations retained.'
    if scene==source:scene.name='Full House | Drawing Revision '+str(doc['revision'])

(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
if tour:
    bpy.context.window.scene=tour
    data=bpy.data.cameras.new('Detail | Sink window and right shelf');data.lens=26;data.clip_start=.025;data.clip_end=100
    cam=bpy.data.objects.new(data.name,data);tour.collection.objects.link(cam)
    cam.location=(.18,6.55,1.64);cam.rotation_euler=(Vector((-.05,8.49,1.48))-cam.location).to_track_quat('-Z','Y').to_euler()
    tour.camera=cam;tour.render.resolution_x=1500;tour.render.resolution_y=1100
    tour.render.filepath=str(base.parent.parent/'walkthrough'/'04-sink-window-and-shelf.png')
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='RENDERED'
    bpy.ops.wm.save_as_mainfile(filepath=str(base.parent.parent/'walkthrough'/'house-walkthrough.blend'))
print('Window narrowed to 1000 mm; interior-right 550 x 280 mm oak shelf added. Revision',doc['revision'])
