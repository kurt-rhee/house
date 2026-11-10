import bpy,json
from pathlib import Path
base=Path('/Users/kurt/Programs/house/output/blender/full-house');doc=json.loads((base.parent.parent/'floor-plan.house.json').read_text());s=bpy.context.scene
for o in s.objects:
 ident=o.get('source_fixture_id')
 if ident not in doc['fixtures']:continue
 f=doc['fixtures'][ident];o['source_revision']=doc['revision'];o['plan_footprint_mm']=[f['width'],f['depth']]
 for field in ['material','style']:
  if f.get(field):o['drawing_'+field]=f[field]
s['source_revision']=doc['revision'];s.name='Full House | Drawing Revision '+str(doc['revision'])
s['material_assignments']=json.dumps({f['id']:{'material':f.get('material'),'style':f.get('style')} for f in doc['fixtures'].values() if f.get('material') or f.get('style')})
(base/'drawing-snapshot.json').write_text(json.dumps(doc,indent=2))
main=next(o for o in s.objects if o.name=='Current | Main house')
for name,file,w,h in [('Current | Whole property','01-whole-property.png',2400,1500),('House | Plan.002','03-overhead-plan.png',2200,1400)]:
 s.camera=next(o for o in s.objects if o.name==name);s.render.resolution_x=w;s.render.resolution_y=h;s.render.filepath=str(base/file);bpy.ops.render.render(write_still=True)
s.camera=main;s.render.resolution_x=2000;s.render.resolution_y=1800;s.render.filepath=str(base/'02-main-house.png');bpy.ops.wm.save_as_mainfile(filepath=str(base/'full-house.blend'))
print('Blender properties and snapshots synchronized with drawing revision',doc['revision'])
