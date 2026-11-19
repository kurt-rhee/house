"""Continuous shelf/cabinet/hood line and aligned round/rectangular window centers."""
import bpy, json, math, shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());revision=doc['revision']+1
backup=base/'blender'/f'before-continuous-shelf-revision-{revision}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']
wood=bpy.data.materials['Finish | Photographed white oak satin']
hood_id='cc99b809-cb08-51b4-a631-7c1eae3d9db0'
shelf_id='33ac9591-fe96-5361-867e-89318d0ce11c'

def bounds(o):
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    return [(min(p[i] for p in bb),max(p[i] for p in bb)) for i in range(3)]
def cubemesh(name,b,inv=None):
    x,y,z=b
    v=[Vector((x[i],y[j],z[k])) for i,j,k in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
    if inv is not None:v=[inv@p for p in v]
    m=bpy.data.meshes.new(name);m.from_pydata(v,[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);m.update();return m
def grain(o):
    uv=o.data.uv_layers.active or o.data.uv_layers.new(name='Physical oak grain')
    for p in o.data.polygons:
        for li in p.loop_indices:
            co=o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=(co.y/1.2,co.z/1.6)
def cut_round(o,center):
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.225,depth=1.2,location=(-1.95,7.83,center),rotation=(0,math.pi/2,0))
    cutter=bpy.context.object;bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Circular window clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    solvers=[e.identifier for e in mod.bl_rna.properties['solver'].enum_items]
    if 'EXACT' in solvers:mod.solver='EXACT'
    while list(o.modifiers).index(mod)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)

