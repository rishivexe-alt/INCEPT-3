import sys, copy, json, math, os, uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sch_lib as S
import design as D
from kiutils.symbol import SymbolLib, Symbol

OUT=str(ROOT); os.makedirs(OUT,exist_ok=True)
PROJ='buck555'
ROOT=str(uuid.uuid5(uuid.NAMESPACE_DNS,'buck555-root'))
def uid(): return str(uuid.uuid4())
def q(s): return '"'+s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
G=2.54

# ------------------------------------------------------------------ custom FDS4435A symbol (project library)
def make_fds():
    base=S.get_symbol('Device:Q_PMOS_GSD')
    s=copy.deepcopy(base); s.libraryNickname='buck555'; s.entryName='FDS4435A'
    for u in s.units: u.entryName='FDS4435A'
    for p in s.properties:
        if p.key=='Value': p.value='FDS4435A'
        if p.key=='Reference': p.value='M'
        if p.key=='Footprint': p.value='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
        if p.key=='Datasheet': p.value='https://www.onsemi.com/download/data-sheet/pdf/fds4435a-d.pdf'
        if p.key=='ki_description': p.value='P-channel MOSFET SO-8: pins 1,2,3 = S; 4 = G; 5,6,7,8 = D (standard SO-8 P-FET pinout)'
    newpins=[]
    for u in s.units:
        for pn in list(u.pins):
            if pn.name=='G': pn.number='4'
            elif pn.name=='S':
                pn.number='1'
                for n in ('2','3'):
                    c=copy.deepcopy(pn); c.number=n; c.hide=True; newpins.append((u,c))
            elif pn.name=='D':
                pn.number='5'
                for n in ('6','7','8'):
                    c=copy.deepcopy(pn); c.number=n; c.hide=True; newpins.append((u,c))
    for u,c in newpins: u.pins.append(c)
    return s
FDS=make_fds()
def custom_lib_text():
    L=SymbolLib(); s=copy.deepcopy(FDS); s.libraryNickname=None; L.symbols=[s]; L.version='20211014'; L.generator='buck555-gen'
    return L.to_sexpr()
_cache={}
def sym(libid):
    if libid in _cache: return _cache[libid]
    s=FDS if libid=='buck555:FDS4435A' else S.get_symbol(libid)
    _cache[libid]=s; return s

# ------------------------------------------------------------------ geometry helpers
def snap(v): return round(round(v/1.27)*1.27,4)
class Out:
    def __init__(s): s.items=[]; s.libids=set()
    def add(s,t): s.items.append(t)
O=Out()

