#!/usr/bin/env python3
"""
Behavioural time-domain model of the selectable-output 555 buck converter.

Models: NE555 astable (diode-steered), NPN gate driver, PMOS gate dynamics with a
square-law channel, Schottky freewheel diode, inductor (DCR), capacitor (ESR), load.
It is NOT a replacement for LTspice: no Miller/Coss ringing, no inductor saturation,
no temperature. Use it to size parts and to predict what LTspice should show.

Usage:  python3 buck555_sim.py            (full design + verification run)
"""
import math, json, sys

VT = 0.02585

# ---------------------------------------------------------------- parameters
P = dict(
    Vin=15.0,
    C_T=4.7e-9,           # timing capacitor (C0G/NP0)
    L=1e-3, DCR=0.15,     # inductor
    COUT=220e-6, ESR=0.05,
    R6=4.7e3,             # NPN base resistor
    R7=1.0e3,             # gate pull-up (spec starting value was 10k)
    Cg=2.2e-9,            # effective gate capacitance (Qg/Vgs, FDS4435A-ish)
    Ilim_npn=0.15,        # usable NPN pull-down current while discharging gate
    Rce=5.0, Vcesat=0.15,
    Vth=2.0, K=3.0, Vov_max=8.0,   # PMOS square-law: Rds(on) ~ 20 mOhm at Vsg=10 V
    Iq555=0.010,          # NE555 supply current at 15 V
    V555_drop_hi=1.7,     # NE555 OUT high = Vcc - 1.7 V
    td_on=0.15e-6, td_off=0.45e-6,   # 555 out -> NPN delay (storage etc.)
    Rdis=15.0, Vdis=0.1,  # 555 discharge transistor
)

def vd_1n4148(I, Is=2.52e-9, n=1.752, Rs=0.568):
    return n * VT * math.log(I / Is + 1.0) + I * Rs

def i_through(Vsrc, R, guess=None):
    """current through R in series with a 1N4148 from source Vsrc"""
    if Vsrc <= 0.3:
        return 0.0
    I = max((Vsrc - 0.6) / R, 1e-9)
    for _ in range(3):
        I = max((Vsrc - vd_1n4148(I)) / R, 1e-9)
    return I

def vf_schottky(I):            # SS34-ish
    return 0.30 + 0.12 * I


# ---------------------------------------------------------------- 555 only
def timing_555(RA, RB, Vcc=15.0, C=None, cycles=6, dt=20e-9):
    """returns (t_high, t_low) of the 555 OUT in steady state"""
    C = C or P['C_T']
    vc, out, t = 0.0, True, 0.0
    edges = []
    hi, lo = Vcc * 2 / 3, Vcc / 3
    while len(edges) < 2 * cycles + 2:
        if out:
            I = i_through(Vcc - vc, RA)
            vc += I * dt / C
            if vc >= hi:
                out = False; edges.append((t, 'f'))
        else:
            I = i_through(vc - P['Vdis'], RB + P['Rdis'])
            vc -= I * dt / C
            if vc <= lo:
                out = True; edges.append((t, 'r'))
        t += dt
    r = [e[0] for e in edges if e[1] == 'r']
    f = [e[0] for e in edges if e[1] == 'f']
    T = (r[-1] - r[-3]) / 2.0
    th = [f[i] - r[i - 1] for i in range(len(f)) if i >= 1 and f[i] > r[i - 1]]
    th = th[-1] if th else f[-1] - r[-2]
    return th, T - th

def solve_RA_RB(t_high, t_low, Vcc=15.0):
    RA = t_high / (0.76 * P['C_T']); RB = t_low / (0.77 * P['C_T'])
    for _ in range(6):
        th, tl = timing_555(RA, RB, Vcc)
        RA *= t_high / th; RB *= t_low / tl
    return RA, RB


