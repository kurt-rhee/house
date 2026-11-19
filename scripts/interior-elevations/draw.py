"""Generate 11 × 17 vector sheets from the coordinated CAD and electrical layout.

Usage: python3 scripts/interior-elevations/draw.py /path/to/staging-directory
Convert each SVG with rsvg-convert -f pdf. Keep render galleries last.
"""
import argparse
import json
from html import escape
from math import cos, pi, radians, sin
from pathlib import Path
from textwrap import wrap

from layout import DEVICES, DIRECTIONS, FACES, HEIGHT, LABELS, MM, PROJECT, SHEETS, is_changed_opening

INK = '#1c2934'
MUTED = '#4e606c'
BLUE = '#005d84'
LINE = '#a7b2b9'
PALE = '#ecf1f4'
FIELD = '#886027'
FONT = 'Helvetica, Arial, sans-serif'
STYLES = {
    'cabinet': ('#eee1ce', '#73644b'), 'shelves': ('#faf1e4', '#73644b'),
    'stone': ('#c9cdcc', '#505958'), 'appliance': ('#e3e9ea', '#65777c'),
    'plaster': ('#f1ebe0', '#8b8171'), 'porcelain': ('#f8f9f7', '#6d7e83'),
    'glass': ('#e3f1f4', '#74949d'), 'outline': ('none', '#65777c'),
    'existing': ('#f2ece1', FIELD),
}
OPEN_LABEL = {'Window': 'Window', 'Round': 'Round lite', 'Pocket': 'Pocket door',
              'Hinged': 'Hinged door', 'SlidingGlass': 'Glazed slider', 'RoundedArch': 'Arch',
              'Portal': 'Open passage', 'Garage': 'Overhead door'}
CIRCUITS = [
    ('S1 / S2', 'Main kitchen counters and dining', 'Two 120 V, 20 A', 'AFCI + GFCI in kitchen'),
    ('DW', 'Dishwasher in adjacent sink base', 'Individual, per nameplate', 'AFCI + GFCI'),
    ('RG', 'Induction range', '240 V class, per nameplate', 'GFCI, connection per listing'),
    ('HD', 'Range hood connection', 'Per nameplate / listing', 'AFCI and GFCI if receptacle'),
    ('MW', 'Built-in microwave', 'Individual, per nameplate', 'AFCI + GFCI'),
    ('RF', 'Refrigerator', 'Individual 120 V, 15 A min.', 'AFCI + GFCI'),
    ('LA', 'Laundry receptacles', '120 V, 20 A min.', 'AFCI + GFCI'),
    ('BM', 'Main bath basin receptacles', '120 V, 20 A, baths only', 'GFCI'),
    ('BR1–3 / LV', 'Main bedrooms, living and hall', '120 V, 15 or 20 A', 'AFCI'),
    ('OF / AD', 'Office / detached living-area power', '120 V, 15 or 20 A', 'AFCI, verify ADU feed'),
    ('BA', 'Detached bath basin receptacle', '120 V, 20 A, bath only', 'GFCI, verify ADU feed'),
    ('GA', 'Garage receptacles', '120 V, 20 A min.', 'GFCI'),
]
NOTES = {
    'I-01': ['The modeled range-to-hood clearance is about 21½″. Set hood height to the selected equipment listing.'],
    'I-02': ['Check refrigerator depth and ventilation against the selected appliance. Arch spring is 5′–10″ AFF (design).'],
    'I-05': ['Confirm valve and fixture rough-ins with selected products.'],
    'I-06': ['Confirm glazing and valve rough-ins with selected products.'],
    'I-13': ['Set the east window sill and head with the selected unit before framing.'],
    'I-14': ['The floor area at the former partition remains open. Confirm sill and head with the selected window before framing.'],
}
INDEX = [('A-00–06', 'Site, floor plans and exterior elevations'),
         ('E-00', 'Electrical criteria and branch circuit intent'),
         ('E-01', 'Main house receptacle plan'), ('E-02', 'Detached wing receptacle plan'),
         ('P-01–03', 'Plumbing fixture plan, utilities and DWV'),
         *[(number, name.replace(' | ', ' — ')) for number,name,_ in SHEETS],
         ('A-07–13', 'Blender render views')]


