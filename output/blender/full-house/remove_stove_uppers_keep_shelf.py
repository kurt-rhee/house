"""Remove stove-wall cabinetry; retain continuous shelf and restore plaster hood."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Vector
base=Path('/Users/kurt/Programs/house/output')
doc=json.loads((base/'floor-plan.house.json').read_text());revision=doc['revision']+1
backup=base/'blender'/f'before-removing-stove-cabinets-revision-{revision}';backup.mkdir(exist_ok=True)
for p in [base/'floor-plan.house.json',base/'blender/full-house/full-house.blend',base/'walkthrough/house-walkthrough.blend']:shutil.copy2(p,backup/p.name)
source=next(s for s in bpy.data.scenes if s.name.startswith('Full House | Drawing Revision'))
tour=bpy.data.scenes['House | Interior walkthrough']
hood_id='cc99b809-cb08-51b4-a631-7c1eae3d9db0';shelf_id='33ac9591-fe96-5361-867e-89318d0ce11c'
for sc in [source,tour]:
    bpy.context.window.scene=sc;sc.frame_set(1);bpy.context.view_layer.update()
    root=next(o for o in sc.objects if o.name.startswith('Kitchen | Full-width ceiling oak'))
    for o in list(sc.objects):
        if o.name.startswith('Oak stove uppers |'):
            if any(k in o.name for k in ['left shelf','right shelf','continuous shelf front edge']):
                o.name=o.name.replace('Oak stove uppers |','Stove wall shelf |')
            else:bpy.data.objects.remove(o,do_unlink=True)
    root.name='Kitchen | Continuous stove-wall floating shelf'
    root['source_fixture_id']=shelf_id;root['source_revision']=revision
    root['construction']='Continuous floating oak shelf with concealed supports and extractor aperture'
    root['shelf_top_mm']=1476
    for key in ['hood_bottom_mm','top_mm','bottom_mm']: 
        if key in root:del root[key]
    frame=next(o for o in sc.objects if o.name.startswith('Round stove window | slim bronze frame'))
    for v in frame.data.vertices:
        if v.co.x>-2.1:v.co.x=-2.013
    frame.data.update();frame['reveal_depth_mm']=180
    win=next(o for o in sc.objects if o.name.startswith('Window | Round stove-side aperture'))
    win['surround']='Warm plaster wall with slim bronze frame'
    hood=next(o for o in sc.objects if o.name.startswith('Kitchen | Ceiling-height integrated hood'))
    # Ceiling-height plaster housing retains shelf-level underside and existing extractor.
    y=6.812075
    verts=[(-2.0251,y-.425,1.476),(-1.6251,y-.425,1.476),(-1.6251,y+.425,1.476),(-2.0251,y+.425,1.476),
           (-2.0251,y-.3,2.4384),(-1.7251,y-.3,2.4384),(-1.7251,y+.3,2.4384),(-2.0251,y+.3,2.4384)]
    inv=hood.matrix_world.inverted()
    mesh=bpy.data.meshes.new('Architectural plaster hood to continuous shelf line')
    mesh.from_pydata([inv@Vector(v) for v in verts],[],[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);mesh.update()
    mesh.materials.append(bpy.data.materials['Hood | Warm mineral plaster'])
    shell=bpy.data.objects.new('Architectural hood | tapered plaster shell',mesh);hood.users_collection[0].objects.link(shell);shell.parent=hood
    bevel=shell.modifiers.new('Soft plaster corners','BEVEL');bevel.width=.002;bevel.segments=3;shell.modifiers.new('Weighted plaster normals','WEIGHTED_NORMAL')
    hood['drawing_style']='architectural_plaster_hood_bottom_1476mm_aligned_continuous_shelf_top_2438.4mm'
    hood['drawing_material']='Warm ivory mineral plaster with concealed extractor'
    hood['source_revision']=revision
    sc['source_revision']=revision
    sc['hood_notes']='Exposed ceiling-height plaster range hood, bottom 1476 mm aligned with continuous oak shelf; stove-wall upper cabinets removed'
    sc['kitchen_shelf_notes']='Continuous stove-wall oak shelf and sink-window shelf retained, both top 1476 mm'
    sc['stove_wall_notes']='Plaster above shelf; round window centered 1756.5 mm aligned to sink window; no stove-wall upper cabinetry'
    assert not any(o.name.startswith('Oak stove uppers |') for o in sc.objects)
    print(sc.name,'removed upper cabinets, retained shelves and aligned windows, restored plaster hood')

f=doc['fixtures'][hood_id];f.update(origin={'x':17358.0,'y':4395.925},width=850,depth=400,
    style='architectural_plaster_hood_bottom_1476mm_aligned_continuous_shelf_ceiling_2438.4mm',material='Warm ivory mineral plaster, concealed extractor')
for label in doc['room_labels'].values():
    if label['name'].startswith('Shelf + oak uppers + hood:'):label['name']='Continuous oak shelf + plaster hood: line 1476 mm'
    elif label['name'].startswith('Stove wall: full-width oak uppers'):label['name']='Stove wall: floating shelf / plaster above'
doc['revision']=revision
for p in [base/'floor-plan.house.json',base/'blender/full-house/drawing-snapshot.json']:p.write_text(json.dumps(doc,indent=2)+'\n')
source.name=f'Full House | Drawing Revision {revision}'
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
p=base/'walkthrough/RENDER-NOTES.txt';p.write_text(p.read_text()+f'\nRevision {revision}: stove-wall oak upper cabinetry removed, continuous floating oak shelf retained at 1476 mm. Restored ceiling-height warm plaster hood, underside aligned at 1476 mm, existing extractor and task lights retained. Round bronze window reveal shortened to wall depth; center remains aligned to sink window at 1756.5 mm. Other cabinetry unchanged.\n')
