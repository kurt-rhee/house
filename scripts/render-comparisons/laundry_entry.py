"""Render the corrected open position of the laundry exterior door from CAD."""
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

stage = Path(sys.argv[sys.argv.index('--') + 1])
source = Path(__file__).resolve().parents[2] / 'output/floor-plan.house.json'
doc = json.loads(source.read_text())
entry = doc['doors']['6c88355d-3d3e-495b-867b-e437bedc835d']
host = doc['walls'][entry['wall']]
assert entry['swing'] == 'Right' and entry['hinge_at_end']
x = host['start']['x']
y = host['start']['y'] + entry['position'] + entry['width']/2

scene = bpy.data.scenes['Full House | Drawing Revision 51']
bpy.context.window.scene = scene
scene.frame_set(1)
wall_mat = bpy.data.materials['Tour | Warm ivory plaster']
for obj in scene.objects:
    if obj.name.startswith(('Label |', 'Tour ceiling', 'Warm plaster ceiling')):
        obj.hide_render = True
    for slot in obj.material_slots:
        if slot.material and slot.material.name.startswith('View | Semi-transparent plaster'):
            slot.material = wall_mat

wood = bpy.data.materials['Natural oak']
metal = bpy.data.materials['Window and door trim']
width = entry['width']/1000
hinge_x = (x-19383.1)/1000
hinge_y = (10783-y)/1000

def cube(name,location,dimensions,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = dimensions
    ob.data.materials.append(mat)

# The opening is already cut into the model's wall. Show the CAD leaf open
# 90 degrees into the room so both the hinge jamb and swing are apparent.
cube('Laundry exterior door opened inward',
     (hinge_x+width/2,hinge_y,.998),(width-.025,.042,1.97),wood)
cube('Laundry exterior door handle',
     (hinge_x+width-.09,hinge_y-.033,.98),(.093,.04,.043),metal)

def vector_path(points):
    curve = bpy.data.curves.new('Door swing on floor','CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = .015
    curve.bevel_resolution = 2
    spline = curve.splines.new('POLY')
    spline.points.add(len(points)-1)
    for pt, location in zip(spline.points,points):
        pt.co=(*location,1)
    ob = bpy.data.objects.new('CAD swing guide',curve)
    scene.collection.objects.link(ob)
    ob.data.materials.append(wood)

vector_path([(hinge_x+width*math.sin(i*math.pi/48),
              hinge_y+width*math.cos(i*math.pi/48),.018)
             for i in range(25)])

def area_fill(loc,target):
    lamp=bpy.data.lights.new('Laundry fill','AREA')
    lamp.energy=980
    lamp.shape='DISK'
    lamp.size=6
    ob=bpy.data.objects.new('Laundry fill',lamp)
    scene.collection.objects.link(ob)
    ob.location=loc
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

loc,target,scale = (-3.78,3.30,11.1),(-3.83,4.93,.35),4.6
data = bpy.data.cameras.new('Matched laundry entry')
camera = bpy.data.objects.new('Matched laundry entry',data)
scene.collection.objects.link(camera)
camera.location=loc
camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO'
data.ortho_scale=scale
scene.camera=camera
area_fill(loc,target)
scene.render.engine='CYCLES'
scene.cycles.samples=int(os.environ.get('HOUSE_RENDER_SAMPLES','12'))
scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED'
scene.render.threads=int(os.environ.get('HOUSE_RENDER_THREADS','10'))
scene.render.resolution_x,scene.render.resolution_y=1040,650
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='JPEG'
scene.render.image_settings.quality=89
scene.render.filepath=str(stage/'laundry-entry.jpg')
bpy.ops.render.render(write_still=True)