def ft(mm, precision=4):
    n = round(mm / MM * precision)
    feet, inch_count = divmod(n, 12 * precision)
    inches, fraction = divmod(inch_count, precision)
    quarters = {1:'¼', 2:'½', 3:'¾'}
    return f'{feet}′–{inches}{quarters.get(fraction, "")}″'


def aff(mm):
    return f'{mm / MM:g}″'


class Canvas:
    def __init__(self):
        self.items = ['<svg xmlns="http://www.w3.org/2000/svg" width="17in" height="11in" viewBox="0 0 1224 792">']

    def rect(self,x,y,w,h,fill='white',stroke='none',width=1,dash=''):
        attr = f' stroke-dasharray="{dash}"' if dash else ''
        self.items.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{attr}/>')

    def path(self,d,stroke=INK,width=1,fill='none',dash=''):
        attr = f' stroke-dasharray="{dash}"' if dash else ''
        self.items.append(f'<path d="{d}" stroke="{stroke}" stroke-width="{width}" fill="{fill}"{attr}/>')

    def line(self,x,y,u,v,stroke=INK,width=1,dash=''):
        self.path(f'M{x:.2f},{y:.2f} L{u:.2f},{v:.2f}',stroke,width,dash=dash)

    def circle(self,x,y,r,fill,stroke,width=1):
        self.items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def text(self,x,y,value,size=10,colour=INK,weight=400,anchor='start'):
        self.items.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" font-size="{size}" fill="{colour}" '
                          f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')

    def paragraph(self,x,y,value,width=85,size=10,leading=13,colour=MUTED):
        for line in wrap(value,width,break_long_words=False,break_on_hyphens=False):
            self.text(x,y,line,size,colour)
            y += leading
        return y

    def write(self, path):
        path.write_text('\n'.join([*self.items, '</svg>']))


def base(sheet,title,subtitle,scope):
    c = Canvas()
    c.rect(0,0,1224,792)
    c.text(34,33,'214 N KATHERINE DRIVE  /  VENTURA, CA 93003',11,BLUE,700)
    c.text(1190,33,scope,10,MUTED,700,'end')
    c.text(34,68,title,27,INK,700)
    c.text(35,89,subtitle,10,MUTED)
    c.line(34,103,1190,103,INK,1.2)
    c.line(34,739,1190,739,INK,1.2)
    c.text(35,759,'PROPOSED REMODEL  /  BUILDER COORDINATION',10,INK,700)
    c.text(35,775,'Field-verify existing work and all rough-ins.  |  CAD rev. '+str(PROJECT['revision'])+'  |  November 2026',9,MUTED)
    c.text(1190,771,sheet,24,INK,700,'end')
    return c


def issue_notes(c,sheet,y):
    for message in NOTES.get(sheet, ()):
        y = c.paragraph(35,y,message,173,9.5,12) + 2


def dim(c, a, b, y, solid, size=9):
    c.line(a,y,b,y,MUTED,.6)
    for x in (a,b):
        c.line(x,y-3,x,y+3,MUTED,.65)
        c.line(x-2,y+2,x+2,y-2,MUTED,.65)
    c.text((a+b)/2,y-4,solid,size,MUTED,500,'middle')


