"""Create an independent, real-time interior walkthrough from the current house."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

OUT=Path('/Users/kurt/Programs/house/output/walkthrough')
source=next(scene for scene in bpy.data.scenes if scene.objects.get('Dining arch | curved plaster header'))
s=bpy.data.scenes.new('House | Interior walkthrough')
s.unit_settings.system='METRIC'
s['source_revision']=source['source_revision']
s['walkthrough_controls']='Shift + grave accent: walk; WASD: move; mouse: look; E/Q: up/down; Shift: faster; wheel: speed; left click: confirm; Escape: exit. N sidebar > House Tour: start/reset and room viewpoints.'
col=bpy.data.collections.new('Walkthrough | House model');s.collection.children.link(col)
objects={}
for old in source.objects:
    if old.type=='FONT': continue
    new=old.copy()
    if old.data: new.data=old.data.copy()
    col.objects.link(new);objects[old]=new
    new['walkthrough_source_name']=old.name
for old,new in objects.items():
    if old.parent: new.parent=objects.get(old.parent)
bpy.context.window.scene=s
try: s.render.engine='BLENDER_EEVEE'
except TypeError as e: raise RuntimeError(str(e))
s.eevee.taa_samples=32;s.eevee.taa_render_samples=96
s.eevee.use_raytracing=True;s.eevee.use_fast_gi=True
s.eevee.fast_gi_quality=.7;s.eevee.fast_gi_ray_count=4
s.eevee.use_shadow_jitter_viewport=True
s.eevee.ray_tracing_options.screen_trace_quality=.75
s.eevee.ray_tracing_options.use_denoise=True
s.view_settings.view_transform='AgX';s.view_settings.exposure=.35
s.render.resolution_x=1600;s.render.resolution_y=1000;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'

def material(name,color,rough=.6,metal=0):
    m=bpy.data.materials.new('Tour | '+name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m,p
wall,p=material('Warm ivory plaster',(.72,.69,.63),.82)
n=wall.node_tree.nodes;l=wall.node_tree.links
tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=150
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001
l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
ceiling,_=material('Soft white ceiling',(.78,.77,.73),.87)
glass,p=material('Clear architectural glass',(.9,.96,1),.045)
p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.45
# A transparent component keeps daylight visible in the real-time engine.
n=glass.node_tree.nodes;l=glass.node_tree.links
trans=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=.12
l.new(trans.outputs[0],mix.inputs[1]);l.new(p.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],next(n for n in n if n.type=='OUTPUT_MATERIAL').inputs['Surface'])
wood,p=material('Brushed oak cabinetry',(.46,.28,.14),.36)
n=wood.node_tree.nodes;l=wood.node_tree.links
coord=n.new('ShaderNodeTexCoord');stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(32,32,1.4)
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.6
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.12;ramp.color_ramp.elements[0].color=(.20,.105,.045,1);ramp.color_ramp.elements[1].position=.88;ramp.color_ramp.elements[1].color=(.55,.36,.18,1)
l.new(coord.outputs['Generated'],stretch.inputs[0]);l.new(stretch.outputs['Vector'],noise.inputs['Vector']);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs['Color'],p.inputs['Base Color'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.0006;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
floor,p=material('Natural oak floorboards',(.44,.31,.19),.42)
n=floor.node_tree.nodes;l=floor.node_tree.links
coord=n.new('ShaderNodeTexCoord');brick=n.new('ShaderNodeTexBrick');brick.inputs['Scale'].default_value=1;brick.inputs['Mortar Size'].default_value=.0018;brick.inputs['Mortar Smooth'].default_value=.001;brick.inputs['Brick Width'].default_value=1.4;brick.inputs['Row Height'].default_value=.18;brick.offset=.5
brick.inputs['Color1'].default_value=(.48,.33,.20,1);brick.inputs['Color2'].default_value=(.34,.22,.12,1);brick.inputs['Mortar'].default_value=(.18,.12,.07,1)
l.new(coord.outputs['Object'],brick.inputs['Vector'])
stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(2,90,2)
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2.5;noise.inputs['Detail'].default_value=3
l.new(coord.outputs['Object'],stretch.inputs[0]);l.new(stretch.outputs['Vector'],noise.inputs['Vector'])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.18;l.new(brick.outputs['Color'],mix.inputs[1]);l.new(noise.outputs['Fac'],mix.inputs[2]);l.new(mix.outputs[0],p.inputs['Base Color'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0008;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
for old,o in objects.items():
    if o.type not in {'MESH','CURVE'}: continue
    for slot in o.material_slots:
        if not slot.material: continue
        name=slot.material.name
        if name.startswith(('View | Semi-transparent','Warm white plaster','Design | Warm limewash','Study | Warm plaster')): slot.material=wall
        elif name.startswith(('Window frosted glazing','Study | Glazing')):slot.material=glass
        elif name.startswith('Natural oak'):slot.material=wood
        elif name.startswith('Pale oak flooring'):slot.material=floor
    if o.get('view_wall_opacity') is not None:o['view_wall_opacity']=1.0
# Close the roofless study at the modeled ceiling elevation, using the existing floor footprints.
for old,o in list(objects.items()):
    if old.name.startswith(('Main house floor','Garage and ADU wing floor','Office floor','Utility floor','Laundry floor')):
        roof=o.copy();roof.data=o.data.copy();col.objects.link(roof);roof.name='Tour ceiling | '+old.name
        low=min((roof.matrix_world@Vector(c)).z for c in roof.bound_box)
        roof.location.z+=2.4384-low;roof.data.materials.clear();roof.data.materials.append(ceiling)
# Use a sky with a low afternoon sun and softly illuminated interiors.
s.world=bpy.data.worlds.new('Tour | Afternoon sky');s.world.use_nodes=True
nodes=s.world.node_tree.nodes;links=s.world.node_tree.links
bg=next(n for n in nodes if n.type=='BACKGROUND');bg.inputs['Strength'].default_value=.35
sky=nodes.new('ShaderNodeTexSky')
items=[i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items]
sky.sky_type='MULTIPLE_SCATTERING' if 'MULTIPLE_SCATTERING' in items else items[0]
if hasattr(sky,'sun_elevation'):sky.sun_elevation=math.radians(32)
if hasattr(sky,'sun_rotation'):sky.sun_rotation=math.radians(140)
links.new(sky.outputs['Color'],bg.inputs['Color'])
for o in s.objects:
    if o.type=='LIGHT' and o.data.type=='SUN':o.data.energy=1.6;o.data.angle=.12;o.rotation_euler=(.5,-.4,-.6)
    elif o.type=='LIGHT' and 'Broad daylight' in o.name:o.hide_render=True;o.hide_set(True)
fixtures=bpy.data.collections.new('Walkthrough | Interior lighting');s.collection.children.link(fixtures)

def light(name,loc,power,size=1.0,color=(1,.84,.65),target=None):
    data=bpy.data.lights.new('Tour | '+name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(data.name,data);fixtures.objects.link(o);o.location=loc
    if target:o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o
# Soft ceiling sources approximate recessed ambient lighting without a harsh on-camera hotspot.
for name,x,y,power,size in [('Kitchen',-.45,7.15,120,1.7),('Dining',2.9,7.15,150,2),('Living',2.8,4.05,180,2.5),('Bedroom 3',-1.35,3.0,85,1.6),('Main bedroom',-1.6,-1.1,90,1.8),('Hallway',2.7,.6,70,1.0),('Guest bedroom',5.1,-.4,90,1.5),('Bathroom 1',.85,-1.1,75,1.0),('Bathroom 2',2.55,-1.1,75,1.0),('Laundry',-3.3,5.6,85,1.2),('ADU',-12,4,90,1.5),('Office',-17,8,90,1.5),('Garage',-12.5,8.5,160,2.5)]:
    light(name,(x,y,2.38),power,size)
# Window-shaped daylight sources add believable soft fill and metal reflections.
light('Kitchen window daylight',(-.2,8.50,1.65),130,1.5,(.82,.90,1),(-.2,6.8,1.0))
light('Dining window daylight',(4.64,7.2,1.65),170,1.4,(.85,.92,1),(2.7,7.2,1.1))
light('Living window daylight',(4.64,4.9,1.65),140,1.4,(.85,.92,1),(2.8,4.5,1.0))
# Named eye-level camera positions are also reset points for the walk controls.
viewpoints={
 'Kitchen':((-.55,7.75,1.65),(.15,5.35,1.35)),
 'Dining / arch':((3.7,6.85,1.65),(-.2,6.85,1.45)),
 'Living room':((3.5,4.4,1.65),(.8,5.5,1.4)),
 'Laundry':((-3.25,6.2,1.65),(-3.4,4.6,1.3)),
 'Main bedroom':((-1.7,.5,1.65),(-1.65,-1.5,1.1)),
 'Bathroom 1':((.8,-.15,1.65),(.9,-2,1.25)),
}
for name,(eye,target) in viewpoints.items():
    data=bpy.data.cameras.new('Tour camera | '+name);data.lens=21;data.clip_start=.03;data.clip_end=250
    camera=bpy.data.objects.new(data.name,data);fixtures.objects.link(camera);camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    if name=='Kitchen':s.camera=camera
s['tour_viewpoints']=json.dumps(viewpoints)
walk=bpy.context.preferences.inputs.walk_navigation
walk.walk_speed=1.2;walk.walk_speed_factor=3;walk.view_height=1.65;walk.mouse_speed=.8;walk.use_gravity=False
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        space=a.spaces.active;space.overlay.show_overlays=False;space.shading.type='RENDERED'
        space.shading.use_scene_lights_render=True;space.shading.use_scene_world_render=True
        space.clip_start=.03;space.clip_end=250;space.lens=21
        region=space.region_3d;region.view_perspective='PERSP';region.view_rotation=s.camera.rotation_euler.to_quaternion();region.view_distance=.01
        region.view_location=s.camera.location+region.view_rotation@Vector((0,0,-.01))
        space.show_region_ui=True
s.render.filepath=str(OUT/'01-kitchen-interior.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'house-walkthrough.blend'))
# Export the interior scene as a portable model; browser materials are refined separately.
export_objects=[o for o in s.objects if o.type in {'MESH','CURVE','EMPTY'} and not o.hide_render]
bpy.ops.object.select_all(action='DESELECT')
for o in export_objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath='/Users/kurt/Programs/house/sites/house-walkthrough/public/assets/house.glb',export_format='GLB',use_active_scene=True,use_selection=True,export_cameras=False,export_lights=False,export_extras=True)
print('Interior model exported; source revision',s['source_revision'])
