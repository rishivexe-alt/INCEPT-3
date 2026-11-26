import pcbnew
from pathlib import Path
from pcbnew import FromMM as mm
PRJ = Path(__file__).resolve().parents[1]
ROUTE = PRJ / 'routing'; ROUTE.mkdir(exist_ok=True)
b=pcbnew.LoadBoard(str(PRJ / 'buck555_unrouted.kicad_pcb'))
ns=b.GetDesignSettings().m_NetSettings
nc=pcbnew.NETCLASS('Power'); nc.SetTrackWidth(mm(1.2)); nc.SetClearance(mm(0.25)); nc.SetViaDiameter(mm(1.0)); nc.SetViaDrill(mm(0.5))
ns.m_NetClasses['Power']=nc
for n in ['+15V','VSRC','SW','VOUT']: b.FindNet(n).SetNetClass(nc)
n2=pcbnew.NETCLASS('P12'); n2.SetTrackWidth(mm(0.5)); n2.SetClearance(mm(0.2)); ns.m_NetClasses['P12']=n2
for n in ['+12V','VBUS','VBUS_SW']: b.FindNet(n).SetNetClass(n2)
pcbnew.ExportSpecctraDSN(b, str(ROUTE / 'in.dsn'))

# --- KiCad 7 does not write net->class membership for in-memory classes: patch the DSN text
import re
PW=['+15V','VSRC','SW','VOUT']; P12=['+12V','VBUS','VBUS_SW']
s=(ROUTE / 'in.dsn').read_text()
m=re.search(r'\(class kicad_default "" (.*?)\n\s*\(circuit',s,re.S)
names=m.group(1).split()
rest=[n for n in names if n not in PW+P12]
s=s.replace(m.group(0),'(class kicad_default "" '+' '.join(rest)+'\n      (circuit')
s=s.replace('(class P12\n','(class P12 '+' '.join(P12)+'\n').replace('(class Power\n','(class Power '+' '.join(PW)+'\n')
s=s.replace('(width 200)\n        (clearance 200.1)','(width 250)\n        (clearance 200.1)',1)
(ROUTE / 'in.dsn').write_text(s)
