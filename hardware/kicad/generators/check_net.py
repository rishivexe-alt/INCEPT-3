import sys, xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import design as D
def load(xmlf):
    t=ET.parse(xmlf).getroot(); nets={}
    for n in t.find('nets'):
        nm=n.get('name').lstrip('/')
        for nd in n: nets.setdefault(nm,[]).append((nd.get('ref'),nd.get('pin')))
    return nets
def compare(xmlf):
    nets=load(xmlf); pin2net={}
    for nm,nodes in nets.items():
        for r,p in nodes: pin2net[(r,p)]=nm
    errs=[]; checked=0
    for part in D.P:
        for pin,net in part['pins'].items():
            if net=='NC': continue
            checked+=1
            got=pin2net.get((part['ref'],pin))
            if got is None: errs.append(f"{part['ref']}.{pin}: expected {net}, NOT CONNECTED in KiCad netlist")
            elif got!=net and not got.startswith('Net-('): errs.append(f"{part['ref']}.{pin}: expected {net}, KiCad has {got}")
            elif got.startswith('Net-('): errs.append(f"{part['ref']}.{pin}: expected {net}, KiCad has unnamed {got}")
    # extra pins in netlist not in design (e.g., stacked pins fine)
    design_pins={(p['ref'],pin) for p in D.P for pin,net in p['pins'].items() if net!='NC'}
    extra=[(k,v) for k,v in pin2net.items() if k not in design_pins and not k[0].startswith('#')]
    return checked,errs,extra,nets
if __name__=='__main__':
    c,e,x,nets=compare(sys.argv[1] if len(sys.argv)>1 else str(ROOT / 'buck555.xml'))
    print('pins checked:',c,' mismatches:',len(e)); print('\n'.join(e[:40])); print('extra nodes not in design:',x[:20])
    print('nets:',len(nets))
    single=[n for n,v in nets.items() if len(v)<2]; print('single-node nets:',single)
