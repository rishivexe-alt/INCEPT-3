from pathlib import Path
import sys, json, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen, suite
from multiprocessing import Pool
def job(a):
    kind,mode,val=a
    name=f"{kind}{mode}_{str(val).replace('.','p')}"
    if kind=='ld':   # load sweep
        gen.run(suite.base(mode,tstop=0.09,rload=val),name); r=suite.stats(name,rload=val)
    elif kind=='vin':# input voltage sweep (adapter value), TVS removed for 20 V
        gen.run(suite.base(mode,tstop=0.09,vin_pwl=f"0 0 1m {val}",tvs=(val<16)),name); r=suite.stats(name,Vin_src=val)
    elif kind=='nl': # no load (1 Mohm) -> only preload
        gen.run(suite.base(mode,tstop=0.09,rload=1e6),name); r=suite.stats(name,rload=1e6)
    return a,r
if __name__=="__main__":
    jobs=[('ld',m,v) for m in (1,2,3) for v in (5.0,20.0,50.0,100.0)]
    jobs+=[('vin',m,v) for m in (1,2,3) for v in (12.0,14.25,15.75)]
    with Pool(2) as p: out=p.map(job,jobs)
    R={f"{k}|{m}|{v}":r for (k,m,v),r in out}
    json.dump(R,open("res_sweeps.json","w"),indent=1)
    for k,r in R.items():
        if r.get('running'): print(k, f"Vo={r['vavg']:.3f} Vpp={r['vpp']*1e3:.1f}mV IL {r['ilmin']:.2f}/{r['ilmax']:.2f} f={r['f']/1e3:.1f}k eff={(r['eff'] or 0)*100:.1f}%")
        else: print(k,"NOT RUNNING (inhibited)", f"Vo={r['vavg']:.3f}")
