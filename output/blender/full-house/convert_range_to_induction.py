"""Replace gas fittings with a flat, black glass four-zone induction cooktop."""
import bpy,json,math
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output');doc=json.loads((base/'floor-plan.house.json').read_text());doc['revision']=18
fid='f6bd213e-4f0b-4b20-8167-2b0e1436cc5a'
doc['fixtures'][fid]['style']='induction_range_four_zones_electric_oven';doc['fixtures'][fid]['material']='Black ceramic induction glass, satin nickel oven'
(base/'floor-plan.house.json').write_text(json.dumps(doc,indent=2)+'\n')
source=next(s for s in bpy.data.scenes if s.objects.get('Dining arch | curved plaster header'));tour=bpy.data.scenes['House | Interior walkthrough']
def material(name,color,rough):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough
 return m,p
glass,p=material('Range | Black induction ceramic glass',(.006,.008,.010),.12);p.inputs['Coat Weight'].default_value=.32;p.inputs['Coat Roughness'].default_value=.10;p.inputs['IOR'].default_value=1.52
ink,_=material('Range | Subtle induction zone printing',(.23,.25,.25),.35)
for scene in [source,tour]:
 bpy.context.window.scene=scene;scene.frame_set(1)
 root=next(o for o in scene.objects if o.type=='EMPTY' and o.get('source_fixture_id')==fid)
 removed=0
 for o in list(root.children):
  if o.name.startswith(('Range | burner cap','Range | cast iron grate')) or o.get('walkthrough_source_name',o.name).startswith('Torus'):
   bpy.data.objects.remove(o,do_unlink=True);removed+=1
 top=next(o for o in root.children if o.get('walkthrough_source_name',o.name).startswith('Black cooktop'))
 top.data.materials.clear();top.data.materials.append(glass);top['appliance_type']='Induction cooktop, four zones';top['source_revision']=18
 for i,(x,y,r) in enumerate([(.19812,-.1778,.09),(.19812,-.4272,.102),(.56388,-.1778,.102),(.56388,-.4272,.09)],1):
  d=bpy.data.curves.new('Induction | Printed zone '+str(i),'CURVE');d.dimensions='3D';d.bevel_depth=.00038;d.bevel_resolution=2
  sp=d.splines.new('POLY');sp.points.add(95);sp.use_cyclic_u=True
  for k,pt in enumerate(sp.points):
   a=k*2*math.pi/96;pt.co=(x+r*math.cos(a),y+r*math.sin(a),.9475,1)
  o=bpy.data.objects.new(d.name,d);root.users_collection[0].objects.link(o);o.parent=root;d.materials.append(ink);o['induction_zone']=i
 root['appliance_type']='Induction range with electric oven';root['drawing_style']=doc['fixtures'][fid]['style'];root['drawing_material']=doc['fixtures'][fid]['material'];root['source_revision']=18
 scene['source_revision']=18;scene['range_notes']='Four-zone induction range with flat black ceramic glass and an electric oven; gas burner caps and cast-iron supports removed.'
 if scene==source:scene.name='Full House | Drawing Revision 18'
 assert not any(o.name.startswith(('Range | burner cap','Range | cast iron grate')) for o in root.children)
 assert len([o for o in root.children if o.get('induction_zone')])==4
 print(scene.name,': removed',removed,'gas parts; four flat induction zones installed.')
(base/'blender/full-house/drawing-snapshot.json').write_text(json.dumps(doc,indent=2)+'\n')
bpy.context.window.scene=source;bpy.ops.wm.save_as_mainfile(filepath=str(base/'blender/full-house/full-house.blend'))
bpy.context.window.scene=tour;tour.camera=bpy.data.objects['Photo | Stove and floating prep shelf'];tour.render.filepath=str(base/'walkthrough/11-induction-range.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'walkthrough/house-walkthrough.blend'))