for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    sink_shelf=next(o for o in sc.objects if o.name.startswith('Panoramic shelf | floating'))
    level=bounds(sink_shelf)[2][1]
    long_window=next(o for o in sc.objects if o.type=='MESH' and o.get('source_window_id')=='9b44bb93-1dea-42b1-98cd-26466e14a447' and 'glazing' in o.name)
    center=(long_window['sill_mm']+long_window['head_mm'])/2000
    window_root=next(o for o in sc.objects if o.name.startswith('Window | Round stove-side aperture'))
    window_root.location.z+=center-window_root['center_height_mm']/1000
    window_root['center_height_mm']=round(center*1000,1);window_root['source_revision']=revision
    window_root['alignment']='Center aligned with long sink window'
    wall=next(o for o in sc.objects if o.name.startswith('Kitchen west | plaster wall with circular'))
    plaster=wall.data.materials[0]
    wall.data=cubemesh('Stove wall circular opening aligned with sink window',[(-2.1829,-2.0251),(6.483,8.5738),(0,2.4384)],wall.matrix_world.inverted())
    wall.data.materials.append(plaster);cut_round(wall,center)
    root=next(o for o in sc.objects if o.name.startswith('Kitchen | Full-width ceiling oak'))
    col=root.users_collection[0]
    for o in list(sc.objects):
        if o.name.startswith('Oak stove uppers |'):bpy.data.objects.remove(o,do_unlink=True)
    def box(name,b):
        o=bpy.data.objects.new('Oak stove uppers | '+name,cubemesh(name,b));col.objects.link(o);o.parent=root
        o.data.materials.append(wood);grain(o)
        bevel=o.modifiers.new('Soft joinery edges','BEVEL');bevel.width=.001;bevel.segments=3
        o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');o['source_revision']=revision
        return o
    rear=-2.0251;front=-1.6451;top=2.4384;y0=5.6316;y1=8.4949
    boundaries=[y0,6.1016,6.5716,7.1116,7.5716,8.1916,y1]
    box('ceiling top',[(rear,front-.018),(y0,y1),(top-.018,top)])
    for i,y in enumerate(boundaries):box(f'full-height gable {i+1}',[(rear,front-.018),(y,y+.018),(level+.114 if i in [2,3] else level,top)])
    for i,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:])):
        panel=box(f'continuous-line oak front {i+1}',[(front-.018,front),(a+.0015,b-.0015),(level+.002,top-.002)])
        panel['hardware']='Concealed hinges or removable service panel; recessed edge grip'
        if a<7.83<b:
            cut_round(panel,center);grain(panel);panel['construction']='Fixed panel with clear circular window reveal'
    # The ledge runs continuously in front; an underside aperture leaves the extractor filters clear.
    for name,a,b in [('left shelf',y0,6.3876),('right shelf',7.2365,y1)]:
        box(name,[(rear,front+.02),(a,b),(level-.032,level)])
    rail=box('continuous shelf front edge',[(front-.006,front+.02),(y0,y1),(level-.032,level)])
    rail['source_fixture_id']=shelf_id;rail['shelf_top_mm']=round(level*1000,1)
    rail['construction']='Continuous floating oak ledge with concealed supports; extractor aperture behind front edge'
    hood=next(o for o in sc.objects if o.name.startswith('Kitchen | Ceiling-height integrated hood'))
    old=hood.get('bottom_mm',1805)/1000
    hood.location.z+=level-old;hood['bottom_mm']=round(level*1000,1);hood['source_revision']=revision
    root['bottom_mm']=round(level*1000,1);root['hood_bottom_mm']=round(level*1000,1);root['source_revision']=revision
    root['construction']='Single straight cabinet, hood and shelf line; no raised center bay'
    slab=next(o for o in sc.objects if o.name.startswith('Backsplash | Honed soapstone slab'))
    stone=slab.data.materials[0]
    slab.data=cubemesh('Stove soapstone to continuous shelf line',[(-2.0241,-2.0041),(y0,y1),(.9325,level)],slab.matrix_world.inverted());slab.data.materials.append(stone)
    slab['top_mm']=round(level*1000,1);slab.parent['top_mm']=round(level*1000,1);slab['source_revision']=revision
    sc['source_revision']=revision
    sc['hood_notes']='Concealed hood lowered to the continuous shelf/cabinet line at 1476 mm; raised center bay removed'
    sc['backsplash_notes']='Full stove-wall soapstone from 932.5 mm countertop to continuous shelf line 1476 mm'
    sc['stove_wall_notes']='Full-width shelf and flush cabinet/hood edge at 1476 mm. Round window center 1756.5 mm aligns with rectangular sink window center.'
    bpy.context.view_layer.update()
    assert abs(bounds(rail)[2][1]-level)<1e-5
    assert center-.225>level
    print(sc.name,'continuous line mm',round(level*1000,1),'window center mm',round(center*1000,1))

f=doc['fixtures'][hood_id];f['style']='full_width_oak_uppers_and_concealed_hood_single_bottom_line_1476mm_ceiling_2438.4mm';f['depth']=400
doc['fixtures'][shelf_id]={'id':shelf_id,'kind':'OverheadCabinet','origin':{'x':17358.0,'y':5151.4},'width':2863.3,'depth':400,'rotation':270,'layer':f['layer'],'style':'continuous_stove_wall_floating_oak_shelf_top_1476mm_concealed_extractor_aperture','material':'Photographed white oak satin'}
for label in doc['room_labels'].values():
    if label['name'].startswith('Oak uppers:'):label['name']='Shelf + oak uppers + hood: continuous line 1476 mm'
    elif label['name'].startswith('Round stove window:'):label['name']='Round window: Ø450 mm / center 1756.5 mm aligned sink'
    elif label['name'].startswith('Soapstone:'):label['name']='Soapstone: full stove wall / top at shelf 1476 mm'
doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {revision}: continuous stove-wall shelf/ledge, cabinet lower edge and concealed hood at 1476 mm, matching sink shelf. Removed raised hood bay. Shelf front continuous with filter opening behind it. Soapstone ends at this line. Round window lowered to center 1756.5 mm, aligned with rectangular sink window center; wall and oak openings rebuilt. Appliance-specific construction clearances have not been verified.\n')
