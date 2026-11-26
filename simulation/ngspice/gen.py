"""Netlist generator + ngspice runner for the selectable 555 buck (hardware version)."""
import subprocess, struct, os, re, numpy as np, textwrap
from pathlib import Path

DEF = dict(
    vin_pwl="0 0 1m 15",         # adapter ramp
    rsrc=0.10,                   # adapter + cable + fuse resistance
    tvs=True,
    mode_ctl=[1,0,0],            # rotary: which contact is made (list of 3 flags) or PWL strings
    ra=[1500,2800,8060], rb=[9530,8250,3090],
    rtop=[18.2,44.2,147], rlow=30.1,
    rload=10.0, cout=220e-6, esr=0.05, L=1e-3, dcr=0.10,
    css=2.2e-6, rs=0.15, rr=100e3,
    tstop=0.12, rhold=1.5e6, tmax=100e-9, extra="", saves="", ic="", uvtop=100e3, uvbot=22.6e3,
)

def netlist(p):
    p = {**DEF, **p}
    mc = p['mode_ctl']
    ctl = []
    for i in range(3):
        v = mc[i]
        ctl.append(f"Vc{i+1} ctl{i+1} 0 {v}" if not isinstance(v,str) else f"Vc{i+1} ctl{i+1} 0 {v}")
    tvs = "Dtvs 0 vin DTVS15" if p['tvs'] else "* TVS omitted in this run"
    models_file = Path(__file__).resolve().with_name("models.inc")
    return textwrap.dedent(f"""\
    * INCEPT-3 selectable-output 555 buck -- hardware architecture, ngspice-42
    .include "{models_file.as_posix()}"
    * ---------------- input: PD adapter 15 V, cable/fuse resistance, TVS, bulk caps
    Vadp adp 0 PWL({p['vin_pwl']})
    Rsrc adp vraw {p['rsrc']}
    {tvs}
    Cin1 vraw cin1 47u
    Rcin1 cin1 0 0.1
    Cin2 vraw 0 10u
    Rv vraw vin 0.001
    Cin3 vin 0 100n
    * ---------------- 12 V timer rail (behavioural 78L12-class LDO: Vdo=1.7 V, Iq=4 mA)
    Iq vin 0 DC 4m
    Bldo l12 0 V = min(12, max(V(vin)-1.7, 0))
    Rldo l12 vcc12 1
    Cv1 vcc12 0 10u
    Cv2 vcc12 0 100n
    * ---------------- 2.495 V reference (TL431-class shunt, behavioural)
    Rkb vcc12 ref 3.9k
    Btl ref 0 I = (V(ref) > 2.495) ? (V(ref)-2.495)/0.5 : 0
    Cref ref 0 100n
    * ---------------- rotary selector (single pole, non-shorting) -> M1..M3 logic rails
    {chr(10).join(ctl)}
    S1 vcc12 m1 ctl1 0 SWM
    S2 vcc12 m2 ctl2 0 SWM
    S3 vcc12 m3 ctl3 0 SWM
    Rpd1 m1 0 100k
    Rpd2 m2 0 100k
    Rpd3 m3 0 100k
    Dv1 m1 val D1N4148
    Dv2 m2 val D1N4148
    Dv3 m3 val D1N4148
    Rval val 0 100k
    * ---------------- 555 timing network
    * charge: VCC12 -> RA_n -> sw -> X -> D1 -> tc ;  discharge: tc -> D2 -> RB_n -> sw -> X
    RA1 vcc12 a1 {p['ra'][0]}
    RA2 vcc12 a2 {p['ra'][1]}
    RA3 vcc12 a3 {p['ra'][2]}
    MA1 a1 m1 x 0 NM2N7002
    MA2 a2 m2 x 0 NM2N7002
    MA3 a3 m3 x 0 NM2N7002
    D1t x tc D1N4148
    D2t tc y D1N4148
    RB1 y b1 {p['rb'][0]}
    RB2 y b2 {p['rb'][1]}
    RB3 y b3 {p['rb'][2]}
    MB1 b1 m1 x 0 NM2N7002
    MB2 b2 m2 x 0 NM2N7002
    MB3 b3 m3 x 0 NM2N7002
    Ct tc 0 4.7n
    Cctl ctrl 0 10n
    Css ctrl 0 {p['css']}
    Dss ctrl rst D1N4148
    X555 0 tc outp rst ctrl tc x vcc12 TLC555B
    * ---------------- interlock bus (wired-OR, active-low RESET)
    Rr vcc12 rst {p['rr']}
    * UV / power-good: Vin divider vs reference
    Ruv1 vin uvs {p['uvtop']}
    Ruv2 uvs 0 {p['uvbot']}
    Cuv uvs 0 10n
    XUV uvs ref rst vcc12 0 CMP
    * position valid: VAL vs VCC12/2
    Rh1 vcc12 vh 10k
    Rh2 vh 0 10k
    XVAL val vh rst vcc12 0 CMP
    * output-overvoltage + preload: selected string only
    RT1 vout t1 {p['rtop'][0]}
    RT2 vout t2 {p['rtop'][1]}
    RT3 vout t3 {p['rtop'][2]}
    MO1 t1 m1 ovs 0 NM2N7002
    MO2 t2 m2 ovs 0 NM2N7002
    MO3 t3 m3 ovs 0 NM2N7002
    Rlow ovs 0 {p['rlow']}
    Cov ovs 0 100n
    * over-voltage: comparator output ON (low) while OK; when ovs > ref it releases and the pull-up charges HOLD
    XOV ovs ref ovf vcc12 0 CMP
    Rovu vcc12 ovf 2.2k
    Dov ovf hold D1N4148
    * over-current: ratiometric detector. V_a = 0.4856*Vin ; V_b = 0.5*Vsrc ; fault when Vin-Vsrc > ~3% of Vin
    Roc1 vin oca 10.6k
    Roc2 oca 0 10k
    Coca oca 0 1n
    Roc3 vsrc ocb 10k
    Roc4 ocb 0 10k
    Cocb ocb 0 1n
    XOC oca ocb ocf vcc12 0 CMP
    Rocu vcc12 ocf 2.2k
    Doc ocf hold D1N4148
    * hold-off pulse stretcher -> pulls RESET low
    Chold hold 0 22n
    Rhold hold 0 {p['rhold']}
    Mhold rst hold 0 0 NM2N7002
    * run LED
    Rbl rst bl 1Meg
    Qled lc bl 0 Q2N2222
    Dled lk lc DLED
    Rled vcc12 lk 2.7k
    * ---------------- gate driver + PMOS
    R6 outp nb 4.7k
    Qdrv gd nb 0 Q2N2222
    Rg gd gate 470
    R7 vsrc gate 1k
    Dz12 gate vsrc DZ12
    Rsns vin vsrc {p['rs']}
    Cfet vsrc 0 2.2u
    M1 sw gate vsrc FDS4435A
    D3 0 sw DSS34
    L1 sw lx {p['L']}
    Rdcr lx vo {p['dcr']}
    Resr vo ce {p['esr']}
    Cout ce 0 {p['cout']}
    Cob vo 0 100n
    Rload vo 0 {p['rload']}
    * vout alias for sensing strings
    Rvo vo vout 0.001
    {p['extra']}
    {p['ic']}
    .options method=gear reltol=2m abstol=1n vntol=100u gmin=1e-10 itl4=200 maxord=2
    .tran 50n {p['tstop']} 0 {p['tmax']} uic
    .end
    """)

