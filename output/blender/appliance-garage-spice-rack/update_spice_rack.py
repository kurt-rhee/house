import bpy, math
from mathutils import Vector
from pathlib import Path
s=bpy.context.scene
out=Path('/Users/kurt/Programs/house/output/blender/appliance-garage-spice-rack')
r=bpy.data.objects['Kitchen | Left-facing appliance garage']
col=r.users_collection[0]
wood=bpy.data.objects['Appliance garage end panel'].data.materials[0]
metal=bpy.data.objects['Appliance garage lower pull'].data.materials[0]
w,d,split=.6604,.4572,.1524
def box(name,loc,dims,ma=wood,bev=.003):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o);o.parent=r;o.location=loc;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(ma)
    if bev:
        b=o.modifiers.new('Cabinet edge rounding','BEVEL');b.width=bev;b.segments=3
        o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
    return o
# Reserve 6 inches of the 26-inch run for a north-facing spice niche.
# The garage retains its west-facing opening and the original outside footprint.
for o in list(r.children):
    if o.name.startswith('Appliance garage raised tambour slat'):
        o.location.x=(split+w)/2;o.dimensions.x=w-split-.047
        bpy.context.view_layer.objects.active=o
        o.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.select_set(False)
    if o.name=='Appliance garage shutter lift pull':o.location.x=(split+w)/2
o=bpy.data.objects['Appliance garage end panel']
o.location.z=.47125;o.dimensions.z=.9425
bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
box('Spice niche upper end panel',(.009,-d/2,(1.6825+2.26)/2),(.018,d,2.26-1.6825))
box('Spice niche divider and back',(split-.009,-d/2,1.31),(.018,d,.735))
# Close the west side of the reserved strip; its open face points north, like the fridge.
box('Spice niche west return',(split/2,-d+.009,1.31),(split,.018,.735))
for i,z in enumerate([.965,1.135,1.305,1.475]):
    box('Spice rack oak shelf '+str(i+1),(split/2,-d/2,z),(split-.012,d-.036,.018))
    box('Spice rack retaining rail '+str(i+1),(.014,-d/2,z+.043),(.012,d-.046,.048))

def mat(name,color,rough=.55):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
    return m
jars=[mat('Spices | paprika',(.40,.13,.045)),mat('Spices | herbs',(.20,.27,.08)),mat('Spices | turmeric',(.60,.38,.055)),mat('Spices | pepper',(.12,.095,.065))]
cap=mat('Spice jars | matte black caps',(.045,.04,.035))
label=mat('Spice jars | cream labels',(.79,.74,.60))
def cyl(name,loc,rad,height,ma):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=rad,depth=height)
    o=bpy.context.object;o.name=name
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o);o.parent=r;o.location=loc;o.data.materials.append(ma)
    b=o.modifiers.new('Soft jar edge','BEVEL');b.width=.002;b.segments=2
    for p in o.data.polygons:p.use_smooth=True
    return o
for row,z in enumerate([.974,1.144,1.314,1.484]):
    for j in range(5):
        y=-.065-j*.081;h=.092+(j%2)*.012
        cyl('Spice jar',(.067,y,z+h/2),.029,h,jars[(j+row)%4])
        cyl('Spice jar label',(.067,y,z+h*.48),.0295,.037,label)
        cyl('Spice jar lid',(.067,y,z+h+.006),.030,.012,cap)
r['overall_width_mm']=660.4;r['spice_section_mm']=152.4
r['appliance_section_mm']=508.0;r['bay_clear_width_mm']=472.0
r['spice_opening_direction']='North / same direction as refrigerator doors'
r['design_notes']='Original 660.4 x 457.2 mm footprint retained. Upper bay reserves 152.4 mm at refrigerator-front end for side-facing spice shelves; west-facing garage narrowed.'
for o in s.objects:
    if o.name.startswith('Person A |'):o.location=(-.78,5.28,.008)
    if o.name.startswith('Person B |'):o.location=(-1.12,6.72,.008)
cam=s.camera;cam.location=(-3.4,8.5,4.2)
cam.rotation_euler=(Vector((-.12,5.61,1.12))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=3.55
s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.resolution_percentage=100
s.cycles.samples=40;s.render.filepath=str(out/'appliance-garage-spice-rack.png')
s['scale_render_notes']='Original cabinet footprint. 6 inch spice section faces same way as fridge; remaining 20 inch section faces kitchen aisle. Walls retained.'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'appliance-garage-spice-rack.blend'))
print('Saved: overall 26 inches; spice section 6 inches; appliance section 20 inches.')
