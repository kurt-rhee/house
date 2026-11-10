import bpy,json
s=bpy.context.scene
assert s.name.startswith('Full House | Drawing Revision')
ids={'c08078d4-006c-4eba-8032-0bf18c432cec','c0c93320-283f-4d94-bc6e-b11ec56a989a'}
m=bpy.data.materials.get('Kitchen | Honed charcoal soapstone') or bpy.data.materials.new('Kitchen | Honed charcoal soapstone')
m.use_nodes=True;m.diffuse_color=(.035,.045,.040,1)
n=m.node_tree.nodes;n.clear();l=m.node_tree.links
out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');p.inputs['Roughness'].default_value=.48;l.new(p.outputs['BSDF'],out.inputs['Surface'])
coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.65;l.new(coord.outputs['Object'],noise.inputs['Vector'])
base=n.new('ShaderNodeValToRGB');base.color_ramp.elements[0].color=(.018,.026,.022,1);base.color_ramp.elements[1].color=(.052,.065,.057,1);l.new(noise.outputs['Fac'],base.inputs['Fac'])
warp=n.new('ShaderNodeVectorMath');warp.operation='SCALE';warp.inputs[3].default_value=.28;l.new(noise.outputs['Color'],warp.inputs[0])
add=n.new('ShaderNodeVectorMath');add.operation='ADD';l.new(coord.outputs['Object'],add.inputs[0]);l.new(warp.outputs['Vector'],add.inputs[1])
vein=n.new('ShaderNodeTexVoronoi');vein.feature='DISTANCE_TO_EDGE';vein.inputs['Scale'].default_value=2.1;l.new(add.outputs['Vector'],vein.inputs['Vector'])
r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.003;r.color_ramp.elements[0].color=(1,1,1,1);r.color_ramp.elements[1].position=.017;r.color_ramp.elements[1].color=(0,0,0,1);l.new(vein.outputs['Distance'],r.inputs['Fac'])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';l.new(r.outputs['Color'],mix.inputs[0]);l.new(base.outputs['Color'],mix.inputs[1]);mix.inputs[2].default_value=(.12,.14,.125,1);l.new(mix.outputs[0],p.inputs['Base Color'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.002;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
changed=[]
for o in s.objects:
 if o.type=='MESH' and o.name.startswith(('Quartz countertop','Soapstone kitchen countertop')) and o.parent and o.parent.get('source_fixture_id') in ids:
  o.data.materials.clear();o.data.materials.append(m);o.name='Soapstone kitchen countertop';o['finish']='Honed charcoal soapstone';o['source_fixture_id']=o.parent['source_fixture_id'];changed.append(o.parent['source_fixture_id'])
assert set(changed)==ids,changed
s['material_assignments']=json.dumps({ident:{'material':'soapstone','finish':'honed','color':'charcoal with subtle pale veining'} for ident in ids})
basepath='/Users/kurt/Programs/house/output/blender/full-house/'
main=s.camera
bpy.ops.wm.save_as_mainfile(filepath=basepath+'full-house.blend')
for camera,file,w,h in [(main,'02-main-house.png',2000,1800),(next(o for o in s.objects if o.name.startswith('Current | Whole property')),'01-whole-property.png',2400,1500)]:
 s.camera=camera;s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=basepath+file;bpy.ops.render.render(write_still=True)
s.camera=main;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=basepath+'02-main-house.png'
bpy.ops.wm.save_as_mainfile(filepath=basepath+'full-house.blend')
print('Assigned honed charcoal soapstone to both kitchen countertops and refreshed renders.')
