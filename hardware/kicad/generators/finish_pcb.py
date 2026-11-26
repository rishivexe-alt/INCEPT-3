import pcbnew, sys
from pathlib import Path
from pcbnew import FromMM as mm, VECTOR2I
PRJ=Path(__file__).resolve().parents[1]
ROUTE=PRJ/'routing'
BW,BH=132,92
b=pcbnew.LoadBoard(str(PRJ/'buck555_unrouted.kicad_pcb'))
import re
ses=(ROUTE/'out.ses').read_text()
ses=ses[ses.index('(network_out'):]
LY={'F.Cu':pcbnew.F_Cu,'B.Cu':pcbnew.B_Cu}
def P(x,y): return VECTOR2I(int(round(x*100)),int(round(-y*100)))  # ses unit = 0.1 um -> nm = *100
nw=nv=0
for m in re.finditer(r'\(net (\S+)\s(.*?)(?=\n      \(net |\Z)',ses,re.S):
    name=m.group(1).strip('"'); body=m.group(2); ni=b.FindNet(name)
    if ni is None: raise SystemExit('unknown net '+name)
    for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+?)\)',body):
        pts=list(map(int,w.group(3).split())); xy=[(pts[i],pts[i+1]) for i in range(0,len(pts),2)]
        for (x0,y0),(x1,y1) in zip(xy,xy[1:]):
            t=pcbnew.PCB_TRACK(b); t.SetStart(P(x0,y0)); t.SetEnd(P(x1,y1)); t.SetWidth(int(w.group(2))*100)
            t.SetLayer(LY[w.group(1)]); t.SetNet(ni); b.Add(t); nw+=1
    for v in re.finditer(r'\(via "?Via\[0-1\]_(\d+):(\d+)_um"? (-?\d+) (-?\d+)',body):
        t=pcbnew.PCB_VIA(b); t.SetPosition(P(int(v.group(3)),int(v.group(4)))); t.SetWidth(int(v.group(1))*1000); t.SetDrill(int(v.group(2))*1000)
        t.SetViaType(pcbnew.VIATYPE_THROUGH); t.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); t.SetNet(ni); b.Add(t); nv+=1
print('imported wires',nw,'vias',nv)
# GND zones, both layers
gnd=b.FindNet('GND')
for layer in (pcbnew.F_Cu,pcbnew.B_Cu):
    z=pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(gnd)
    z.SetLocalClearance(mm(0.3)); z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if layer==pcbnew.F_Cu else pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(mm(0.3)); z.SetThermalReliefSpokeWidth(mm(0.4))
    o=z.Outline(); o.NewOutline()
    for x,y in [(0.8,0.8),(BW-0.8,0.8),(BW-0.8,BH-0.8),(0.8,BH-0.8)]: o.Append(mm(x),mm(y))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); z.SetIsFilled(False); b.Add(z)
# silkscreen annotation
def txt(s,x,y,size=1.2,layer=pcbnew.F_SilkS):
    t=pcbnew.PCB_TEXT(b); t.SetText(s); t.SetPosition(VECTOR2I(mm(x),mm(y))); t.SetLayer(layer)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT); t.SetTextSize(pcbnew.VECTOR2I(mm(size),mm(size))); t.SetTextThickness(mm(0.18)); b.Add(t)
txt('555 BUCK 3V3/5V/12V (OPEN LOOP) rev A',50,BH-2.4,1.2)
txt('VIN 15V PD',9,29,1.0); txt('VOUT',118,70,1.0)
txt('TP1 PWM  TP2 GATE  TP3 SW  TP4 VOUT  TP5 GND  TP6 12V  TP7 RST  TP8 15V  TP9 HOLD',6,BH-4.5,0.8)
# GND stitching vias on a 8 mm grid where clear of everything else
import math
def segd(p,a,bb):
    ax,ay,bx,by=a.x,a.y,bb.x,bb.y; px,py=p
    dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    t=0 if L==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
tr=[t for t in b.GetTracks()]
pads=[p for f in b.GetFootprints() for p in f.Pads()]
ns=0
for gx in range(6,int(BW)-4,8):
    for gy in range(6,int(BH)-4,8):
        p=(mm(gx),mm(gy)); ok=True
        for pd in pads:
            bb=pd.GetBoundingBox(); cx,cy=bb.GetCenter().x,bb.GetCenter().y
            if abs(p[0]-cx)<bb.GetWidth()/2+mm(0.9) and abs(p[1]-cy)<bb.GetHeight()/2+mm(0.9): ok=False;break
        if not ok: continue
        for t in tr:
            if t.GetClass()=='PCB_VIA':
                if math.hypot(t.GetPosition().x-p[0],t.GetPosition().y-p[1])<mm(1.6): ok=False;break
            else:
                if segd(p,t.GetStart(),t.GetEnd())<t.GetWidth()/2+mm(0.8): ok=False;break
        if not ok: continue
        v=pcbnew.PCB_VIA(b); v.SetPosition(VECTOR2I(*p)); v.SetWidth(mm(0.8)); v.SetDrill(mm(0.4)); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(gnd); b.Add(v); tr.append(v); ns+=1
print('stitching vias',ns)
fill=pcbnew.ZONE_FILLER(b); fill.Fill(b.Zones())
pcbnew.SaveBoard(str(PRJ/'buck555.kicad_pcb'),b)
b.BuildConnectivity()
print('tracks',len([t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK']),'vias',len([t for t in b.GetTracks() if t.GetClass()=='PCB_VIA']))
print('unrouted/ratsnest items:',b.GetConnectivity().GetUnconnectedCount(False))
b2=pcbnew.LoadBoard(PRJ+'/buck555.kicad_pcb')
pcbnew.WriteDRCReport(b2,str(PRJ/'buck555_drc.rpt'),pcbnew.EDA_UNITS_MILLIMETRES,True)
