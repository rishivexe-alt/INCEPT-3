from pathlib import Path
import sys, json, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen, suite
from calib import edges
R={}
def load(k):
    d=gen.read_raw(k+".raw"); return d,d['time']
def seg(d,t,a,b,k): m=(t>=a)&(t<=b); return d[k][m]
print("== no-load / 20 V")
for k,rl,vin in (('nl1',1e6,15),('nl2',1e6,15),('nl3',1e6,15),('v20_1',10,20),('v20_3',10,20)):
    s=suite.stats(k,rload=rl,Vin_src=vin); R[k]=s
    d,t=load(k); rst=d['v(rst)']; low=(seg(d,t,60e-3,90e-3,'v(rst)')<1).mean()
    print(k, {a:(round(b,3) if isinstance(b,float) else b) for a,b in s.items() if a in('running','vavg','vpp','ilmin','ilmax','f','eff','vsrc_min')}, "frac RESET low (60-90ms):",round(low,3), "peak vo",round(d['v(vo)'].max(),3))
print("== short circuit (applied at 90 ms)")
for k in ('short1','short2','short3'):
    d,t=load(k); m=t>90e-3
    il=d['i(l1)'][m]; rst=d['v(rst)'][m]; tt=t[m]
    low=(rst<1)
    # count hiccup events = falling edges of rst through 1 V
    ev=edges(tt,rst,1.0,False)
    iin=(-d['i(vadp)'][m]); 
    print(k,"IL peak %.2f A"%il.max(),"hiccup events",len(ev),"first events (ms)",np.round((ev[:5]-90e-3)*1e3,2),"mean Iin %.3f A"%iin.mean(),"max Iin %.2f"%iin.max(),"frac time RESET low %.2f"%low.mean(), "pre-short Vo %.2f"%np.interp(89e-3,t,d['v(vo)']))
    R[k]=dict(ilpeak=float(il.max()),events=int(len(ev)),iin_mean=float(iin.mean()))
print("== overload 12 V mode, load stepped 10 -> 2.5 ohm at 90 ms (4.8 A nominal)")
d,t=load('ovl3'); m=t>90e-3
il=d['i(l1)'][m]; rst=d['v(rst)'][m]; tt=t[m]; ev=edges(tt,rst,1.0,False)
print("IL peak %.2f"%il.max(),"events",len(ev),"first ms",np.round((ev[:4]-90e-3)*1e3,2),"Vo min %.2f"%d['v(vo)'][m].min())
# current at the moment of the first event
if len(ev): 
    i0=np.interp(ev[0],t,d['i(l1)']); print("IL at first trip %.2f A"%i0)
print("== OVP injection (1 A into output for 4 ms at 90 ms)")
for k in ('ovp1','ovp2','ovp3'):
    d,t=load(k); m=(t>=89e-3)&(t<=130e-3)
    vo=d['v(vo)'][m]; rst=d['v(rst)'][m]; tt=t[m]; sw=d['v(sw)'][m]
    ev=edges(tt,rst,1.0,False); 
    pre=np.interp(89.9e-3,t,d['v(vo)'])
    print(k,"Vo before %.2f"%pre,"Vo peak %.2f"%vo.max(),"RESET low events at ms",np.round((ev-90e-3)*1e3,2)[:5],"Vo at 120 ms %.2f"%np.interp(120e-3,t,d['v(vo)']))
print("== selector transitions")
for k in ('sel13','sel31'):
    d,t=load(k); 
    for a,b,lab in ((80e-3,90e-3,'before'),(90e-3,110e-3,'break'),(110e-3,125e-3,'after+0-15ms'),(205e-3,220e-3,'settled')):
        vo=seg(d,t,a,b,'v(vo)'); il=seg(d,t,a,b,'i(l1)'); rst=seg(d,t,a,b,'v(rst)')
        print(k,lab,"Vo %.2f..%.2f"%(vo.min(),vo.max()),"IL %.2f..%.2f"%(il.min(),il.max()),"RESET min %.2f max %.2f"%(rst.min(),rst.max()))
    print(k,"Vo peak overall after 90ms: %.2f"%d['v(vo)'][t>90e-3].max(),"IL peak %.2f"%d['i(l1)'][t>90e-3].max())
print("== input dropout 15 V -> 10 V for 5 ms at 90 ms (mode 2)")
d,t=load('drop'); m=t>=89e-3
print("Vo min %.2f"%d['v(vo)'][m].min(),"Vo max after recovery %.2f"%d['v(vo)'][t>95.2e-3].max(),"IL max %.2f"%d['i(l1)'][t>95.2e-3].max())
rst=d['v(rst)']; low=(rst<1)&(t>90e-3); print("RESET low from %.2f to %.2f ms"%(t[low][0]*1e3,t[low][-1]*1e3))
for a in (88,100,110,120,140,159): print(" Vo @%d ms = %.3f"%(a,np.interp(a*1e-3,t,d['v(vo)'])))
json.dump(R,open("res_faults.json","w"),indent=1,default=float)
