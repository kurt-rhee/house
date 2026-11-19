"""Blender reference reconstruction traced from docs/floor-plan-before-reference.png.

Run in full-house.blend. Pixel coordinates refer to the 2354 × 1318 original
reference. Use neutral massing for undocumented forms, elevations and finishes.
The After artwork is based on the current CAD and saved Blender scenes.
"""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCALE = .01145
WALL = 2.4384
stage = Path(sys.argv[sys.argv.index('--') + 1])
requested = set(sys.argv[sys.argv.index('--') + 2:])
stage.mkdir(parents=True, exist_ok=True)
full = bpy.data.scenes['Full House | Drawing Revision 51']
tour = bpy.data.scenes['House | Interior walkthrough']
original = bpy.data.scenes.new('Original | A-01 drawing reconstruction')
bpy.context.window.scene = original


def point(x, y, z=0.0):
    return (x*SCALE-19.3831, 10.783-y*SCALE, z)


def material(name, color, roughness=.6):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    return mat


plaster = material('Original | Wall', (.72,.72,.66))
floor = material('Original | Floor', (.54,.52,.45))
concrete = material('Original | Concrete', (.51,.53,.51))
ground = material('Original | Ground', (.39,.42,.38))
cabinet = material('Original | Casework', (.54,.56,.55))
countertop = material('Original | Worktop', (.28,.36,.38))
ceramic = material('Original | Fixtures', (.88,.86,.78))
door = material('Original | Door', (.44,.44,.40))
gray = material('Original | Appliance', (.32,.39,.40))
pane = material('Original | Glazing', (.54,.66,.70), .35)


def box(name, p, size, mat, angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.rotation_euler.z = angle
    ob.data.materials.append(mat)
    bevel = ob.modifiers.new('Readable edges', 'BEVEL')
    bevel.width = .012
    bevel.segments = 2
    ob.modifiers.new('Smooth planar faces', 'WEIGHTED_NORMAL')
    return ob


def rect(name, x0, y0, x1, y1, z0, z1, mat, angle=0):
    return box(name, point((x0+x1)/2,(y0+y1)/2,(z0+z1)/2),
               ((x1-x0)*SCALE,(y1-y0)*SCALE,z1-z0),mat,angle)


def recess(body, name, coordinates, radius):
    cutter = rect(name,*coordinates,countertop)
    edge = cutter.modifiers[0]
    edge.width = radius
    edge.segments = 6
    bpy.context.view_layer.objects.active = cutter
    bpy.ops.object.modifier_apply(modifier=edge.name)
    bpy.context.view_layer.objects.active = body
    boolean = body.modifiers.new('Recess', 'BOOLEAN')
    boolean.object = cutter
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


def basin(name,x0,y0,x1,y1,bottom,top,rim,radius):
    body = rect(name,x0,y0,x1,y1,bottom,top,ceramic)
    recess(body, name+' cavity',
           (x0+rim,y0+rim,x1-rim,y1-rim,bottom+.08,top+.26), radius)


def ellipse(name, x, y, z, dimensions):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=point(x,y,z))
    ob=bpy.context.object
    ob.name=name
    ob.dimensions=dimensions
    ob.data.materials.append(ceramic)


