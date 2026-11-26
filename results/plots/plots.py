from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / 'simulation' / 'ngspice'
sys.path.insert(0, str(SIM))
import gen, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, json, re, os
OUT = str(Path(__file__).resolve().parent) + os.sep
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.25,'figure.dpi':130})
C={'v':'#1f5fa8','i':'#c4571a','g':'#5b5b5b','k':'#2a8a5a'}
def ds(t,y,n=6000):
    k=max(1,len(t)//n); return t[::k],y[::k]
def env(t,y,n=1500):
    # min/max envelope decimation for fast switching signals
    k=max(1,len(t)//n); m=len(t)//k*k
    a=y[:m].reshape(-1,k); tt=t[:m].reshape(-1,k)[:,0]
    return tt,a.min(1),a.max(1)
NAMES={1:'3.3 V mode',2:'5 V mode',3:'12 V mode'}
VT={1:3.3,2:5,3:12}
# A: startup, 3 modes (VOUT, IL)
fig,ax=plt.subplots(2,3,figsize=(11,5),sharex='col')
for m in (1,2,3):
    d=gen.read_raw(str(SIM / f'su{m}.raw')); t=d['time']*1e3
    a,b,c=env(t,d['v(vo)'],900); ax[0,m-1].fill_between(a,b,c,color=C['v'],lw=0.6); ax[0,m-1].axhline(VT[m],color=C['g'],ls='--',lw=.8)
    ax[0,m-1].set_title(f'{NAMES[m]}: startup, 10 Ω'); ax[0,m-1].set_ylabel('VOUT (V)') if m==1 else None
    a,b,c=env(t,d['i(l1)'],900); ax[1,m-1].fill_between(a,b,c,color=C['i'],lw=0.6); ax[1,m-1].set_xlabel('t (ms)'); ax[1,m-1].set_ylabel('IL (A)') if m==1 else None
fig.tight_layout(); fig.savefig(OUT+'A_startup.png'); plt.close()
# B: steady state zoom
fig,ax=plt.subplots(4,3,figsize=(11,8),sharex='col')
for m in (1,2,3):
    d=gen.read_raw(str(SIM / f'su{m}.raw')); t=d['time']; w=(t>0.1)&(t<0.1+160e-6); tt=(t[w]-t[w][0])*1e6
    for r,(k,lab,col) in enumerate([('v(gate)','GATE (V)',C['g']),('v(sw)','SW (V)',C['v']),('v(vo)','VOUT (V)',C['k']),('i(l1)','IL (A)',C['i'])]):
        ax[r,m-1].plot(tt,d[k][w],color=col,lw=1)
        if m==1: ax[r,m-1].set_ylabel(lab)
        if r==3: ax[r,m-1].set_xlabel('t (µs)')
    ax[0,m-1].set_title(NAMES[m]+' (steady state)')
fig.tight_layout(); fig.savefig(OUT+'B_steady.png'); plt.close()
# D: load sweep, E: line sweep (from out_suite2.txt)
txt=(SIM / 'out_suite2.txt').read_text()
ld={m:[] for m in (1,2,3)}; vin={m:[] for m in (1,2,3)}
for l in txt.splitlines():
    mm=re.match(r'ld\|(\d)\|([\d.]+) Vo=([\d.]+) .* eff=([\d.]+)%',l)
    if mm: ld[int(mm[1])].append((float(mm[2]),float(mm[3]),float(mm[4])))
    mm=re.match(r'vin\|(\d)\|([\d.]+) (NOT RUNNING.*Vo=0.000|Vo=([\d.]+).*eff=([\d.]+)%)',l)
    if mm: vin[int(mm[1])].append((float(mm[2]),float(mm[4] or 0)))
# add the 10 ohm and 15 V base points
base={1:(3.3027,62.5),2:(4.9664,72.9),3:(11.944,86.8)}
fig,ax=plt.subplots(1,3,figsize=(11,3.3))
cols=[C['v'],C['i'],C['k']]
for m in (1,2,3):
    p=sorted(ld[m]+[(10.0,base[m][0],base[m][1])]); x=[q[0] for q in p]
    ax[0].plot(x,[q[1]/VT[m] for q in p],'o-',color=cols[m-1],label=NAMES[m]); ax[1].plot(x,[q[2] for q in p],'o-',color=cols[m-1])
    q=sorted(vin[m]+[(15.0,base[m][0])]); ax[2].plot([a[0] for a in q],[a[1]/VT[m] for a in q],'o-',color=cols[m-1])
ax[0].set_xscale('log'); ax[1].set_xscale('log'); ax[0].set_xlabel('load (Ω)'); ax[1].set_xlabel('load (Ω)'); ax[2].set_xlabel('Vin (V)')
ax[0].set_ylabel('VOUT / target'); ax[1].set_ylabel('efficiency (%)'); ax[2].set_ylabel('VOUT / target')
ax[0].legend(frameon=False); ax[0].set_title('Load regulation (open loop)'); ax[1].set_title('Efficiency vs load'); ax[2].set_title('Line sensitivity (UV lockout at 12 V)')
fig.tight_layout(); fig.savefig(OUT+'D_E_load_line.png'); plt.close()
# F: faults
def panel(ax,name,sig,lab,col,tlo,thi,fn=lambda x:x):
    d=gen.read_raw(str(SIM / (name+'.raw'))); t=d['time']*1e3; w=(t>=tlo)&(t<=thi)
    a,b,c=env(t[w],fn(d[sig][w]),1200); ax.fill_between(a,b,c,color=col,lw=.6); ax.set_ylabel(lab)
fig,ax=plt.subplots(4,3,figsize=(11,8.5))
for j,(n,ttl,lo,hi) in enumerate([('short1','Short at 90 ms, 3.3 V mode',85,140),('short3','Short at 90 ms, 12 V mode',85,140),('ovp1','1 A injected into VOUT, 3.3 V mode',85,125)]):
    panel(ax[0,j],n,'v(vo)','VOUT (V)',C['v'],lo,hi); panel(ax[1,j],n,'i(l1)','IL (A)',C['i'],lo,hi); panel(ax[2,j],n,'v(rst)','555 RESET (V)',C['g'],lo,hi)
    panel(ax[3,j],n,'i(vadp)','Iin (A)',C['k'],lo,hi,lambda x:-x); ax[0,j].set_title(ttl); ax[3,j].set_xlabel('t (ms)')
fig.tight_layout(); fig.savefig(OUT+'F1_short_ovp.png'); plt.close()
fig,ax=plt.subplots(3,3,figsize=(11,6.5))
for j,(n,ttl,lo,hi) in enumerate([('sel13','Selector 3.3 V → 12 V (break at 90 ms)',80,200),('sel31','Selector 12 V → 3.3 V',80,200),('drop','Input 15→10 V for 5 ms, 5 V mode',80,170)]):
    panel(ax[0,j],n,'v(vo)','VOUT (V)',C['v'],lo,hi); panel(ax[1,j],n,'i(l1)','IL (A)',C['i'],lo,hi); panel(ax[2,j],n,'v(rst)','555 RESET (V)',C['g'],lo,hi)
    ax[0,j].set_title(ttl); ax[2,j].set_xlabel('t (ms)')
fig.tight_layout(); fig.savefig(OUT+'F2_selector_dropout.png'); plt.close()
fig,ax=plt.subplots(1,2,figsize=(8,3.2))
for j,(n,ttl) in enumerate([('nl1','No load, 3.3 V mode'),('nl3','No load, 12 V mode')]):
    d=gen.read_raw(str(SIM / (n+'.raw'))); t=d['time']*1e3; a,b,c=env(t,d['v(vo)'],900); ax[j].fill_between(a,b,c,color=C['v']); ax[j].set_title(ttl); ax[j].set_xlabel('t (ms)'); ax[j].set_ylabel('VOUT (V)')
fig.tight_layout(); fig.savefig(OUT+'F3_noload.png'); plt.close()
print('ok')
