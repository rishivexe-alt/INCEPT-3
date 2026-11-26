* ====================== models.inc  (ngspice-42 syntax) ======================
* Generic / datasheet-derived models. NONE of these are vendor-supplied SPICE models.
* Source of each parameter set is stated in DESIGN_REPORT.md section "Model provenance".

.model D1N4148 D(IS=2.52n RS=0.568 N=1.752 CJO=4p M=0.4 TT=20n BV=100 IBV=100u)
.model DSS34   D(IS=5u RS=0.04 N=1.05 CJO=300p M=0.5 BV=40 IBV=0.5m)
.model DZ12    D(IS=1f RS=5 N=1 BV=12 IBV=5m)
.model DTVS15  D(IS=1n RS=0.15 N=1.0 BV=16.7 IBV=1m)
.model DLED    D(IS=1f N=2.0 RS=5)

* Standard-library style small-signal BJTs (typical, not vendor-verified)
.model Q2N2222 NPN(IS=14.34f XTI=3 EG=1.11 VAF=74.03 BF=255.9 NE=1.307 ISE=14.34f IKF=0.2847 XTB=1.5 BR=6.092 NC=2 ISC=0 IKR=0 RC=1 CJC=7.306p MJC=0.3416 VJC=0.75 FC=0.5 CJE=22.01p MJE=0.377 VJE=0.75 TR=46.91n TF=411.1p ITF=0.6 VTF=1.7 XTF=3 RB=10)
.model Q2N3906 PNP(IS=1.41f XTI=3 EG=1.11 VAF=18.7 BF=180.7 NE=1.5 ISE=0 IKF=0.08 XTB=1.5 BR=4.977 NC=2 ISC=0 IKR=0 RC=2.5 CJC=9.728p MJC=0.5776 VJC=0.75 FC=0.5 CJE=8.063p MJE=0.3677 VJE=0.75 TR=33.42n TF=179.3p ITF=0.4 VTF=4 XTF=6 RB=10)

* 2N7002-class small NMOS: Rds(on) ~ 2 ohm @ Vgs=10 V, Vth ~ 2.1 V (datasheet-typical, generic)
.model NM2N7002 NMOS(LEVEL=1 VTO=2.1 KP=0.13 LAMBDA=0.02 RD=0.5 RS=0.5 CBD=20p CBS=0 CGSO=20p CGDO=10p IS=1e-14)

* FDS4435A: values from onsemi FDS4435A datasheet read in this session:
*  Rds(on) 15 mohm typ @ Vgs=-10 V; Vth -1.7 V typ; Ciss 2010 pF, Coss 590 pF, Crss 260 pF
.model FDS4435A VDMOS(PCHAN VTO=-1.7 KP=12 LAMBDA=0.01 RD=2m RS=3m RG=3 CGS=1.7n CGDMAX=700p CGDMIN=200p A=0.5 CJO=450p VJ=0.8 M=0.5 IS=1e-10 RB=10m BV=30 TT=30n)

.model SWM SW(VT=0.5 VH=0.1 RON=1 ROFF=1G)
.model SWS SW(VT=0.5 VH=0.1 RON=10m ROFF=1G)
.model SWC SW(VT=0 VH=5m RON=50 ROFF=100Meg)

* ---- behavioural comparator, open-collector output (LM339-class) ----
.subckt CMP inp inm out vcc gnd
S1 out gnd inm inp SWC
.ends CMP

* ---- behavioural CMOS 555 (TLC555-class) ----
* pins: gnd trig out rst ctrl thr dis vcc
.subckt TLC555B gnd trig out rst ctrl thr dis vcc
Rt1 vcc ctrl 5k
Rt2 ctrl nd 5k
Rt3 nd gnd 5k
Bhi hi gnd V = V(thr,gnd) > V(ctrl,gnd) ? 1 : 0
Blo lo gnd V = V(trig,gnd) < V(nd,gnd) ? 1 : 0
Brs rs gnd V = (V(hi,gnd) > 0.5 || V(rst,gnd) < 0.9) ? 1 : 0
Bq  gnd q I = (V(rs,gnd) > 0.5) ? -V(q,gnd)/1k : ((V(lo,gnd) > 0.5) ? (1-V(q,gnd))/1k : ((V(q,gnd) > 0.5) ? (1-V(q,gnd))/1k : -V(q,gnd)/1k))
Cq  q gnd 10p
Bo  o gnd V = V(q,gnd) > 0.5 ? V(vcc,gnd) : 0
Ro  o out 50
Bqb qb gnd V = 1 - V(q,gnd)
Sd  dis gnd qb gnd SDIS
.model SDIS SW(VT=0.5 VH=0.05 RON=10 ROFF=1G)
.ends TLC555B