def poly(name, vertices, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([point(x,y,-.015) for x,y in vertices], [], [tuple(reversed(range(len(vertices))))])
    mesh.update()
    ob = bpy.data.objects.new(name,mesh)
    original.collection.objects.link(ob)
    ob.data.materials.append(mat)
    solid = ob.modifiers.new('Floor slab', 'SOLIDIFY')
    solid.thickness = .12
    return ob


partition_sets = {}
def wall(name, start, end, openings=(), ext=False):
    horizontal = start[1]==end[1]
    index = 0 if horizontal else 1
    constant = start[1-index]
    assert constant==end[1-index]
    thickness = .1578 if ext else .1052
    begin,finish = start[index],end[index]
    pieces = []
    partition_sets[name] = pieces
    def segment(a,b,z0,z1,mat,width=None):
        if b-a<.15 or z1-z0<.005:
            return
        u=(a+b)/2
        coords=(u,constant) if horizontal else (constant,u)
        long=(b-a)*SCALE
        dim=width or thickness
        ob=box(name,point(*coords,(z0+z1)/2), (long,dim,z1-z0) if horizontal else (dim,long,z1-z0),mat)
        pieces.append(ob)
    cursor = begin
    for a,b,kind in openings:
        assert cursor<=a<b<=finish,(name,cursor,a,b,finish)
        sill,head = {'w': (1,2.1), 'wet': (1.45,2.05), 'd': (0,2.032), 'free': (0,2.032),
                     'barn': (0,2.032), 'opening': (0,2.1336)}[kind]
        segment(cursor,a,0,WALL,plaster)
        segment(a,b,0,sill,plaster)
        segment(a,b,head,WALL,plaster)
        if kind in ('w','wet'):
            segment(a,b,sill,sill+.055,door,thickness+.024)
            segment(a,b,head-.055,head,door,thickness+.024)
            segment(a+5,b-5,sill+.055,head-.055,pane,.022)
            for x in (a+2.5,(a+b)/2,b-2.5):
                segment(x-2,x+2,sill,head,door,thickness+.015)
        elif kind in ('d','barn'):
            segment(a+3,b-3,.013,head-.025,door,.046)
            if kind=='barn':
                for z in (.42,.84,1.26,1.68):
                    segment(a+2,b-2,z,z+.012,cabinet,.052)
        cursor=b
    segment(cursor,finish,0,WALL,plaster)


# Original detached building. The small garage predates the office, and the
# bath partition and enclosed space at the ADU door come from A-01.
poly('Detached floor',[(80,118),(342,118),(342,59),(846,59),(846,772),(342,772),(342,534),(80,534)],concrete)
wall('Small garage, top',(80,118),(342,118),ext=True)
wall('Small garage, left',(80,118),(80,534),[(206,290,'w')],True)
wall('Small garage, bottom',(80,534),(342,534),[(125,192,'d')],True)
wall('Garage dividing wall',(342,118),(342,534),[(260,327,'d')])
wall('Large garage, top',(342,59),(846,59),ext=True)
wall('Large garage, left return',(342,59),(342,118),ext=True)
wall('Large garage and bedroom, right',(846,59),(846,772),[(87,475,'barn'),(540,607,'d'),(680,766,'w')],True)
wall('Garage and bedroom partition',(342,515),(846,515),[(555,664,'opening')])
wall('Garage closet front',(342,461),(541,461))
wall('Garage partition, left step',(541,461),(541,515))
wall('Garage partition, cross step',(541,461),(681,461))
wall('Garage partition, right step',(681,461),(681,515))
wall('Detached wing, left',(342,534),(342,772),[(548,597,'wet')],True)
wall('Detached wing, bottom',(342,772),(846,772),[(459,526,'d'),(756,838,'w')],True)
wall('ADU bathroom and enclosed-space partition',(541,515),(541,772),[(518,584,'free')])
wall('ADU bath, lower',(342,627),(541,627))
basin('ADU bath tub',349,526,411,620,0,.51,5,.11)
rect('ADU bath vanity',484,580,533,624,.1,.76,cabinet)
basin('ADU bath basin',484,580,533,624,.72,.85,5,.085)
rect('ADU bath toilet tank',434,605,469,623,0,.74,ceramic)
ellipse('ADU toilet bowl',451,585,.37,(.36,.50,.23))

# Main dwelling, including the original single hall bath and two living rooms.
poly('Main house floor',[(1510,193),(2107,193),(2107,735),(2284,735),(2284,1155),
      (1408,1155),(1408,848),(1460,848),(1460,562),(1322,562),(1322,341),(1510,341)],floor)
wall('Main house, top',(1510,193),(2107,193),[(1517,1601,'w'),(1799,1859,'w'),(2029,2088,'w')],True)
wall('Kitchen, left',(1510,193),(1510,562),[(483,551,'free')],True)
wall('Laundry, top',(1322,341),(1510,341),[(1338,1451,'w')],True)
wall('Laundry, left',(1322,341),(1322,562),[(357,456,'w'),(478,547,'free')],True)
rect('Original laundry exterior door opened inward',1322,544,1388,548,.013,1.983,door)
wall('Laundry, bottom',(1322,562),(1518,562),ext=True)
wall('Kitchen dining partition',(1784,193),(1784,849),[(267,335,'opening')])
wall('Dining and living',(1784,410),(2107,410),[(1839,2052,'opening')])
wall('Dining and living, right',(2107,193),(2107,735),[(264,344,'w'),(455,536,'w'),(600,680,'w')],True)
wall('Entry top',(2107,735),(2284,735),[(2117,2185,'free')],True)
wall('Entry left return',(2107,735),(2107,849),[(745,840,'opening')])
wall('Entry closet',(2210,735),(2210,849),[(772,827,'free')])
wall('Front bedroom, right',(2284,735),(2284,1155),ext=True)
wall('Living, left',(1460,562),(1460,848),[(582,655,'w'),(765,840,'w')],True)
wall('Kitchen closet, top',(1607,493),(1784,493))
wall('Kitchen closet, left',(1607,493),(1607,561),[(498,553,'free')])
wall('Kitchen closet, bottom',(1607,561),(1784,561),[(1699,1769,'free')])
wall('Hallway, upper',(1408,849),(2284,849),[(1705,1773,'free'),(1793,1862,'free')])
wall('Main bedroom, left',(1408,849),(1408,1155),[(861,941,'w')],True)
wall('Main house, bottom',(1408,1155),(2284,1155),[(1587,1665,'w'),(1785,1840,'wet')],True)
wall('Main bedroom, hall and closet',(1689,849),(1689,1155),[(858,926,'free'),(1013,1083,'free')])
wall('Guest bedroom, hall and closet',(1985,849),(1985,1155),[(858,926,'free'),(1013,1083,'free')])
wall('Hall bath, top',(1689,938),(1985,938),[(1694,1740,'free'),(1754,1823,'free'),(1928,1980,'free')])
wall('Hall bath, left',(1747,938),(1747,1155))
wall('Hall bath, right',(1920,938),(1920,1155))
wall('Bedroom closet returns 1',(1689,999),(1747,999))
wall('Bedroom closet returns 2',(1920,999),(1985,999))
wall('Hall bath tub privacy wall',(1850,1019),(1920,1019))
basin('Original main tub',1855,1027,1915,1147,0,.51,5,.12)
rect('Original main basin cabinet',1752,1020,1796,1124,.1,.74,cabinet)
basin('Original main sink',1752,1058,1795,1113,.70,.82,5,.08)
rect('Original main toilet tank',1898,962,1914,998,0,.76,ceramic)
ellipse('Original main toilet bowl',1878,980,.38,(.51,.39,.23))

# Original fixture and worktop footprints visible in the reference. Their
# elevation and styling are intentionally generic.
rect('Kitchen return base',1518,223,1567,428,0,.86,cabinet)
rect('Kitchen return worktop',1517,221,1569,427,.86,.91,countertop)
rect('Kitchen corner counter run',1518,202,1708,240,0,.91,cabinet)
rect('Kitchen corner sink rim',1537,219,1584,268,.86,.95,ceramic,-math.pi/4)
rect('Sink bowl 1',1537,232,1555,253,.94,.96,countertop,-math.pi/4)
rect('Sink bowl 2',1559,220,1577,240,.94,.96,countertop,-math.pi/4)
rect('Stove',1518,372,1566,427,0,.92,gray)
for x,y in ((1532,386),(1553,386),(1532,406),(1553,406)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.077,depth=.018,location=point(x,y,.928))
    bpy.context.object.data.materials.append(countertop)
rect('Original refrigerator (traced appliance footprint)',1707,202,1775,263,0,1.83,gray)
rect('Original laundry appliance one',1334,353,1389,413,0,.91,ceramic)
rect('Original laundry appliance two',1396,353,1451,413,0,.91,ceramic)
rect('Original laundry cupboard',1472,349,1505,472,0,2.12,cabinet)
rect('Original laundry landing',1207,434,1315,568,-.14,-.055,concrete)
rect('Original front porch',2114,332,2237,733,-.16,-.055,concrete)
rect('Site',-180,-310,2550,1530,-.32,-.23,ground)


def lamp(name, location, target, power, size):
    light = bpy.data.lights.new(name,'AREA')
    light.energy = power
    light.shape = 'DISK'
    light.size = size
    light.color = (1,.96,.9)
    ob = bpy.data.objects.new(name, light)
    original.collection.objects.link(ob)
    ob.location = location
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z','Y').to_euler()


world = bpy.data.worlds.new('Original | Neutral daylight')
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
bg.inputs[0].default_value = (.78,.84,.92,1)
bg.inputs[1].default_value = .55
original.world = world
lamp('Main daylight',(-1,5,10),(0,3,0),2400,9)
lamp('Detached daylight',(-14,5,10),(-14,6,0),2700,8)
lamp('Front fill',(-11,-9,8),(-12,4,1),1750,10)

# Match the After camera and projection. Cut the reference in the same places
# for like-for-like cutaway views.
views = [
    ('range',(tour,'Photo | Stove and floating prep shelf'),()),
    ('sink',(tour,'Photo | Sink and floating shelves'),()),
    ('lantern',(tour,'Photo | Kitchen lantern and daylight'),()),
    ('round-blind',((-.05,7.05,1.62),(-1.99,7.83,1.73),39),()),
    ('appliances',(tour,'Photo | Fridge and microwave shelves'),()),
    ('portal',(tour,'Tour camera | Dining / arch'),()),
    ('dining-header',((2.97,2.64,1.68),(2.94,6.63,1.47),22),()),
    ('laundry-entry',((-3.78,3.30,11.1),(-3.83,4.93,.35),4.6,True),()),
    ('laundry-front',((-3.45,4.65,1.61),(-3.21,6.60,1.17),21),()),
    ('laundry-storage',((-3.50,4.67,1.72),(-3.31,6.18,.98),23),()),
    ('laundry-door',((-1.0,6.78,1.66),(-2.3,5.15,1.35),25),()),
    ('layout',((8,-11,29),(1.37,3.05,0),14.4,True),()),
    ('bedroom3',((-2.47,1.48,1.58),(-1.06,3.78,1.1),20),()),
    ('wardrobe-detail',(full,'Current | Main bedroom wardrobe'),('Main house, bottom','Main bedroom, hall and closet')),
    ('main-slider',((-1.30,-1.50,1.58),(-3.10,-.52,1.20),23),()),
    ('bathrooms-final',((1.82,-6.05,9.62),(1.82,-1.18,.7),5.6,True),('Main house, bottom',)),
    ('office',((-23,1.30,4.3),(-17.05,6.25,1.3),6.85,True),()),
    ('adu-window',((-18.4,-2.8,4.0),(-12.65,2.75,1.15),7.5,True),()),
    ('adu-open',((-15.4,-3.5,8.8),(-12.67,3.25,.55),6.65,True),('Detached wing, bottom','Detached wing, left')),
]


def camera_for(view):
    if len(view)==2:
        other, name = view
        bpy.context.window.scene = other
        other.frame_set(1)
        bpy.context.view_layer.update()
        src=other.objects[name]
        depsgraph=bpy.context.evaluated_depsgraph_get()
        matrix=src.evaluated_get(depsgraph).matrix_world.copy()
        data = src.data.copy()
        bpy.context.window.scene = original
        c = bpy.data.objects.new('Matched '+name,data)
        original.collection.objects.link(c)
        c.matrix_world=matrix
    else:
        loc,target,lens,*ortho = view
        data=bpy.data.cameras.new('Matched view')
        c=bpy.data.objects.new('Matched view',data)
        original.collection.objects.link(c)
        c.location=loc
        c.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
        if ortho:
            data.type='ORTHO'
            data.ortho_scale=lens
        else:
            data.lens=lens
    return c


original.render.engine='CYCLES'
original.cycles.samples=int(os.environ.get('HOUSE_RENDER_SAMPLES','12'))
original.cycles.use_denoising=True
original.render.threads_mode='FIXED'
original.render.threads=int(os.environ.get('HOUSE_RENDER_THREADS','10'))
original.render.resolution_x=1040
original.render.resolution_y=650
original.render.resolution_percentage=100
original.render.image_settings.file_format='JPEG'
original.render.image_settings.quality=89
for key, view, cuts in views:
    if requested and key not in requested:
        continue
    objects = [ob for name in cuts for ob in partition_sets[name]]
    for ob in objects:
        ob.hide_render=True
    original.camera=camera_for(view)
    original.render.filepath=str(stage / f'before-{key}.jpg')
    bpy.ops.render.render(write_still=True)
    for ob in objects:
        ob.hide_render=False
    print('DONE',key,flush=True)
