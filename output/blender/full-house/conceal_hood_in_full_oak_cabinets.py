"""Reference-style continuous ceiling-height oak uppers with concealed range hood."""
import bpy, json, math, random, shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());revision=doc['revision']+1
backup=base/'blender'/f'before-oak-hood-revision-{revision}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:
    shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin']
hood_id='cc99b809-cb08-51b4-a631-7c1eae3d9db0'
shelf_id='33ac9591-fe96-5361-867e-89318d0ce11c'
doc['fixtures'].pop(shelf_id,None)
f=doc['fixtures'][hood_id]
f.update(origin={'x':17358.0,'y':5151.4},width=2863.3,depth=380,rotation=270,
    style='ceiling_height_oak_wall_cabinets_concealed_hood_round_window_fixed_panel_bottom_1805mm_top_2438.4mm',
    material='Photographed white oak satin, recessed finger pulls, concealed extractor')
for label in doc['room_labels'].values():
    if label['name'].startswith('Floating shelf:'):label['name']='Stove wall: full-width oak uppers to ceiling'
    elif label['name'].startswith('Architectural hood:'):label['name']='Concealed hood in oak uppers / 1805–2438 mm'

def original(o):return o.get('walkthrough_source_name',o.name)
def oak_uv(o):
    uv=o.data.uv_layers.new(name='Oak physical grain')
    rng=random.Random(o.name);offset=(rng.random()*.7,rng.random()*.5)
    for p in o.data.polygons:
        axis=max(range(3),key=lambda i:abs(p.normal[i]))
        for li in p.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            u,v=((co.y/1.2,co.z/1.6) if axis==0 else ((co.x/1.2,co.z/1.6) if axis==1 else (co.x/1.2,co.y/1.6)))
            uv.data[li].uv=(v+offset[1],u+offset[0])

for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    to_remove=set()
    for o in list(sc.objects):
        if original(o).startswith(('Kitchen | Stove-side floating shelf','Stove shelf |','Shelf accessories | stove prep shelf','Architectural hood | tapered plaster shell')):
            to_remove.add(o);to_remove.update(o.children_recursive)
    for o in to_remove:bpy.data.objects.remove(o,do_unlink=True)
    hood=next(o for o in sc.objects if original(o).startswith('Kitchen | Ceiling-height integrated hood'))
    hood['source_revision']=revision;hood['drawing_style']=f['style'];hood['drawing_material']=f['material']
    hood['extractor_type']='Concealed under oak cabinetry; removable front panels for duct access'
    col=bpy.data.collections.new('Kitchen | Continuous oak stove wall uppers');sc.collection.children.link(col)
    root=bpy.data.objects.new('Kitchen | Full-width ceiling oak hood cabinetry',None);col.objects.link(root)
    root['source_fixture_id']=hood_id;root['source_revision']=revision;root['bottom_mm']=1805;root['top_mm']=2438.4
    root['depth_mm']=380;root['width_mm']=2863.3
    root['construction']='Usable side storage, concealed central extractor/duct, fixed circular-window panel'
    def box(name,x0,x1,y0,y1,z0,z1):
        # Local coordinates around individual panel centers keep physical wood mapping consistent.
        bpy.ops.mesh.primitive_cube_add(size=1,location=((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))
        o=bpy.context.object;o.name='Oak stove uppers | '+name
        for c in list(o.users_collection):c.objects.unlink(o)
        col.objects.link(o);o.parent=root;o.dimensions=(x1-x0,y1-y0,z1-z0)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(wood);oak_uv(o)
        b=o.modifiers.new('Soft oak joinery edges','BEVEL');b.width=.001;b.segments=3
        o.modifiers.new('Weighted cabinet normals','WEIGHTED_NORMAL')
        o['source_revision']=revision
        return o
    rear=-2.0251;front=-1.6451;bottom=1.805;top=2.4384;y0=5.6316;y1=8.4949;t=.018
    boundaries=[y0,6.1016,6.5716,7.1116,7.5716,8.1916,y1]
    # Side/bottom carcasses stop around the extractor and round-window reveal.
    box('ceiling top',rear,front-.018,y0,y1,top-t,top)
    for i,y in enumerate(boundaries):box(f'vertical gable {i+1}',rear,front-.018,y,y+t,bottom,top)
    box('left storage base',rear,front-.018,y0,6.3876,bottom,bottom+t)
    box('right storage base',rear,front-.018,7.2365,y1,bottom,bottom+t)
    window_root=next(o for o in sc.objects if o.name.startswith('Window | Round stove-side aperture'))
    center=window_root['center_height_mm']/1000
    for i,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:])):
        door=box(f'flush oak front {i+1}',front-.018,front,a+.0015,b-.0015,bottom+.002,top-.002)
        door['hardware']='Concealed hinges and recessed underside finger grip; no projecting pull'
        if a<7.83<b:
            door['construction']='Fixed oak panel around circular window, removable for service'
            bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.225,depth=1,location=(-1.85,7.83,center),rotation=(0,math.pi/2,0))
            cutter=bpy.context.object
            bpy.ops.object.select_all(action='DESELECT');door.select_set(True);bpy.context.view_layer.objects.active=door
            mod=door.modifiers.new('Round window through oak front','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
            solvers=[e.identifier for e in mod.bl_rna.properties['solver'].enum_items]
            if 'EXACT' in solvers:mod.solver='EXACT'
            # Apply the cut before the finishing bevels.
            bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_move_up(modifier=mod.name)
            bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
            assert len(door.data.polygons)>20
            oak_uv(door)
    # Extend the continuous bronze window lining through the cabinet to its flush front.
    frame=next(o for o in sc.objects if o.name.startswith('Round stove window | slim bronze frame'))
    for v in frame.data.vertices:
        if v.co.x>-2.1:v.co.x=front+.012
    frame.data.update();frame['reveal_depth_mm']=560
    window_root['surround']='Fixed white oak cabinet panel with bronze-lined clear circular reveal'
    sc['source_revision']=revision
    sc['hood_notes']='Range hood fully concealed in full-width ceiling-height white oak cabinetry; filters and warm task lights visible only underneath.'
    sc['kitchen_shelf_notes']='Stove-side floating shelf removed; sink-wall window shelf retained'
    bpy.context.view_layer.update()
    assert not any(original(o).startswith('Architectural hood | tapered plaster shell') for o in sc.objects)
    assert abs(max((o.matrix_world@Vector(c)).z for o in col.objects if o.type=='MESH' for c in o.bound_box)-top)<1e-5
    print(sc.name,'oak uppers added, plaster hood and stove shelf removed, window remains clear')

doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour
for w in bpy.context.window_manager.windows:
    for a in w.screen.areas:
        if a.type=='VIEW_3D':a.spaces.active.shading.type='RENDERED'
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {revision}: full-width 2863.3 x 380 mm white oak wall uppers, bottom 1805 / ceiling 2438.4 mm. Concealed existing extractor, filters and warm task lights; exposed plaster hood removed. Stove shelf and accessories removed. Bronze circular reveal extends through fixed oak window panel. Full-height-to-hood soapstone and warm lighting retained. 2D fixture and notes synchronized.\n')
