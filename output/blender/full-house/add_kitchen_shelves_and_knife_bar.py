"""Update the cutaway and interior scenes together, without publishing web changes."""
import bpy, math, json, uuid
from pathlib import Path
from mathutils import Vector

base=Path('/Users/kurt/Programs/house/output/blender/full-house')
doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text())
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'))
tour=bpy.data.scenes.get('House | Interior walkthrough')

def original_name(o):return o.get('walkthrough_source_name',o.name)
def ident(key):return str(uuid.uuid5(uuid.NAMESPACE_URL,'house/kitchen-revision/'+key))

for scene in [s for s in [source,tour] if s]:
    bpy.context.window.scene=scene
    root=next(o for o in scene.objects if original_name(o)=='Kitchen | Counter-height cabinet beside fridge')
    shelf_parts=[o for o in root.children if original_name(o).startswith('Wall shelf |')]
    oak=next(o.data.materials[0] for o in shelf_parts if 'oak floating shelf' in original_name(o))
    metal=bpy.data.materials['Brushed chrome']
    for o in shelf_parts:
        name=original_name(o)
        if 'oak floating shelf' in name:
            o.dimensions.y=.28;o.location.y=.14
            o['source_fixture_id']='e1928df0-155f-546e-b491-516387590509'
            o['depth_mm']=280;o['shelf_top_mm']=1476
        elif 'bracket underside' in name:
            o.dimensions.y=.22;o.location.y=.11
    bpy.context.view_layer.update()
    for o in shelf_parts:
        new=o.copy();new.data=o.data.copy()
        o.users_collection[0].objects.link(new)
        new.name='Microwave upper shelf | '+original_name(o).split('|',1)[1].strip()
        new.location.z+=.35
        new['walkthrough_source_name']=new.name
        if 'oak floating shelf' in original_name(o):new['shelf_top_mm']=1826
    root['shelf_depth_mm']=280
    root['shelf_top_heights_mm']=[1476,1826]
    root['shelf_count']=2

    col=bpy.data.collections.new('Kitchen | Stove shelf and knife bar')
    scene.collection.children.link(col)
    rack=bpy.data.objects.new('Kitchen | Stove-side shelf and magnetic knife bar',None)
    col.objects.link(rack);rack.location=(-2.0251,6.305,0);rack.rotation_euler.z=math.pi/2
    rack['source_fixture_id']=ident('stove-prep-shelf')
    rack['shelf_top_mm']=1750;rack['shelf_width_mm']=650;rack['shelf_depth_mm']=250
    rack['knife_bar_center_mm']=1340;rack['knife_bar_width_mm']=520
    rack['placement']='Prep counter south of stove; 151 mm clear of cooktop footprint'

    def box(name,loc,dims,mat=oak,bevel=.003):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o=bpy.context.object
        for c in list(o.users_collection):c.objects.unlink(o)
        col.objects.link(o);o.name=name;o.parent=rack;o.location=loc;o.dimensions=dims
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        o.data.materials.append(mat)
        if bevel:
            b=o.modifiers.new('Soft manufactured edges','BEVEL');b.width=bevel;b.segments=3
            o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
        return o

    box('Stove shelf | floating oak board',(0,-.125,1.734),(.65,.25,.032))
    box('Stove shelf | concealed wall cleat',(0,-.009,1.698),(.61,.018,.04))
    for u in [-.245,.245]:
        box('Stove shelf | bracket vertical',(u,-.012,1.657),(.018,.024,.122),metal)
        box('Stove shelf | bracket underside',(u,-.10,1.707),(.018,.20,.019),metal)
    bar=box('Knife bar | oak magnetic holder',(0,-.015,1.34),(.52,.03,.045))
    bar['source_fixture_id']=ident('stove-magnetic-knife-bar')
    dark=bpy.data.materials.get('Kitchen | Knife handles')
    if not dark:
        dark=bpy.data.materials.new('Kitchen | Knife handles');dark.use_nodes=True
        p=next(n for n in dark.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value=(.025,.029,.024,1);p.inputs['Roughness'].default_value=.38
    box('Knife bar | inset magnetic strip',(0,-.031,1.34),(.49,.003,.022),dark,.001)
    steel=bpy.data.materials.get('Kitchen | Knife blade steel')
    if not steel:
        steel=bpy.data.materials.new('Kitchen | Knife blade steel');steel.use_nodes=True
        p=next(n for n in steel.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        p.inputs['Base Color'].default_value=(.53,.58,.60,1);p.inputs['Metallic'].default_value=.92;p.inputs['Roughness'].default_value=.24
    for label,u,width,height in [('Chef',-.16,.048,.22),('Santoku',0,.044,.18),('Utility',.16,.027,.145)]:
        z=1.29
        profile=[(u-width/2,z),(u+width/2,z),(u+width/2,z+height*.82),(u+width*.05,z+height),(u-width*.32,z+height*.7)]
        verts=[(x,y,zz) for y in [-.036,-.038] for x,zz in profile]
        faces=[tuple(reversed(range(5))),tuple(range(5,10))]
        faces += [(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)]
        mesh=bpy.data.meshes.new(label+' knife blade');mesh.from_pydata(verts,[],faces);mesh.update()
        o=bpy.data.objects.new('Knife bar | '+label+' blade',mesh);col.objects.link(o);o.parent=rack;mesh.materials.append(steel)
        b=o.modifiers.new('Blade edge highlight','BEVEL');b.width=.0006;b.segments=2
        box('Knife bar | '+label+' handle',(u,-.043,1.23),(.028,.019,.12),dark,.005)
        for zz in [1.195,1.23,1.265]:
            box('Knife bar | handle pin',(u,-.053,zz),(.004,.002,.004),steel,.001)
    scene['source_revision']=doc['revision']
    scene['kitchen_shelf_notes']='Two 622 x 280 mm oak shelves above microwave, tops 1476 / 1826 mm. Stove-side 650 x 250 mm shelf top 1750 mm, magnetic knife bar centered 1340 mm.'
    for o in scene.objects:
        fixture=doc['fixtures'].get(o.get('source_fixture_id'))
        if fixture:
            o['source_revision']=doc['revision'];o['plan_footprint_mm']=[fixture['width'],fixture['depth']]
            o['drawing_style']=fixture.get('style','')
    if scene==source:scene.name='Full House | Drawing Revision '+str(doc['revision'])

(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source
source.camera=bpy.data.objects['Current | Kitchen arch and fridge']
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
if tour:
    bpy.context.window.scene=tour
    bpy.ops.wm.save_as_mainfile(filepath=str(base.parent.parent/'walkthrough'/'house-walkthrough.blend'))
print('Updated microwave shelves and stove shelf / knife bar in both Blender scenes; revision',doc['revision'])
