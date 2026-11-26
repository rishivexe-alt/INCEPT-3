from pathlib import Path
import sys, json, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen
from calib import edges
RA=[953,2210,7500]; RB=[9760,8660,3400]
VT=[3.3,5.0,12.0]
def base(mode,**kw):
    mc=[0,0,0]; mc[mode-1]=1
    p=dict(mode_ctl=mc,ra=RA,rb=RB); p.update(kw); return p

def stats(name,tw=6e-3,Vin_src=15.0,rload=10.0):
    d=gen.read_raw(name+".raw"); t=d['time']; te=t[-1]
    m=t>te-tw; tt=t[m]
    vo=d['v(vo)'][m]; il=d['i(l1)'][m]; o=d['v(outp)'][m]; sw=d['v(sw)'][m]
    ia=-d['i(vadp)'][m]; vsrc=d['v(vsrc)'][m]
    r=edges(tt,o,6,True)
    if len(r)<3: return dict(running=False,vavg=float(vo.mean()),vpk=float(vo.max()))
    a,b=r[0],r[-1]; mm=(tt>=a)&(tt<=b); T=(b-a)/(len(r)-1)
    avg=lambda x: np.trapezoid(x[mm],tt[mm])/(b-a)
    vavg=avg(vo); pin=Vin_src*avg(ia)
    pout=avg(vo*vo)/rload
    f=edges(tt,o,6,False); th=np.mean([f[f>x][0]-x for x in r[:-1] if (f>x).any()])
    dfet=avg((sw>7.5).astype(float))
    return dict(running=True,vavg=float(vavg),vpp=float(vo[mm].max()-vo[mm].min()),ilmin=float(il[mm].min()),ilmax=float(il[mm].max()),
        ilavg=float(avg(il)),f=float(1/T),d555=float(th/T),dfet=float(dfet),pin=float(pin),pout=float(pout),eff=float(pout/pin) if pin>0 else None,
        vsrc_min=float(vsrc[mm].min()))

def startup(name,vt):
    d=gen.read_raw(name+".raw"); t=d['time']; vo=d['v(vo)']; il=d['i(l1)']
    fin=vo[t>t[-1]-6e-3].mean()
    # settling: last time |vo-fin|>2% fin (smooth by 200us moving window)
    k=np.where(np.abs(vo-fin)>0.02*fin)[0]; ts=t[k[-1]] if len(k) else 0
    return dict(final=float(fin),vpeak=float(vo.max()),overshoot_pct=float((vo.max()-fin)/fin*100),
                ilpeak=float(il.max()),settle_2pct_ms=float(ts*1e3))

if __name__=="__main__":
    res={'startup':{}, 'steady':{}}
    for mode in (1,2,3):
        gen.run(base(mode,tstop=0.12),f"su{mode}")
        res['startup'][mode]=startup(f"su{mode}",VT[mode-1])
        res['steady'][mode]=stats(f"su{mode}")
        print(mode,res['startup'][mode]); print('  ',res['steady'][mode],flush=True)
    json.dump(res,open("res_startup.json","w"),indent=1)
