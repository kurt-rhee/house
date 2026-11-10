import bpy,json
from pathlib import Path
s=bpy.context.scene
base=Path('/Users/kurt/Programs/house/output/blender/full-house')
root=next((o for o in s.objects if o.get('design_element')=='dishwasher_drawer'),None)
if root:
 for o in list(root.children):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.objects.remove(root,do_unlink=True)
col=next(o for o in s.objects if o.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a' and o.type=='EMPTY').users_collection[0]
root=bpy.data.objects.new('Kitchen | Single dishwasher drawer',None);col.objects.link(root)
root.location=((18145.9-19383.1)/1000,(10783-2288.1)/1000,0)
root['design_element']='dishwasher_drawer';root['nominal_width_mm']=609.6;root['open_extension_mm']=558.8;root['placement']='Left of sink, north countertop';root['clearance_note']='Closed drawer clears oven. Open drawer overlaps assumed oven door sweep; use one at a time.'
# Generic panel-ready concept envelope; final cabinetry depends on selected model.
wood=next(o for o in s.objects if o.name.startswith('Oak base cabinets') and o.parent and o.parent.get('source_fixture_id')=='c0c93320-283f-4d94-bc6e-b11ec56a989a').data.materials[0]
metal=bpy.data.materials.get('Brushed chrome')
def material(name,color):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.5;return m
dark=material('Dishwasher | Shadow gap',(.022,.022,.019))
def box(name,loc,size,ma,bevel=.003):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);o.name=name;o.parent=root;o.location=loc;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if ma:o.data.materials.append(ma)
 if bevel:
  b=o.modifiers.new('Soft edges','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
box('Dishwasher drawer reveal',(.3048,-.635,.665),(.605,.012,.451),dark)
box('Dishwasher oak integrated front',(.3048,-.647,.665),(.594,.024,.43),wood)
box('Dishwasher recessed pull',(.3048,-.662,.855),(.36,.012,.014),dark)
root['finish']='Oak panel matching kitchen cabinets'
# Drawer stays closed in this view so the oven remains usable.
s['dishwasher_layout_note']=root['clearance_note']
s.camera=next(o for o in s.objects if o.name=='Current | Kitchen');s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.filepath=str(base/'04-kitchen.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'));bpy.ops.render.render(write_still=True)
print('Dishwasher drawer added left of sink; closed clears oven, both open interfere.')
