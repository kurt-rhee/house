import bpy,ctypes as C,numpy as np,shutil
from pathlib import Path
out=Path('/Users/kurt/Programs/house/sites/house-walkthrough/public/assets');src=out/'lighting.exr'
shutil.copy2(src,Path('/Users/kurt/Programs/house/output/walkthrough/lighting-before-denoise.exr'))
im=bpy.data.images.load(str(src));w,h=im.size;data=np.empty(w*h*4,dtype=np.float32);im.pixels.foreach_get(data);rgba=data.reshape(h,w,4);rgb=np.ascontiguousarray(rgba[:,:,:3]);result=np.empty_like(rgb)
lib=C.CDLL('/Applications/Blender.app/Contents/Resources/lib/libOpenImageDenoise.dylib')
lib.oidnNewDevice.argtypes=[C.c_int];lib.oidnNewDevice.restype=C.c_void_p
lib.oidnCommitDevice.argtypes=[C.c_void_p]
lib.oidnNewFilter.argtypes=[C.c_void_p,C.c_char_p];lib.oidnNewFilter.restype=C.c_void_p
lib.oidnSetSharedFilterImage.argtypes=[C.c_void_p,C.c_char_p,C.c_void_p,C.c_int,C.c_size_t,C.c_size_t,C.c_size_t,C.c_size_t,C.c_size_t]
lib.oidnSetFilterBool.argtypes=[C.c_void_p,C.c_char_p,C.c_bool]
lib.oidnCommitFilter.argtypes=[C.c_void_p];lib.oidnExecuteFilter.argtypes=[C.c_void_p]
lib.oidnGetDeviceError.argtypes=[C.c_void_p,C.POINTER(C.c_char_p)];lib.oidnGetDeviceError.restype=C.c_int
lib.oidnReleaseFilter.argtypes=[C.c_void_p];lib.oidnReleaseDevice.argtypes=[C.c_void_p]
d=lib.oidnNewDevice(1);lib.oidnCommitDevice(d);f=lib.oidnNewFilter(d,b'RT')
for name,array in [(b'color',rgb),(b'output',result)]:lib.oidnSetSharedFilterImage(f,name,C.c_void_p(array.ctypes.data),3,w,h,0,12,w*12)
lib.oidnSetFilterBool(f,b'hdr',True);lib.oidnCommitFilter(f);lib.oidnExecuteFilter(f)
msg=C.c_char_p();error=lib.oidnGetDeviceError(d,C.byref(msg));assert not error,(error,msg.value)
result[rgb.max(axis=2)==0]=0;rgba[:,:,:3]=result
im.pixels.foreach_set(rgba.ravel());im.update()
s=bpy.context.scene;s.render.image_settings.file_format='OPEN_EXR';s.render.image_settings.color_mode='RGB';s.render.image_settings.color_depth='16';s.render.image_settings.exr_codec='PIZ';s.view_settings.view_transform='Raw'
im.save_render(str(out/'lighting-clean.exr'),scene=s)
lib.oidnReleaseFilter(f);lib.oidnReleaseDevice(d)
print('Denoised lightmap',w,h,(out/'lighting-clean.exr').stat().st_size)