def wire(a,b):
    O.add(f'(wire (pts (xy {a[0]:.4f} {a[1]:.4f}) (xy {b[0]:.4f} {b[1]:.4f})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
def label(net,pt,d):
    # d = outward direction of the wire the label hangs on (dx,dy) screen coords
    ang={(1,0):0,(-1,0):180,(0,-1):90,(0,1):270}[d]
    just={0:'left bottom',180:'right bottom',90:'left bottom',270:'right bottom'}[ang]
    if ang==270: ang=90; just='right bottom'
    O.add(f'(label {q(net)} (at {pt[0]:.4f} {pt[1]:.4f} {ang}) (effects (font (size 1.27 1.27)) (justify {just})) (uuid "{uid()}"))')
def noconn(pt): O.add(f'(no_connect (at {pt[0]:.4f} {pt[1]:.4f}) (uuid "{uid()}"))')
def junction(pt): O.add(f'(junction (at {pt[0]:.4f} {pt[1]:.4f}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))')
def text(t,pt,size=1.6,bold=False):
    O.add(f'(text {q(t)} (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size {size} {size}){" bold" if bold else ""}) (justify left bottom)) (uuid "{uid()}"))')
def frame(x,y,w,h,title):
    pts=[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
    O.add('(polyline (pts '+' '.join(f'(xy {a:.3f} {b:.3f})' for a,b in pts)+') (stroke (width 0.3) (type dash)) (uuid "%s"))'%uid())
    text(title,(x+2,y+5),2.2,True)

def power_inst(libid,net,pt,outdir):
    ang_map_gnd={(0,1):0,(1,0):90,(0,-1):180,(-1,0):270}
    ang_map_pos={(0,-1):0,(-1,0):90,(0,1):180,(1,0):270}
    ang=(ang_map_gnd if net=='GND' else ang_map_pos)[outdir]
    O.libids.add(libid)
    n=len([1 for t in O.items if t.startswith('(symbol (lib_id "power')])+1
    ref=f'#PWR0{n:03d}'
    O.add(f'(symbol (lib_id {q(libid)}) (at {pt[0]:.4f} {pt[1]:.4f} {ang}) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{uid()}")\n'
          f'  (property "Reference" {q(ref)} (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (property "Value" {q(net)} (at {pt[0]+ (2.0 if outdir[1]==0 else 0):.4f} {pt[1]+(2.5*outdir[1]*-1 if outdir[1]!=0 else 0)+0:.4f} 0) (effects (font (size 1.27 1.27))))\n'
          f'  (property "Footprint" "" (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (property "Datasheet" "" (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (pin "1" (uuid "{uid()}"))\n'
          f'  (instances (project {q(PROJ)} (path "/{ROOT}" (reference {q(ref)}) (unit 1)))))')
def pwr_flag(net,pt):
    """PWR_FLAG at pt, wired 5.08 mm up to a power symbol for the net"""
    O.libids.add('power:PWR_FLAG')
    n=len([1 for t in O.items if 'PWR_FLAG' in t and t.startswith('(symbol')])+1
    ref=f'#FLG0{n:02d}'
    end=(pt[0],pt[1]-5.08) if net!='GND' else (pt[0],pt[1]+5.08)
    O.add(f'(symbol (lib_id "power:PWR_FLAG") (at {pt[0]:.4f} {pt[1]:.4f} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{uid()}")\n'
          f'  (property "Reference" {q(ref)} (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (property "Value" "PWR_FLAG" (at {pt[0]+2:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) (justify left)))\n'
          f'  (property "Footprint" "" (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (property "Datasheet" "~" (at {pt[0]:.4f} {pt[1]:.4f} 0) (effects (font (size 1.27 1.27)) hide))\n'
          f'  (pin "1" (uuid "{uid()}"))\n'
          f'  (instances (project {q(PROJ)} (path "/{ROOT}" (reference {q(ref)}) (unit 1)))))')
    wire(pt,end)
    power_inst(D.POWER_NETS[net],net,end,(0,-1) if net!='GND' else (0,1))

# ------------------------------------------------------------------ item (placed part/unit)
class Item:
    def __init__(s,part,unit=1):
        s.part=part; s.unit=unit; s.sym=sym(part['lib'])
        s.allpins=[p for p in S.pins_of(s.sym) if p['unit'] in (0,unit)]
        # nets for the pins of this unit
        s.pins=[p for p in s.allpins]
        s.rot=0; s.x=s.y=0
        s.bw=s.bh=0
    def net(s,p): return s.part['pins'].get(p['number'],None)
    def pwr_dirs(s,rot):
        """score: power pins want outward dir up (+V) or down (GND)"""
        sc=0
        for p in s.pins:
            n=s.net(p)
            if n in D.POWER_NETS:
                _,o=S.pin_abs(p['x'],p['y'],p['angle'],0,0,rot)
                want=(0,1) if n=='GND' else (0,-1)
                sc+= (2 if o==want else (-2 if o==(0,-want[1]) else 0))
        return sc
    def choose_rot(s):
        best=None
        npins=len([p for p in s.pins if not p['hide']])
        pref=[0,90,270,180] if npins!=2 else [0,180,90,270]
        for r in pref:
            sc=s.pwr_dirs(r)
            # for 2-pin signal-only parts prefer horizontal (90/270)
            if npins==2 and not any(s.net(p) in D.POWER_NETS for p in s.pins):
                if r in (90,270): sc+=1
            if best is None or sc>best[0]: best=(sc,r)
        s.rot=best[1]
    def extent(s):
        # bounding box (relative to origin) of the symbol in screen coords after rotation incl. stubs and label allowance
        xs=[0];ys=[0]
        for p in s.pins:
            if p['hide']: continue
            pt,o=S.pin_abs(p['x'],p['y'],p['angle'],0,0,s.rot)
            net=s.net(p) or ''
            lab=max(len(net),2)*1.35+2
            xs+= [pt[0], pt[0]+o[0]*(G+ (lab if o[0] else 0))]
            ys+= [pt[1], pt[1]+o[1]*(G+ (3.0 if o[1] else 0))]
            if o[1]: xs.append(pt[0]+lab)   # label text runs to the right
        # symbol body (from graphics approx) use pin box +- 2.5
        return min(xs)-4,min(ys)-6,max(xs)+4,max(ys)+7

def emit_item(it):
    part=it.part; X,Y=it.x,it.y
    libid=part['lib']; O.libids.add(libid)
    props=[('Reference',part['ref'],(X+0,Y-0),False),('Value',part['value'],(X,Y),False)]
    if part['fp'] is not None: pass
    x0,y0,x1,y1=it.extent()
    vis=[p for p in it.pins if not p['hide']]
    pts=[S.pin_abs(p['x'],p['y'],p['angle'],0,0,it.rot) for p in vis]
    if len(vis)==2 and abs(pts[0][0][0]-pts[1][0][0])<0.1:      # vertical 2-pin part
        refpos=(X+3.2,Y-1.4); valpos=(X+3.2,Y+1.4)
    elif len(vis)==2:                                             # horizontal 2-pin part
        refpos=(X-3.0,Y-5.4); valpos=(X-3.0,Y-3.4)
    elif len(vis)==3:
        refpos=(X+5.5,Y-1.4); valpos=(X+5.5,Y+1.4)
    else:
        refpos=(X+x0+4,Y+y0+3.0); valpos=(X+x0+4,Y+y0+5.0)
    unit_txt=(f' (unit {it.unit})' )
    flds=[('Reference',part['ref'],refpos,False),('Value',part['value'],valpos,False),
          ('Footprint',part['fp'],(X,Y),True),('Datasheet','',(X,Y),True)]
    if part['mfr']: flds.append(('Manufacturer',part['mfr'],(X,Y),True))
    if part['mpn']: flds.append(('MPN',part['mpn'],(X,Y),True))
    if part['desc']: flds.append(('Description',part['desc'],(X,Y),True))
    s=f'(symbol (lib_id {q(libid)}) (at {X:.4f} {Y:.4f} {it.rot}) (unit {it.unit}) (in_bom {"yes" if part["bom"] else "no"}) (on_board {"no" if part["flags"].get("no_board") else "yes"}) (dnp no) (uuid "{uid()}")\n'
    for k,v,pos,hide in flds:
        s+=f'  (property {q(k)} {q(v)} (at {pos[0]:.4f} {pos[1]:.4f} 0) (effects (font (size 1.27 1.27)){" hide" if hide else ""}{"" if hide else " (justify left)"}))\n'
    for p in it.allpins:
        s+=f'  (pin {q(p["number"])} (uuid "{uid()}"))\n'
    s+=f'  (instances (project {q(PROJ)} (path "/{ROOT}" (reference {q(part["ref"])}) (unit {it.unit}))))'
    s+=')'
    O.add(s)
    # connectivity
    for p in it.pins:
        net=it.net(p)
        if p['hide']: continue
        pt,o=S.pin_abs(p['x'],p['y'],p['angle'],X,Y,it.rot)
        pt=(round(pt[0],4),round(pt[1],4))
        if net is None:
            if p['type']!='no_connect':
                noconn(pt)
            continue
        if net=='NC':
            if p['type']!='no_connect': noconn(pt)
            continue
        end=(pt[0]+o[0]*G, pt[1]+o[1]*G)
        wire(pt,end)
        if net in D.POWER_NETS: power_inst(D.POWER_NETS[net],net,end,o)
        else: label(net,end,o)

# ------------------------------------------------------------------ layout

GROUPS=[
 ('A','USB-C connector + CC resistors',['J1','R1','R2','R37','C22']),
 ('A','PD sink (IP2721 requests 15 V, SEL floating) + pass NMOS',['U1','Q1','C1','C2','D1']),
 ('A','Fuse, input bulk and decoupling (+15V rail)',['F1','C3','C4','C5']),
 ('A','Current-sense resistor R3 (OC detector sees Vin - VSRC) + switch-node caps',['R3','C6','C7']),
 ('B','12 V timer/logic rail (555 limited to 15 V supply)',['U2','C8','C9','C10']),
 ('B','2.495 V reference',['U3','R4','C11']),
 ('C','Comparators: A=undervoltage  B=selector-valid  C=overvoltage  D=overcurrent',['U4']),
 ('C','Undervoltage divider (trip ~13.6 V) and valid-reference',['R16','R17','C15','R18','R19']),
 ('C','RESET bus pull-up (active-low interlock, OR-wired)',['R15']),
 ('D','555 astable',['U5','C12','C13','C14']),
 ('D','Steering diodes: D2 charge, D3 discharge, D4 soft-start reset',['D2','D3','D4']),
 ('D','MODE 1 (3.3 V): RA=953  RB=9.76k',['R5','Q2','R8','Q5','R11','D5']),
 ('D','MODE 2 (5 V): RA=2.21k  RB=8.66k',['R6','Q3','R9','Q6','R12','D6']),
 ('D','MODE 3 (12 V): RA=7.5k  RB=3.4k',['R7','Q4','R10','Q7','R13','D7']),
 ('D','Rotary selector connector and position-valid pull-down',['J3','SW1','R14']),
 ('E','Preload + overvoltage sense strings (select per mode)',['R20','Q8','R21','Q9','R22','Q10','R23','C16']),
 ('E','Overcurrent detector (ratiometric: trips when Vin-Vsrc > 3 % of Vin, ~3 A)',['R26','R27','C17','R28','R29','C18']),
 ('E','Fault hold-off pulse stretcher (~30 ms) -> RESET',['R24','D8','R25','D9','C19','R30','Q11']),
 ('E','Run indicator',['R31','Q12','D12','R32']),
 ('F','Gate driver (NPN pulls PMOS gate low; R35 pulls up; D10 clamps Vgs)',['R33','Q13','R34','R35','D10']),
 ('F','Buck power stage',['M1','D11','L1','C20','C21','J2']),
 ('F','Test points and mounting',['TP1','TP2','TP3','TP4','TP5','TP6','TP7','TP8','TP9','MH1','MH2','MH3','MH4']),
]
def build():
    items=[]
    for part in D.P:
        if part['lib']=='Comparator:LM339':
            for u in (1,2,3,4,5): items.append(Item(part,u))
        else: items.append(Item(part,1))
    for it in items: it.choose_rot()
    byref={}
    for it in items: byref.setdefault(it.part['ref'],[]).append(it)
    used=set(); gl=[]
    for sec,title,refs in GROUPS:
        its=[]
        for r in refs: its+=byref[r]; used.add(r)
        gl.append((sec,title,its))
    assert used==set(byref), set(byref)-used
    WIDTH={'A':250,'B':120,'C':250,'D':330,'E':290,'F':420}
    layout={}; heads={}
    cur={}
    for sec,title,its in gl:
        W=WIDTH[sec]
        st=cur.setdefault(sec,dict(x=8,y=14,rowh=0,maxx=0))
        # new row for each group
        if st['rowh']>0: st['y']+=st['rowh']+6; st['rowh']=0
        st['x']=8
        heads.setdefault(sec,[]).append((title,(st['x'],st['y'])))
        st['y']+=5
        for it in its:
            x0,y0,x1,y1=it.extent(); w=x1-x0; h=y1-y0
            if st['x']+w>W and st['x']>8:
                st['x']=8; st['y']+=st['rowh']+2; st['rowh']=0
            it.x=snap(st['x']-x0); it.y=snap(st['y']-y0)
            st['x']+=w+2; st['rowh']=max(st['rowh'],h); st['maxx']=max(st['maxx'],st['x'])
    for sec,st in cur.items(): layout[sec]=(st['maxx']+6,st['y']+st['rowh']+8)
    rows=[['A','B','C'],['D','E'],['F']]
    ox0,oy=12,24; secpos={}
    for row in rows:
        ox=ox0; rh=0
        for sec in row:
            w,h=layout[sec]; secpos[sec]=(ox,oy,w,h); ox+=w+8; rh=max(rh,h)
        oy+=rh+14
    secs={}
    for sec,title,its in gl:
        x,y,w,h=secpos[sec]
        for it in its: it.x=snap(it.x+x); it.y=snap(it.y+y); secs.setdefault(sec,[]).append(it)
    for sec,hl in heads.items():
        x,y,w,h=secpos[sec]
        for title,(hx,hy) in hl: text(title,(x+hx,y+hy+1),1.5,True)
    return items,secpos,secs

def write():
    items,secpos,secs=build()
    for it in items: emit_item(it)
    for sec,(x,y,w,h) in secpos.items(): frame(x,y,w,h,D.SECTIONS[sec])
    # PWR_FLAGs placed under section A area
    ax,ay,aw,ah=secpos['A']
    pwr_flag('VBUS',(snap(ax+aw-30),snap(ay+ah+12)))
    pwr_flag('+15V',(snap(ax+aw-20),snap(ay+ah+12)))
    pwr_flag('GND',(snap(ax+aw-10),snap(ay+ah+4)))
    # notes
    dx,dy,dw,dh=secpos['D']
    text("ROTARY SWITCH (off-board, J3): 1 pole x 3 positions, NON-SHORTING (break-before-make).\n"
         "J3-1 = COM (+12V)   J3-2 = POS 1 (3.3 V)   J3-3 = POS 2 (5 V)   J3-4 = POS 3 (12 V).\n"
         "Between positions every M1..M3 line is low -> VAL low -> comparator pulls RESET low -> 555 and PMOS OFF.\n"
         "Each position enables ONLY its own RA / RB / preload branch (no parallel combination of networks).",(dx+4,dy+dh+9),1.4)
    fx,fy,fw,fh=secpos['F']
    text("POWER PATH: MOSFET ON : +15V -> R3 -> M1 -> SW -> L1 -> VOUT -> load -> GND.   MOSFET OFF: GND -> D11 -> SW -> L1 -> VOUT -> load (freewheel).\n"
         "OPEN-LOOP converter: Vout ~ D x Vin. Calibrated targets 3.3 / 5 / 12 V at 10 ohm, 15 V in. NOT a regulated output.",(fx+4,fy+fh+9),1.4)
    libsyms=''
    seen=set()
    for lid in sorted(O.libids):
        if lid in seen: continue
        seen.add(lid)
        s=sym(lid) if not lid.startswith('power:') else S.get_symbol(lid)
        txt=s.to_sexpr(indent=2)
        if lid=='buck555:FDS4435A':
            pass
        libsyms+=txt
    maxx=max(x+w for x,y,w,h in secpos.values())+20; maxy=max(y+h for x,y,w,h in secpos.values())+40
    PAPER='A3' if maxx<=410 and maxy<=285 else ('A2' if maxx<=580 and maxy<=405 else 'A1')
    PAPERSTR=f'(paper "User" {round(maxx)} {round(maxy)})'; print(PAPERSTR)
    sch=(f'(kicad_sch (version 20230121) (generator eeschema)\n  (uuid "{ROOT}")\n  {PAPERSTR}\n'
         f'  (title_block (title "Selectable 3.3 V / 5 V / 12 V Buck Converter - 555 PWM, open-loop")\n'
         f'    (date "2026-11-25") (rev "1.0") (company "buck555 project")\n'
         f'    (comment 1 "USB-C PD 15 V in, protected: UV lockout, soft-start, OV/OC hold-off, safe selector")\n'
         f'    (comment 2 "OPEN LOOP - output varies with input, load, temperature")\n'
         f'    (comment 3 "Simulated in ngspice (behavioural 555/comparator/LDO); hardware NOT yet verified"))\n'
         f'  (lib_symbols\n{libsyms}  )\n')
    sch+='\n'.join('  '+t.replace('\n','\n  ') for t in O.items)
    sch+=f'\n  (sheet_instances (path "/" (page "1")))\n)\n'
    open(f'{OUT}/{PROJ}.kicad_sch','w').write(sch)
    open(f'{OUT}/{PROJ}.kicad_sym','w').write(custom_lib_text())
    json.dump({'secpos':secpos}, open(ROOT / 'secpos.json', 'w'))
    return items

if __name__=='__main__':
    items=write(); print('parts placed',len(items))
