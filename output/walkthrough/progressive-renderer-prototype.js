import { WebGLPathTracer, DenoiseMaterial } from 'three-gpu-pathtracer';
import { GenerateMeshBVHWorker } from 'three-mesh-bvh/worker';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';

// Keep the walking renderer independent: expensive lighting work runs only at rest.
export async function createPhotorealRenderer(renderer,scene,camera,rasterize){
 const tracer=new WebGLPathTracer(renderer),worker=new GenerateMeshBVHWorker();
 tracer.setBVHWorker(worker);tracer.bounces=7;tracer.transmissiveBounces=6;
 tracer.filterGlossyFactor=.5;tracer.tiles.set(3,3);tracer.textureSize.set(1024,1024);
 tracer.renderScale=Math.min(1,1/renderer.getPixelRatio());
 tracer.renderDelay=350;tracer.minSamples=32;tracer.fadeDuration=700;tracer.dynamicLowRes=false;
 tracer.rasterizeSceneCallback=rasterize;
 const denoise=new FullScreenQuad(new DenoiseMaterial({sigma:3,kSigma:1.5,threshold:.35}));
 tracer.renderToCanvasCallback=(target,r,quad)=>{
  denoise.material.map=target.texture;denoise.material.opacity=quad.material.opacity;
  const clear=r.autoClear;r.autoClear=false;denoise.material.transparent=true;
  denoise.material.blending=quad.material.blending;denoise.render(r);r.autoClear=clear;
 };
 let building=false,valid=false,failed=false,dirty=false,version=0;
 async function rebuild(){
  if(building||failed)return;building=true;valid=false;const capturedVersion=version;
  try{await tracer.setSceneAsync(scene,camera);dirty=version!==capturedVersion;valid=!dirty;tracer.reset();}
  catch(error){failed=true;console.warn('Detailed lighting unavailable; keeping the walking renderer.',error);}
  finally{building=false;}
 }
 await rebuild();
 let idleSince=performance.now();
 return {
  get compiling(){return tracer.isCompiling},get samples(){return tracer.samples},get ready(){return valid&&!failed},get building(){return building},
  invalidateGeometry(){version++;dirty=true;valid=false;idleSince=performance.now();},
  render(moving){
   if(failed)return false;
   if(moving){idleSince=performance.now();tracer.updateCamera();tracer.reset();return false;}
   if(performance.now()-idleSince<450)return false;
   if(dirty&&!building){rebuild();return false;}
   if(!valid||building)return false;
   try{if(tracer.samples<256)tracer.renderSample();return true;}
   catch(error){failed=true;console.warn('Detailed lighting unavailable; keeping the walking renderer.',error);return false;}
  },
  refresh(){tracer.updateMaterials();tracer.updateLights();tracer.updateEnvironment();tracer.reset();},
  reset(){idleSince=performance.now();tracer.updateCamera();tracer.reset();},
  dispose(){worker.dispose();tracer.dispose();denoise.dispose();},
 };
}
