import bpy,json
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output/blender/full-house');s=bpy.context.scene;doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text())
removed=[]
for o in [o for o in s.objects if o.name.startswith(('Oatmeal upholstered headboard','Low headboard'))]:
 removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
bed=next(o for o in s.objects if o.name.startswith('6 inch floor mattress | king'))
bed['source_fixture_id']='1b621dde-f0da-44d7-90a1-3a31bb2ed549';bed['headboard']=False
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident in doc['fixtures']:
  f=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f['width'],f['depth']]
  for field in ['material','style']:
   if f.get(field):o['drawing_'+field]=f[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision']);s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')});(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
active=next(o for o in s.objects if o.name=='Current | Transparent walls');s.camera=active;bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
for camera,file,w,h in [('Current | Transparent walls','09-transparent-walls.png',2000,1800),('Current | Main bedroom wardrobe','07-main-bedroom-wardrobe.png',1600,1600)]:
 s.camera=next(o for o in s.objects if o.name==camera);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=active;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'09-transparent-walls.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
assert not any(o.name.startswith(('Oatmeal upholstered headboard','Low headboard')) for o in s.objects)
print('Removed main bedroom headboard panels:',removed)