def run(p, name, workdir='.', timeout=1800):
    p = {**DEF, **p}
    nl = netlist(p)
    # ngspice control block
    saves = "outp rst gate sw vo vsrc vcc12 ctrl tc x hold ocf ovf oca ocb ovs val m1 m2 m3 uvs ref"
    nl = nl.replace(".end\n", f".control\nrun\nwrite {name}.raw {saves} l1#branch vadp#branch vin\nquit\n.endc\n.end\n")
    open(f"{workdir}/{name}.cir","w").write(nl)
    r = subprocess.run(["ngspice","-b","-o",f"{workdir}/{name}.log",f"{workdir}/{name}.cir"],capture_output=True,text=True,timeout=timeout,cwd=workdir)
    return r

def read_raw(path):
    with open(path,'rb') as f: data = f.read()
    i = data.index(b"Binary:\n")
    hdr = data[:i].decode('latin1'); body = data[i+8:]
    nv = int(re.search(r"No. Variables:\s*(\d+)",hdr).group(1))
    npnt = int(re.search(r"No. Points:\s*(\d+)",hdr).group(1))
    names = []
    sect = hdr.split("Variables:\n")[1].strip().split("\n")
    for ln in sect[:nv]:
        names.append(ln.split()[1].lower())
    arr = np.frombuffer(body[:npnt*nv*8],dtype='<f8').reshape(npnt,nv)
    return {n:arr[:,k] for k,n in enumerate(names)}