# ---------------------------------------------------------------- full model
def simulate(RA, RB, Rload, t_end, dt=100e-9, t_meas=None, vin_fn=None,
             init=None, p=None, record=0):
    """Time-domain run. vin_fn(t) -> input voltage (default constant). Returns metrics dict
    (+ optional decimated waveforms)."""
    q = dict(P); q.update(p or {})
    L, DCR, C, ESR = q['L'], q['DCR'], q['COUT'], q['ESR']
    R6, R7, Cg = q['R6'], q['R7'], q['Cg']
    Vth, K, Vovm = q['Vth'], q['K'], q['Vov_max']
    CT = q['C_T']
    Vin0 = vin_fn(0) if vin_fn else q['Vin']

    vc, out = 0.0, True
    Vg = Vin0                                  # gate sits at source = off
    IL, Vcap = 0.0, 0.0
    if init:
        IL, Vcap = init
    npn_on, sched_t, sched_state = False, None, None
    t = 0.0
    t_meas = t_end - 4e-3 if t_meas is None else t_meas

    # accumulators
    n = 0; sVo = sVo2 = 0.0; Vmin, Vmax = 1e9, -1e9; ILmin, ILmax = 1e9, -1e9
    sPfet = sPd = sIin = sIL = sDuty555 = sDutyFET = sVsw = 0.0
    last_r = None; periods = []; t_hi_acc = []
    wf = {k: [] for k in ('t', 'vin', 'out', 'vg', 'vsw', 'il', 'vo', 'vc')}
    Vpeak = 0.0; ILpeak_all = 0.0
    thr = {3.0: None, 5.0: None, 10.0: None}
    steps = int(t_end / dt)
    rec_every = max(1, steps // record) if record else 0
    prev_out = out
    t_rise = None

    for k in range(steps):
        Vin = vin_fn(t) if vin_fn else Vin0
        Vcc = Vin
        # ---- 555 ---------------------------------------------------------
        RAt = RA(t) if callable(RA) else RA
        RBt = RB(t) if callable(RB) else RB
        if out:
            I = i_through(Vcc - vc, RAt) if RAt else 0.0
            vc += I * dt / CT
            IRA = I
            if vc >= Vcc * 2 / 3:
                out = False
                sched_t, sched_state = t + q['td_off'], False
        else:
            I = i_through(vc - q['Vdis'], RBt + q['Rdis']) if RBt else 0.0
            vc -= I * dt / CT
            IRA = (Vcc - q['Vdis']) / RAt if (RAt and Vcc > 0.5) else 0.0
            if vc <= Vcc / 3:
                out = True
                sched_t, sched_state = t + q['td_on'], True
                if last_r is not None and t > t_meas:
                    periods.append(t - last_r)
                last_r = t
        # ---- NPN ---------------------------------------------------------
        if sched_t is not None and t >= sched_t:
            npn_on = sched_state; sched_t = None
        Vout555 = max(Vcc - q['V555_drop_hi'], 0.0) if out else 0.1
        Ibase = max(Vout555 - 0.75, 0.0) / R6 if out else 0.0
        if Vin < 3.0:
            npn_on = False
        # ---- gate node ---------------------------------------------------
        if npn_on:
            G = 1.0 / R7 + 1.0 / q['Rce']
            Vnew = (Vg + dt / Cg * (Vin / R7 + q['Vcesat'] / q['Rce'])) / (1 + dt / Cg * G)
            Inpn = (Vnew - q['Vcesat']) / q['Rce']
            if Inpn > q['Ilim_npn']:
                Vnew = Vg + dt / Cg * ((Vin - Vg) / R7 - q['Ilim_npn'])
            Vg = max(Vnew, q['Vcesat'])
        else:
            Vg = Vin + (Vg - Vin) * math.exp(-dt / (R7 * Cg))
        Ipull = (Vin - Vg) / R7
        # ---- PMOS + diode -> SW node ------------------------------------
        Vsg = Vin - Vg
        Vov = min(max(Vsg - Vth, 0.0), Vovm)
        Ifet = Id = 0.0; Vf = 0.0
        if IL > 0 or Vov > 0.3:
            Iuse = max(IL, 0.0)
            Isat = K * Vov * Vov
            if Vov > 0 and Iuse <= Isat:
                Vsd = Vov - math.sqrt(max(Vov * Vov - Iuse / K, 0.0))
                if IL < 0:
                    Vsd = IL / (2 * K * Vov)
                Vsw = Vin - Vsd; Ifet = IL
            else:
                Ifet = Isat; Id = Iuse - Isat
                Vf = vf_schottky(Id); Vsw = -Vf
        else:
            Vsw = Vcap  # DCM: node floats at Vout
        Vout = (Vcap + ESR * IL) / (1 + ESR / Rload)
        # ---- inductor / capacitor ---------------------------------------
        IL += dt / L * (Vsw - Vout - IL * DCR)
        if IL < 0 and Vov <= 0.3:
            IL = 0.0
        Vcap += dt / C * (IL - Vout / Rload)
        t += dt
        # ---- bookkeeping -------------------------------------------------
        if Vout > Vpeak: Vpeak = Vout
        if IL > ILpeak_all: ILpeak_all = IL
        for th_ in thr:
            if thr[th_] is None and IL > th_: thr[th_] = t
        if t > t_meas:
            n += 1
            sVo += Vout; sVo2 += Vout * Vout
            Vmin = min(Vmin, Vout); Vmax = max(Vmax, Vout)
            ILmin = min(ILmin, IL); ILmax = max(ILmax, IL)
            Vsd_ = max(Vin - Vsw, 0.0)
            sPfet += Vsd_ * max(Ifet, 0.0) + (IL ** 2 * 0 if False else 0)
            sPd += Vf * Id
            Iin = max(Ifet, 0.0) + Ipull + Ibase + q['Iq555'] + IRA
            sIin += Iin * Vin
            sIL += IL
            sDuty555 += 1.0 if out else 0.0
            sDutyFET += 1.0 if Vsw > Vin / 2 else 0.0
            sVsw += Vsw
        if rec_every and k % rec_every == 0:
            for key, val in zip(wf.keys(), (t, Vin, Vout555 if out else 0.1, Vg, Vsw, IL, Vout, vc)):
                wf[key].append(val)

    res = dict(Vpeak=Vpeak, ILpeak_all=ILpeak_all, t_IL=thr)
    if n:
        Vavg = sVo / n
        res.update(
            Vout=Vavg, Vpp=Vmax - Vmin, Vrms_ac=math.sqrt(max(sVo2 / n - Vavg ** 2, 0)),
            IL_avg=sIL / n, IL_min=ILmin, IL_max=ILmax,
            duty555=sDuty555 / n, dutyFET=sDutyFET / n,
            f=(1.0 / (sum(periods) / len(periods))) if periods else float('nan'),
            Pfet=sPfet / n, Pdiode=sPd / n, Pin=sIin / n,
            Pout=(Vavg ** 2) / Rload, Rds_loss_note=None)
        res['eff'] = res['Pout'] / res['Pin'] if res['Pin'] > 0 else float('nan')
    if record:
        res['wf'] = wf
    return res


# ---------------------------------------------------------------- design flow
MODES = {'3.3 V': 3.3, '5 V': 5.0, '12 V': 12.0}
T_TARGET = 40e-6   # 25 kHz

def e96(x):
    E = [1.00,1.02,1.05,1.07,1.10,1.13,1.15,1.18,1.21,1.24,1.27,1.30,1.33,1.37,1.40,1.43,
         1.47,1.50,1.54,1.58,1.62,1.65,1.69,1.74,1.78,1.82,1.87,1.91,1.96,2.00,2.05,2.10,
         2.15,2.21,2.26,2.32,2.37,2.43,2.49,2.55,2.61,2.67,2.74,2.80,2.87,2.94,3.01,3.09,
         3.16,3.24,3.32,3.40,3.48,3.57,3.65,3.74,3.83,3.92,4.02,4.12,4.22,4.32,4.42,4.53,
         4.64,4.75,4.87,4.99,5.11,5.23,5.36,5.49,5.62,5.76,5.90,6.04,6.19,6.34,6.49,6.65,
         6.81,6.98,7.15,7.32,7.50,7.68,7.87,8.06,8.25,8.45,8.66,8.87,9.09,9.31,9.53,9.76]
    dec = 10 ** math.floor(math.log10(x))
    m = x / dec
    best = min(E + [10.0], key=lambda e: abs(math.log(e / m)))
    return best * dec

def calibrate(vt, Rload=10.0):
    I = vt / Rload
    D = (vt + 0.40 + I * 0.1) / 15.4            # first guess from loss estimate
    for it in range(5):
        RA, RB = solve_RA_RB(D * T_TARGET, (1 - D) * T_TARGET)
        r = simulate(RA, RB, Rload, 16e-3, init=(I, vt))
        err = vt - r['Vout']
        if abs(err) < 0.01 * vt / 3.3:
            break
        D += err / 15.0 * 1.05
    return RA, RB, D, r

if __name__ == '__main__':
    out = {}
    for name, vt in MODES.items():
        RA, RB, D, r = calibrate(vt)
        RAs, RBs = e96(RA), e96(RB)
        rs = simulate(RAs, RBs, 10.0, 16e-3, init=(vt / 10, vt))
        out[name] = dict(RA_exact=RA, RB_exact=RB, RA=RAs, RB=RBs, D=D, run=rs)
        print(f"{name}: RA={RA:.0f} RB={RB:.0f} -> E96 {RAs:.0f}/{RBs:.0f}  "
              f"Vout={rs['Vout']:.3f} f={rs['f']/1e3:.2f}kHz D555={rs['duty555']:.3f} "
              f"Vpp={rs['Vpp']*1e3:.1f}mV ILpk={rs['IL_max']:.3f} eff={rs['eff']*100:.1f}%")
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != 'run'} | {'run': {a: b for a, b in v['run'].items() if a != 'wf'}}
               for k, v in out.items()}, open('${PROJECT_ROOT}/design_results.json', 'w'), indent=1)
