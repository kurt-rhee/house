import bpy,os
from pathlib import Path
out=Path('/Users/kurt/Programs/house/sites/house-walkthrough/public/assets')
im=bpy.data.images.load(str(out/'lighting.exr'));s=bpy.context.scene
s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';s.render.image_settings.exr_codec='PIZ';s.view_settings.view_transform='Raw'
im.save_render(str(out/'lighting-compact.exr'),scene=s)
os.replace(out/'lighting-compact.exr',out/'lighting.exr')
print('Lightmap bytes', (out/'lighting.exr').stat().st_size)