def face_box(c, face, x0, y0, width, style):
    k = (18 if style == 'standard' else 27) / 304.8
    x = x0 + (width - k * face.span) / 2
    floor = y0 + (171 if style == 'standard' else 261)
    top = floor - HEIGHT * k
    end = x + face.span * k
    c.text(x0+10,y0+13,face.id,13,BLUE,700)
    c.text(x0+45,y0+13,f'{DIRECTIONS[face.direction]} wall',13,INK,700)
    c.rect(x,top,end-x,floor-top,'#f8f9f8',INK,1.25)
    c.line(x-12,top,x,top,MUTED,.5)
    c.line(x-12,floor,x,floor,MUTED,.5)
    c.line(x-9,top,x-9,floor,MUTED,.5)
    c.text(x-13,(top+floor)/2+3,'8′–0″',8,MUTED,400,'end')

    def stations(a,b):
        return tuple(sorted((x + face.offset(a)*k, x + face.offset(b)*k)))

    op_index = 0
    for opening in face.openings:
        changed = is_changed_opening(face, opening)
        op_index += changed
        a,b = stations(opening.low,opening.high)
        provisional = opening.sill is None or opening.head is None
        floor_opening = opening.sill == 0
        sill = opening.sill if opening.sill is not None else 1000
        head = opening.head if opening.head is not None else 2032
        ya,yb = floor-head*k,floor-sill*k
        stroke = (FIELD if provisional else INK) if changed else LINE
        if opening.kind == 'Round':
            c.circle((a+b)/2,(ya+yb)/2,(b-a)/2,'#e3f1f4',INK)
        elif opening.kind == 'RoundedArch':
            spring = floor-1780*k
            c.path(f'M{a},{floor} V{spring} A{(b-a)/2},{spring-ya} 0 0 1 {b},{spring} V{floor} Z',INK,1,'white')
        else:
            c.rect(a,ya,b-a,yb-ya,'white' if floor_opening else '#e3f1f4',stroke,1,'4 3' if provisional else '')
            if opening.kind in ('Window','SlidingGlass','Garage') and not provisional:
                if opening.kind == 'Garage':
                    for i in range(1,4):
                        c.line(a,ya+(yb-ya)*i/4,b,ya+(yb-ya)*i/4,LINE,.65)
                else:
                    c.line((a+b)/2,ya+2,(a+b)/2,yb-2,LINE,.65)
            if opening.kind == 'Hinged' and not provisional:
                knob = b-8 if face.offset(opening.hinge_station) < face.offset(opening.center) else a+8
                c.circle(knob,floor-36*MM*k,1.3,INK,INK,.5)
        if changed:
            c.text((a+b)/2,ya+11,f'O{op_index}',8,stroke,700,'middle')

    for index,d in enumerate(face.details,1):
        a,b = stations(max(face.low,d.low),min(face.high,d.high))
        upper,lower = floor-d.top*k, floor-d.bottom*k
        fill,stroke = STYLES[d.style]
        c.rect(a,upper,b-a,lower-upper,fill,stroke,.8,'3 2' if d.style=='existing' else '')
        if d.style == 'shelves':
            for i in range(1,6):
                c.line(a,upper+(lower-upper)*i/6,b,upper+(lower-upper)*i/6,stroke,.6)
        if d.style == 'cabinet' and b-a>54:
            c.line((a+b)/2,upper,(a+b)/2,lower,stroke,.55)
        if b-a>=24 and lower-upper>=17:
            c.text((a+b)/2,(upper+lower)/2+3,f'F{index}',7.7,stroke,700,'middle')

    c.line(x-5,floor,end+5,floor,INK,1.15)
    c.text(end+7,floor+2,'FF',7.5,MUTED,700)
    c.line(x,floor+2,x,floor+17,MUTED,.55)
    c.line(end,floor+2,end,floor+17,MUTED,.55)
    c.text(x-8,floor+19,'0',8,MUTED,700,'middle')
    dim(c,x,end,floor+15,ft(face.span))
    return floor+34


