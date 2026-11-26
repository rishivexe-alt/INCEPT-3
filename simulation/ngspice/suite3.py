from pathlib import Path
import sys, json, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen, suite
from calib import edges
from multiprocessing import Pool

def job(key):
    if key=='nl1': p=suite.base(1,tstop=0.09,rload=1e6)
    elif key=='nl2': p=suite.base(2,tstop=0.09,rload=1e6)
    elif key=='nl3': p=suite.base(3,tstop=0.09,rload=1e6)
    elif key=='v20_3': p=suite.base(3,tstop=0.09,vin_pwl="0 0 1m 20",tvs=False)
    elif key=='v20_1': p=suite.base(1,tstop=0.09,vin_pwl="0 0 1m 20",tvs=False)
    elif key.startswith('short'):
        m=int(key[-1]); p=suite.base(m,tstop=0.22,extra="Vsc ctls 0 PWL(0 0 90m 0 90.001m 1)\nSsc vo 0 ctls 0 SWS")
    elif key.startswith('ovl'):   # overload: 12 V mode, load stepped to 2.5 ohm
        p=suite.base(3,tstop=0.16,extra="Vsc ctls 0 PWL(0 0 90m 0 90.001m 1)\nSsc vo 0 ctls 0 SWL\n.model SWL SW(VT=0.5 VH=0.1 RON=2.5 ROFF=1G)")
    elif key.startswith('ovp'):   # external energy injected into the output (mode 1)
        m=int(key[-1]); p=suite.base(m,tstop=0.13,extra="Iinj 0 vo PULSE(0 1.0 90m 10u 10u 4m 1)")
    elif key.startswith('sel'):   # rotary change 1 -> (20 ms break) -> 3 ; and 3 -> 1
        if key=='sel13': mc=["PWL(0 1 90m 1 90.01m 0)","0","PWL(0 0 110m 0 110.01m 1)"]
        else: mc=["PWL(0 0 90m 0 90.01m 0 110m 0 110.01m 1)","0","PWL(0 1 90m 1 90.01m 0)"]
        p=suite.base(1,tstop=0.22,mode_ctl=mc)
    elif key=='raopen':   # charge resistor open (selector contact failure): timer stuck HIGH from power-up
        p=suite.base(1,tstop=0.16,ra=[1e12,2210,7500])
    elif key=='drop':             # input dropout 15->10 V for 5 ms (mode 2)
        p=suite.base(2,tstop=0.16,vin_pwl="0 0 1m 15 90m 15 90.2m 10 95m 10 95.2m 15")
    gen.run(p,key)
    return key
if __name__=="__main__":
    keys=['nl1','nl2','nl3','v20_1','v20_3','short1','short2','short3','ovl3','ovp1','ovp2','ovp3','sel13','sel31','drop','raopen']
    with Pool(2) as pl: pl.map(job,keys)
    print("done")
