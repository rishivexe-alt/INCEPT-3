from pathlib import Path
import sys, json, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen, buck555_sim as b

def edges(t,v,thr,rising=True):
    a=v>thr
    idx=np.where(a[1:]&~a[:-1])[0] if rising else np.where(~a[1:]&a[:-1])[0]
    return t[idx]+(thr-v[idx])/(v[idx+1]-v[idx]+1e-30)*(t[idx+1]-t[idx]) if len(idx) else np.array([])

def measure(name, win=4e-3):
    d=gen.read_raw(name+".raw"); t=d['time']; tend=t[-1]
    m=t>tend-win
    tt=t[m]; vo=d['v(vo)'][m]; o=d['v(outp)'][m]
    r=edges(tt,o,6,True); f=edges(tt,o,6,False)
    # integer number of periods between first and last rising edge
    T=np.mean(np.diff(r)); n=len(r)-1
    a,bb=r[0],r[-1]
    mm=(tt>=a)&(tt<=bb)
    vavg=np.trapezoid(vo[mm],tt[mm])/(bb-a)
    # high times
    th=[]
    for ri in r[:-1]:
        fi=f[f>ri]
        if len(fi): th.append(fi[0]-ri)
    th=np.mean(th)
    return dict(T=T,f=1/T,th=th,tl=T-th,vavg=vavg,duty=th/T,vpp=vo[mm].max()-vo[mm].min())

def calibrate(mode, vt, rload=10.0, iters=7, Tt=40e-6):
    i=mode-1
    I=vt/rload
    D=(vt+0.35+I*0.25)/15.0
    RA,RB=b.solve_RA_RB(D*Tt,(1-D)*Tt,Vcc=12.0)
    hist=[]
    for k in range(iters):
        ra=[1500,2800,8060]; rb=[9530,8250,3090]
        ra[i]=RA; rb[i]=RB
        mc=[0,0,0]; mc[i]=1
        gen.run(dict(tstop=30e-3,mode_ctl=mc,ra=ra,rb=rb,css=1e-9,rload=rload),f"cal{mode}")
        r=measure(f"cal{mode}")
        hist.append((RA,RB,r['vavg'],r['f'],r['duty']))
        print(f"mode{mode} it{k}: RA={RA:.0f} RB={RB:.0f} Vo={r['vavg']:.3f} f={r['f']/1e3:.2f}k D555={r['duty']:.3f} th={r['th']*1e6:.2f}us tl={r['tl']*1e6:.2f}us",flush=True)
        err=vt-r['vavg']
        if abs(err)<0.004*vt and abs(r['T']-Tt)<0.3e-6: break
        Dn=r['duty']+err/15.0*1.0
        th_t=Dn*Tt; tl_t=(1-Dn)*Tt
        RA*=th_t/r['th']; RB*=tl_t/r['tl']
    return RA,RB,hist

if __name__=="__main__":
    out={}
    for mode,vt in ((1,3.3),(2,5.0),(3,12.0)):
        RA,RB,h=calibrate(mode,vt)
        out[mode]=dict(RA=RA,RB=RB)
    json.dump(out,open("calib.json","w"),indent=1); print(out)
