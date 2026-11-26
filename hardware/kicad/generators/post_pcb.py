# widen high-current tracks where it is DRC-clean, remove dangling stitching vias; refill; final DRC
import pcbnew, re, math, os
from pathlib import Path
from pcbnew import FromMM as mm, VECTOR2I
os.environ.setdefault('KICAD7_FOOTPRINT_DIR','/usr/share/kicad/footprints')
PRJ=Path(__file__).resolve().parents[1]; F=str(PRJ/'buck555.kicad_pcb'); R=str(PRJ/'buck555_drc.rpt')
WIDEN={'VBUS':1.2,'VBUS_SW':1.2,'+15V':1.2,'VSRC':1.2,'SW':1.2,'VOUT':1.2}
def load(): return pcbnew.LoadBoard(F)
def save(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(F,b)
def drc():
    b=load(); pcbnew.WriteDRCReport(b,R,pcbnew.EDA_UNITS_MILLIMETRES,True); return open(R).read()
b=load(); orig={}
for t in b.GetTracks():
    if t.GetClass()=='PCB_TRACK' and t.GetNetname() in WIDEN and t.GetWidth()<mm(WIDEN[t.GetNetname()]):
        orig[(t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetLayer())]=t.GetWidth()
        t.SetWidth(mm(WIDEN[t.GetNetname()]))
save(b); print('widened',len(orig))
for it in range(6):
    rep=drc(); bad=[]
    for blk in re.split(r'\n(?=\[)',rep):
        m=re.match(r'\[(\w+)\]',blk)
        if not m or m.group(1) in('silk_over_copper','silk_overlap','silk_edge_clearance'): continue
        pts=[(float(x),float(y),what) for x,y,what in re.findall(r'@\(([-\d.]+) mm, ([-\d.]+) mm\): (.*)',blk)]
        bad.append((m.group(1),pts))
    print('iter',it,'issues',len(bad),[x[0] for x in bad][:8])
    if not bad: break
    b=load(); changed=0
    for kind,pts in bad:
        for x,y,what in pts:
            if what.startswith('Via') and kind=='via_dangling':
                for t in list(b.GetTracks()):
                    if t.GetClass()=='PCB_VIA' and abs(t.GetPosition().x-mm(x))<mm(0.05) and abs(t.GetPosition().y-mm(y))<mm(0.05): b.Remove(t); changed+=1
            elif what.startswith('Track'):
                for t in b.GetTracks():
                    if t.GetClass()!='PCB_TRACK': continue
                    k=(t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetLayer())
                    if k in orig and t.GetWidth()!=orig[k]:
                        # the report gives the track's start/centre area; revert if point lies near the segment
                        ax,ay,bx,by=t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y
                        px,py=mm(x),mm(y); dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
                        tt=0 if L==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
                        if math.hypot(px-(ax+tt*dx),py-(ay+tt*dy))<mm(1.0): t.SetWidth(orig[k]); changed+=1
    if changed==0: print('nothing changed; stop'); break
    save(b)
print(open(R).read()[:1500])