def face_schedule(c,f,x,y,width,detail_columns=1):
    l = x + 4
    for index,op in enumerate((op for op in f.openings if is_changed_opening(f, op)),1):
        height = ('verify sill/head' if op.sill is None else
                  'verify head' if op.head is None else
                  f'CL {ft((op.sill+op.head)/2)} AFF' if op.kind=='Round' else
                  f'{ft(op.sill)} sill / {ft(op.head)} head' if op.sill else f'{ft(op.head)} head')
        lead = 'Ø ' if op.kind=='Round' else ''
        c.text(l,y,f'O{index}',8,MUTED,700)
        jamb = min(f.offset(op.low),f.offset(op.high))
        c.text(l+25,y,f'{OPEN_LABEL[op.kind]}   /   {ft(jamb)} from left   /   {lead}{ft(op.high-op.low)} wide   /   {height}',8.2,MUTED)
        y += 10.5
    if detail_columns == 0:
        return y
    for index,d in enumerate(f.details,1):
        col = (index-1) % detail_columns
        row = (index-1) // detail_columns
        xx,yy = l + col * width/detail_columns, y + 11*row
        lo = max(f.low,d.low)
        hi = min(f.high,d.high)
        left = min(f.offset(lo),f.offset(hi))
        c.text(xx,yy,f'F{index}  {d.name}   |   {ft(left)} L   {ft(hi-lo)} W   {ft(d.bottom)}–{ft(d.top)} AFF',8,MUTED)
    return y + 11 * ((len(f.details) + detail_columns-1) // detail_columns)


def elevation(number,title,keys):
    large = len(keys) <= 2
    scale = '⅜″ = 1′–0″' if large else '¼″ = 1′–0″'
    c = base(number,title,'Viewed from inside. Horizontal dimensions start at the left finish face. O tags identify changed openings. AFF means above finished floor.', 'INTERIOR ELEVATIONS')
    c.text(1187,89,f'{scale}  |  PRINT AT ACTUAL SIZE',9,MUTED,700,'end')
    if large:
        for index,key in enumerate(keys):
            f = FACES[key]
            x = 337 if len(keys) == 1 else 35 + 585*index
            y = face_box(c,f,x,123,550,'detail')
            face_schedule(c,f,x+4,y,548)
        issue_notes(c,number,690)
    else:
        for index,key in enumerate(keys):
            f = FACES[key]
            x = 35 + 585*(index%2)
            row = index//2
            y = face_box(c,f,x,114+row*310,550,'standard')
            last = face_schedule(c,f,x+4,y,548,2)
            assert last < (428 if row==0 else 708), (number,key,last)
        issue_notes(c,number,711)
    return c


def device_schedule(c, x, devices):
    c.text(x,205,'Receptacle and rough-in schedule',14,INK,700)
    c.text(x,222,'Along-wall dimensions start at the named finished end and run to the box center.',9.4,MUTED)
    c.text(x,236,'AFF means above finished floor, measured to the box center.',9.4,MUTED)
    columns = (x+4, x+47, x+130, x+187, x+258, x+293, x+325)
    headers = ('Tag', 'Room', 'Wall', 'From end', 'AFF', 'Ckt', 'Device')
    c.rect(x,247,467,17,PALE)
    for column, label in zip(columns, headers):
        c.text(column,259,label,9,INK,700)
    end = {'S':'E', 'N':'W', 'W':'S', 'E':'N'}
    wall_names = {'U1':'S (garage)', 'U5':'S (bath)'}
    room = None
    y = 276
    for d in devices:
        f = FACES[d.face]
        if room != f.room:
            c.line(x,y-9,x+467,y-9,LINE,.5)
            room = f.room
            room_label = room
        else:
            room_label = ''
        station = f'{ft(f.offset(d.station))} from {end[f.direction]}'
        values = (d.tag, room_label, wall_names.get(f.id, f.direction), station, aff(d.height), d.circuit, d.use)
        for index, (column,value) in enumerate(zip(columns,values)):
            colour = (FIELD if d.provisional else BLUE) if index == 0 else INK
            c.text(column,y,value,8.6,colour,700 if index == 0 else 400)
        y += 11.5
    return y


def plan_background(c, detached, pt, k, *, omit_labels=()):
    cuts = 12000
    for wall in PROJECT['walls'].values():
        s,e = wall['start'],wall['end']
        if (s['x']<cuts) != detached or wall['thickness']<40:
            continue
        along_x = abs(e['x']-s['x'])>abs(e['y']-s['y'])
        axis = 'x' if along_x else 'y'
        fixed = s['y' if along_x else 'x']
        thickness = wall['thickness']
        start,end = s[axis],e[axis]
        def block(a,b,fill,stroke='none',sw=.7):
            if along_x:
                x,y = pt(a,fixed-thickness/2)
                c.rect(x,y,(b-a)*k,thickness*k,fill,stroke,sw)
            else:
                x,y = pt(fixed-thickness/2,a)
                c.rect(x,y,thickness*k,(b-a)*k,fill,stroke,sw)
        block(start,end,INK)
        for group in ('doors','windows'):
            for op in PROJECT[group].values():
                if op['wall'] != wall['id']:
                    continue
                a,b = (start+op['position'] + sign*op['width']/2 for sign in (-1,1))
                block(max(start,a), min(end,b), '#e3eef1' if group=='windows' else 'white')
                if op.get('kind') == 'Hinged':
                    hinge = b if op['hinge_at_end'] else a
                    direction = -1 if op['hinge_at_end'] else 1
                    swing = 1 if op['swing'] == 'Left' else -1
                    def door_point(along, normal):
                        return pt(along, fixed+normal) if along_x else pt(fixed-normal, along)
                    samples = [door_point(hinge + direction*op['width']*cos(i*pi/32),
                                          swing*op['width']*sin(i*pi/32)) for i in range(17)]
                    c.path('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in samples),MUTED,.55)
                    c.line(*door_point(hinge,0),*samples[-1],MUTED,.8)
                if group=='windows' or op.get('kind') in ('SlidingGlass','Pocket'):
                    if along_x:
                        c.line(*pt(a,fixed),*pt(b,fixed),'#718e9c',.7)
                    else:
                        c.line(*pt(fixed,a),*pt(fixed,b),'#718e9c',.7)

    for fixture in PROJECT['fixtures'].values():
        kind = fixture['kind']
        if kind in ('Bed','OverheadCabinet','Countertop'):
            continue
        o = fixture['origin']
        if (o['x']<cuts) != detached:
            continue
        angle = radians(fixture['rotation'])
        def corner(x,y):
            return pt(o['x']+x*cos(angle)-y*sin(angle),o['y']+x*sin(angle)+y*cos(angle))
        w,d = fixture['width'],fixture['depth']
        points = [corner(x,y) for x,y in [(0,0),(w,0),(w,d),(0,d)]]
        c.path('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)+' Z',LINE,.6,'#f3eee6')

    boxes = []
    exclusions = {'Shower','Tub/shower','Porch','Fridge', *omit_labels}
    for name,label in LABELS.items():
        a,b = label['position']['x'],label['position']['y']
        if (a<cuts) != detached or name in exclusions:
            continue
        x,y = pt(a,b)
        if name in {'Laundry','Kitchen','Hallway'}:
            y += 11
        c.text(x,y,name,9.3,INK,700,'middle')
        boxes.append((x,y-3,len(name)*2.7,5))

    return boxes


def power_plan(detached):
    sheet = 'E-02' if detached else 'E-01'
    title = ('Detached wing' if detached else 'Main house') + ' receptacle plan'
    scale = '¼″ = 1′–0″' if detached else '3⁄16″ = 1′–0″'
    c = base(sheet,title,'Proposed floor plan. Match each wall symbol to its tag for the horizontal location, mounting height and circuit.', 'ELECTRICAL PLAN')
    c.text(1187,89,scale+'  |  PRINT AT ACTUAL SIZE',9,MUTED,700,'end')
    k = (18 if detached else 13.5)/304.8
    x0 = 700 if detached else 13600
    y0 = 520 if detached else 1980
    def pt(x,y):
        return (54+(x-x0)*k,145+(y-y0)*k)

    boxes = plan_background(c, detached, pt, k)
    prefix = 'OAUJ' if detached else 'KDLBCPMGVHT'
    selected = sorted((d for d in DEVICES if d.face[0] in prefix), key=lambda d: FACES[d.face].room)
    symbols = {}
    for d in selected:
        f = FACES[d.face]
        xx,yy = symbols[d.tag] = pt(*f.point(d.station,295 if d.tag == 'HD' else 100))
        color = FIELD if d.provisional else BLUE
        c.line(*pt(*f.point(d.station)),xx,yy,color,.8)
        c.circle(xx,yy,3.8,'white',color,1)
        for off in (-1.2,1.2):
            if f.across:
                c.line(xx+off, yy-3, xx+off, yy+3,color,.75)
            else:
                c.line(xx-3, yy+off, xx+3, yy+off,color,.75)

    order = sorted(selected,key=lambda d:(not d.provisional, d.tag))
    for d in order:
        f = FACES[d.face]
        xx,yy = symbols[d.tag]
        color = FIELD if d.provisional else BLUE
        inward = {'S':(0,1),'N':(0,-1),'W':(-1,0),'E':(1,0)}[f.direction]
        ix,iy = inward
        distance = 19 if ix else 12
        for inward_distance, lateral in ((distance,0),(21,9),(21,-9),(21,23),(21,-23),(30,0),(30,18),(30,-18),(42,0)):
            x,y = xx+ix*inward_distance-iy*lateral, yy+iy*inward_distance+ix*lateral
            dx,dy = (14,5.5)
            if not any(abs(x-u)<dx+du+1 and abs(y-v)<dy+dv+1 for u,v,du,dv in boxes):
                break
        boxes.append((x,y,dx,dy))
        c.line(xx+ix*4,yy+iy*4,x,y,color,.5)
        c.rect(x-dx,y-dy,dx*2,dy*2,'white',color,.5)
        c.text(x,y+2.6,d.tag,7,color,700,'middle')

    # The overview uses the same north-down orientation as A-02.
    c.line(79,687,79,710,INK,1)
    c.path('M74,704 L79,712 L84,704',INK,1)
    c.text(79,682,'N',9,INK,700,'middle')
    width = 695
    c.line(width,121,width,717,LINE,.7)
    x = width+20
    c.text(x,139,'Electrical symbols',14,INK,700)
    c.circle(x+8,158,4,'white',BLUE,1)
    for off in (-1.2,1.2):
        c.line(x+8+off,155,x+8+off,161,BLUE,.75)
    c.text(x+24,161,'Proposed duplex receptacle.',10,MUTED)
    c.circle(x+8,178,4,'white',FIELD,1)
    for off in (-1.2,1.2):
        c.line(x+8+off,175,x+8+off,181,FIELD,.75)
    c.text(x+24,181,'Appliance connection or field-dependent rough-in. Verify before installation.',10,MUTED)
    y = device_schedule(c,x,selected)
    if detached:
        y += 14
        c.text(x,y,'Field coordination',14,INK,700)
        y = c.paragraph(x,y+18,'At the ADU bedroom, the garage-side south wall bounds the main room. The bath-side south wall bounds the open area next to the bath.',86,10,13)
        y = c.paragraph(x,y+7,'Verify the existing bath fixture locations and tub clearance at A-G. Confirm each garage bay is served and coordinate the operator receptacle if required.',86,10,13)
    y = c.paragraph(x,y+7,'See E-00 for circuit intent and field coordination.',86,9.4,12)
    assert y < 739, (sheet, y)
    return c


def criteria():
    c = base('E-00','Electrical criteria and branch circuit intent','Read with the proposed electrical floor plans on E-01 and E-02.', 'ELECTRICAL COORDINATION')
    x,y = 35,134
    c.text(x,y,'Electrical layout criteria',16,INK,700)
    sections = [
        ('Code basis', '2025 California Electrical Code (CEC), Title 24 Part 3, with City of Ventura amendments under Municipal Code chapter 12.125. Assumes a new permit application in 2026.'),
        ('General wall space · CEC 210.52(A), (H)', 'Cover qualifying wall space 2 ft or wider so no point measured along the floor line is more than 6 ft from a receptacle. Include wall space below glazing, with doors and similar openings breaking the run. Provide a hall receptacle where length is 10 ft or more.'),
        ('Kitchen and dining · CEC 210.11(C)(1), 210.52(B), (C)', 'Use two 20 A small-appliance branches. Cover wall-counter spaces 12 in or wider within 24 in of a receptacle along the wall line. Counter outlets are 44 in AFF at center, about 7¼ in above the 36¾ in worktop, within the 20 in limit.'),
        ('Baths, laundry and garage · CEC 210.11(C), 210.52(D), (F), (G)', 'Provide a basin receptacle within 3 ft of each basin edge. Keep boxes out of the tub and shower zone under 406.9(C). Provide the designated 20 A bath, laundry, and garage branches. Field-check each garage vehicle bay.'),
        ('Protection · CEC 210.8, 210.12, 406.12', 'Provide GFCI in kitchens, baths, laundry and garage, plus other required locations and appliances. Locate GFCI reset controls where readily accessible. Provide AFCI where required. Use listed tamper-resistant receptacles where required.'),
    ]
    for title,msg in sections:
        y += 22
        c.text(x,y,title,11,INK,700)
        y = c.paragraph(x,y+15,msg,87,9.9,12.5)

    y += 14
    c.text(x,y,'Before submitting to Ventura',14,INK,700)
    y = c.paragraph(x,y+17,'Field-survey existing devices, service rating and panel location. Complete lighting and switch layouts, actual circuiting, panel schedule, load calculations, and one-line diagram to match City checklist BS-007.',87,9.9,12.5)
    y = c.paragraph(x,y+7,'Confirm detached-wing permit classification, ADU supply and any kitchen scope. Check outdoor and service receptacle requirements and lighting or energy-code scope as applicable.',87,9.9,12.5)
    c.text(x,y+13,'Rough-in coordination',10,INK,700)
    y = c.paragraph(x,y+27,'Keep boxes clear of pockets, built-ins and window framing. Verify appliance connection height, accessibility, voltage and cord reach.',87,9.9,12.5)
    y += 13
    c.text(x,y,'Official references',10,INK,700)
    for link, title in [
        ('https://www.cityofventura.ca.gov/DocumentCenter/View/38220/BS-007-Minimum-Plan-Submittal-Requirements_V2','Ventura Building & Safety BS-007'),
        ('https://www.cityofventura.ca.gov/DocumentCenter/View/46991/04','Ventura 2025 code adoption'),
        ('https://www.dgs.ca.gov/BSC/Codes.aspx','California Building Standards Code'),
    ]:
        y += 13
        c.items.append(f'<a xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="{escape(link)}">')
        c.text(x,y,title,9,BLUE,700)
        c.items.append('</a>')
    assert y < 729, y

    x = 610
    c.text(x,134,'Branch circuit intent',16,INK,700)
    c.text(x,151,'Circuit IDs on E-01 and E-02. Verify panel, circuits and loads in the field.',9.4,MUTED)
    y = 174
    for index,(code,use,rating,protect) in enumerate(CIRCUITS):
        if index%2==0:
            c.rect(x,y-10,577,23,PALE)
        c.text(x+5,y,code,9,BLUE,700)
        c.text(x+88,y,use,9.3,INK,700)
        c.text(x+88,y+10,rating,8.5,MUTED)
        c.text(1180,y+3,protect,9,MUTED,400,'end')
        y += 23
    y += 19
    c.text(x,y,'Sheet index',14,INK,700)
    y += 18
    for index,(number,name) in enumerate(INDEX):
        xx = x + (292 if index >= 11 else 0)
        yy = y + (index % 11)*15
        c.text(xx,yy,number,9,BLUE,700)
        c.text(xx+65,yy,name,8.7,INK)
    return c


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('staging', type=Path)
    stage = parser.parse_args().staging
    stage.mkdir(parents=True,exist_ok=True)
    sheets = [('E-00',criteria()),('E-01',power_plan(False)),('E-02',power_plan(True))]
    sheets.extend((number,elevation(number,title,keys)) for number,title,keys in SHEETS)
    for number,page in sheets:
        page.write(stage/f'{number}.svg')
    manifest = {
        'sheets': [
            {'id': number, 'title': title, 'tags': []}
            for number, title, _ in SHEETS
        ],
        'mainTags': [d.tag for d in DEVICES if d.face[0] not in 'OAUJ'],
        'detachedTags': [d.tag for d in DEVICES if d.face[0] in 'OAUJ'],
    }
    (stage/'manifest.json').write_text(json.dumps(manifest))
    print(f'{len(sheets)} sheets, {sum(len(keys) for _, _, keys in SHEETS)} interior views and {len(DEVICES)} tagged electrical points.')


if __name__=='__main__':
    main()
