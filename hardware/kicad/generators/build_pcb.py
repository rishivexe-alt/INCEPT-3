import sys, json, os, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pcbnew
from pcbnew import FromMM as mm, VECTOR2I
import design as D
PRJ=str(ROOT); FPROOT=os.environ.get('KICAD_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
BW,BH=float(os.environ.get('BW',132)),float(os.environ.get('BH',104))

def loadfp(fpid):
    lib,name=fpid.split(':'); return pcbnew.FootprintLoad(f'{FPROOT}/{lib}.pretty',name)

# custom FDS4435A footprint = JEDEC SOIC-8, pads 1-3 S, 4 G, 5-8 D (datasheet), saved in project lib
def make_fds():
    fp=loadfp('Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
    fp.SetFPID(pcbnew.LIB_ID('buck555','FDS4435A_SOIC-8'))
    fp.SetValue('FDS4435A'); fp.SetReference('M**')
    io=pcbnew.IO_MGR.PluginFind(pcbnew.IO_MGR.KICAD_SEXP)
    io.FootprintSave(PRJ+'/buck555.pretty',fp)
    return fp
fds=make_fds()

board=pcbnew.BOARD()
board.SetCopperLayerCount(2)
nets={}
def net(n):
    if n not in nets:
        ni=pcbnew.NETINFO_ITEM(board,n); board.Add(ni); nets[n]=ni
    return nets[n]

fps={}
for p in D.P:
    if p['fp']=='' : continue
    fp = pcbnew.FootprintLoad(PRJ+'/buck555.pretty','FDS4435A_SOIC-8') if p['ref']=='M1' else loadfp(p['fp'])
    fp.SetFPID(pcbnew.LIB_ID(*(('buck555','FDS4435A_SOIC-8') if p['ref']=='M1' else p['fp'].split(':'))))
    fp.SetReference(p['ref']); fp.SetValue(p['value'])
    board.Add(fp); fps[p['ref']]=fp
    pads={}
    for pad in fp.Pads(): pads.setdefault(pad.GetNumber(),[]).append(pad)
    for pin,nn in p['pins'].items():
        if nn in('NC',): continue
        if pin not in pads: raise SystemExit(f"PIN MISMATCH {p['ref']} pin {pin} not a pad of {p['fp']}: {sorted(pads)}")
        for pad in pads[pin]: pad.SetNet(net(nn))
    p['_pads']=sorted(pads)

def bbox(fp):
    b=fp.GetBoundingBox(False,False); return b.GetWidth()/1e6,b.GetHeight()/1e6
def place(ref,x,y,rot=0):
    fp=fps[ref]; fp.SetOrientationDegrees(rot); fp.SetPosition(VECTOR2I(mm(x),mm(y)))
def pack(refs,x0,y0,wmax,gap=1.6,rot=None):
    x=x0; y=y0; rh=0
    for r in refs:
        w,h=bbox(fps[r])
        if x>x0 and x+w>x0+wmax: x=x0; y+=rh+gap; rh=0
        fp=fps[r]; fp.SetOrientationDegrees((rot or {}).get(r,0))
        b=fp.GetBoundingBox(False,False)
        c=fp.GetPosition(); off=(c.x-b.GetX(),c.y-b.GetY())
        fp.SetPosition(VECTOR2I(int(mm(x)+off[0]),int(mm(y)+off[1])))
        x+=w+gap; rh=max(rh,h)
    return y+rh
layout_json = ROOT / 'layout.json'
L=json.load(open(layout_json)) if layout_json.exists() else None
exec((Path(__file__).resolve().parent / 'layout.py').read_text())

# outline
for (a,b,c,d) in [(0,0,BW,0),(BW,0,BW,BH),(BW,BH,0,BH),(0,BH,0,0)]:
    s=pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(VECTOR2I(mm(a),mm(b))); s.SetEnd(VECTOR2I(mm(c),mm(d))); s.SetWidth(mm(0.1)); board.Add(s)
pcbnew.SaveBoard(PRJ+'/buck555_unrouted.kicad_pcb',board)
print('saved; nets',len(nets))
