# INCEPT-3 — Selectable 3.3 V / 5 V / 12 V Buck Converter

**This converter is OPEN LOOP.** Output = duty × input. The 3.3 / 5 / 12 V figures are *calibrated targets at 15 V in and a 10 Ω load*, not guaranteed outputs. Nothing here is a regulated, closed-loop converter.

## 1. Architecture (one line each)
USB-C J1 → IP2721 PD sink (SEL floating → requests 15 V) + AO3400A pass switch → SMAJ15A TVS → 3 A polyfuse F1 → +15V (47 µF + 10 µF + 100 nF) → R3 0.15 Ω sense → VSRC (2.2 µF + 100 nF at the switch) → FDS4435A high-side PMOS → SW → 1 mH L1 → VOUT (220 µF + 100 nF) with SS34 freewheel diode D11 from SW to GND.
L78L12 makes a +12 V rail for the TLC555 (CMOS 555, 2–15 V) and the four LM339 comparators; TL431 gives 2.495 V.
Diode-steered 555: VCC(+12 V)→RA→X→D2→C ; C→D3→RB→X ; DISCH(7) on X ; pins 2 and 6 tied to C (TC) ; C = 4.7 nF C0G.
Gate drive: 555 OUT → R33 4.7 k → Q13 (NPN) → R34 470 Ω → gate; R35 1 k pull-up to VSRC; D10 12 V zener gate→source clamp (VGS stays ≤ 12 V; abs. max ±20 V).

### Current paths
* **ON (OUT high → Q13 on → gate pulled low → PMOS on):** +15V → R3 → VSRC → M1 (S→D) → SW → L1 → VOUT → load/Cout → GND.
* **OFF (gate pulled up by R35, M1 off):** GND → D11 (anode→cathode) → SW → L1 → VOUT → load/Cout → GND (freewheel).

## 2. Problems found in the original design and the fix that was implemented
| Original problem | Implemented measure | Simulated result |
|---|---|---|
| Start-up overshoot 5.1 / 7.8 / 18.9 V, 5.5 A | Soft start: CTRL-pin cap C14 2.2 µF, discharged through D4 when RESET is low | overshoot 0.12 % / 0.07 % / 0.03 %, IL peak 0.45 / 0.63 / 1.87 A |
| Short circuit > 10 A | Ratiometric overcurrent comparator (R3 0.15 Ω; trip ≈ 3 A input) → 30 ms hold-off → RESET low (hiccup) | IL peak 4.28 / 4.04 / 3.75 A in 3.3/5/12 V mode, input current peaks 3.1–3.3 A, ~10 retries in 100 ms, mean input current 57–119 mA |
| Light-load voltage rise | Permanent preload ≈ 65–70 mA from the OV sense string (keeps CCM) | No load: 3.53 / 5.27 / 12.64 V (+7 / +5.4 / +5.3 %). **Still not regulated** |
| No OVP | OV comparator (VOUT/OVS divider vs 2.495 V) → RESET low | see §7: trips in 3.3 and 5 V modes; **does not trip at 13.8 V in 12 V mode** |
| Unsafe rotary transition | Non-shorting selector: each position enables only its own RA/RB/preload branch via 2N7002; no position ⇒ VAL low ⇒ RESET low ⇒ 555/PMOS off | 3.3→12 V and 12→3.3 V: no overshoot beyond target, IL peak 2.04 A |
| PD fallback to 5/9 V | UV comparator (≈13.6 V) holds RESET low | Vin = 12 V: converter inhibited |
| Input spikes | SMAJ15A TVS, polyfuse, 47 µF + 10 µF + 100 nF | not stress-tested (TVS is a simple diode model) |

## 3. Pin-to-pin table (from the schematic netlist)
| Part | Pin → net |
|---|---|
| U5 TLC555CDR | 1 GND · 2 TC · 3 OUT555 · 4 RST · 5 CTRL · 6 TC · 7 X · 8 +12V |
| U1 IP2721 (TSSOP-16) | 1 VBUSG · 2 VBUS · 5 GND · 12 CC2 · 13 CC1 · 16 VBUS_SW · 11 SEL (NC/floating) · 3,4,6–10,14,15 NC |
| U2 L78L12ACD (SO-8) | 8 +15V · 1 +12V · 2,3,6,7 GND · 4,5 NC |
| U3 TL431 (SO-8) | 1, 8 VREF (K tied to REF) · 2,3,6,7 GND |
| U4 LM339 (SO-14) | 3 +12V · 12 GND · A: 5 UVS, 4 VREF, 2 RST · B: 7 VAL, 6 VH, 1 RST · C: 11 OVS, 10 VREF, 13 OVF · D: 9 OCA, 8 OCB, 14 OCF |
| M1 FDS4435A (SO-8) | 1,2,3 VSRC (S) · 4 GATE (G) · 5,6,7,8 SW (D) |
| Q13 MMBT2222A | 1 NB (B) · 2 GND (E) · 3 GD (C) — (KiCad SOT-23 numbering: 1 B, 2 E, 3 C) |
| Q1 AO3400A | 1 VBUSG (G) · 2 VBUS_SW (S) · 3 VBUS (D) |
| D11 SS34 | 1 SW (K) · 2 GND (A) |
| L1 | 1 SW · 2 VOUT |
| J1 USB-C | A9/B9 VBUS · A12/B12 GND · A5 CC1 · B5 CC2 · S1 shield |
| J2 | 1 VOUT · 2 GND |
| J3 rotary header | 1 +12V (common) · 2 M1 (3.3 V) · 3 M2 (5 V) · 4 M3 (12 V) |

Full per-pin list: `kicad/buck555.net` / `.xml`; pin-level SPICE table: `multisim/buck555_netlist_table.csv`.

## 4. Rotary switch contact diagram
```
 off-board rotary, 1 pole x 3 positions, NON-SHORTING (break-before-make)

   J3-1 (+12V) ── COM ──╮
                         ╲ wiper
        pos 1 ── J3-2 (M1) ─┐   M1 gates 2N7002 Q2,Q5,Q8  -> RA 953 / RB 9.76k / preload 18.2 Ω   (3.3 V)
        pos 2 ── J3-3 (M2) ─┤   M2 gates Q3,Q6,Q9         -> RA 2.21k / RB 8.66k / 44.2 Ω          (5 V)
        pos 3 ── J3-4 (M3) ─┘   M3 gates Q4,Q7,Q10        -> RA 7.5k / RB 3.4k / 147 Ω             (12 V)
   M1..M3 each have a 100 k pull-down; D5–D7 OR them into VAL (R14 100 k pull-down).
   Between positions: M1=M2=M3=0 -> VAL low -> LM339-B pulls RESET low -> 555 and PMOS off.
```
Because the rotary is not wired into the timing node itself, the timing node is never floating and two RA/RB networks can never be in parallel unless two M lines are high at once (only possible with a shorting switch — use a non-shorting one).

## 5. Calculations (analytical unless stated)
* Ideal duty D = Vout/Vin = 22 % / 33.3 % / 80 %.
* **Frequency**: T ≈ 0.693·C·(RA + RB) ≈ 0.693 × 4.7 nF × (10.7 k / 10.9 k / 10.9 k) = 34.9 / 35.5 / 35.5 µs *before* diode-drop and threshold effects; **simulated f = 25.3 / 25.0 / 25.1 kHz** (RA/RB were calibrated in the simulation, not from this formula).
* 555 high time (OUT high = PMOS on): simulated 8.9 % / 20.5 % / 68.7 %; the PMOS conduction measured at the SW node is 24 % / 35 % / 83 % because the 1 kΩ gate pull-up and gate charge stretch turn-off. **The timing values are calibrated to this particular (generic) FET model and will need re-trim on the real board.**
* Inductor ripple ΔI = (Vin − Vo)·D·T/L: 0.103 / 0.133 / 0.096 A (simulated 0.107 / 0.135 / 0.083 A).
* Output ripple ≈ ΔI·ESR + ΔI/(8·f·C): ≈ 5.4 + 2.4 mV for the 3.3 V mode; simulated 5.6 / 7.0 / 4.2 mV p-p. **Depends on the assumed 50 mΩ ESR – real capacitor ESR must be checked.**
* **Inductor**: 1 mH, DCR ≤ 0.12 Ω. Isat chosen from fault analysis: highest simulated inductor peak = 4.28 A (short), start-up peak 1.87 A. Required **Isat ≥ 4.5 A** (at −30 % L) and Irms ≥ 2 A. *No manufacturer part number was selected* (footprint: radial Ø21 mm, 19 mm pitch placeholder).
* Switch conduction loss (assumed RDS(on) ≈ 25 mΩ): 12 V mode 1.26² × 0.025 × 0.83 ≈ 33 mW. Diode loss (assumed Vf ≈ 0.45 V): 12 V mode ≈ 1.26 × 0.45 × 0.17 ≈ 96 mW; 3.3 V mode ≈ 0.4 × 0.45 × 0.76 ≈ 137 mW. **Assumed values – not datasheet-verified.** With SO-8 ≈ 50–60 °C/W the FET self-heating is small; the Schottky and R20–R23 are the warm parts.
* Preload strings dissipate: 12 V mode 12.6 V / (147 + 30.1 Ω) = 71 mA → R22 ≈ 0.74 W (**at 74 % of a 1 W rating – derate or use 2 W parts**). 
* Copper (IPC-2221, 1 oz outer, 20 K rise): 1.2 mm ≈ 3.8 A; 0.5 mm ≈ 2.0 A; 0.25 mm ≈ 0.9 A.

## 6. Simulated steady-state results (ngspice, Vin 15 V from a 0.1 Ω source, 10 Ω load) — SIMULATED
| | 3.3 V | 5 V | 12 V |
|---|---|---|---|
| Vout average | 3.303 V | 4.966 V | 11.944 V |
| Ripple p-p | 5.6 mV | 7.0 mV | 4.2 mV |
| IL min / max | 0.341 / 0.448 A | 0.493 / 0.628 A | 1.218 / 1.301 A |
| Frequency | 25.3 kHz | 25.0 kHz | 25.1 kHz |
| Pin / Pout | 1.75 / 1.09 W | 3.38 / 2.47 W | 16.4 / 14.3 W |
| Efficiency | 62.5 % | 72.9 % | 86.8 % |
| Start-up overshoot / 2 % settling | 0.12 % / 28 ms | 0.07 % / 30 ms | 0.03 % / 22 ms |

Efficiency includes everything fed from the 15 V rail (555, LDO, comparators, LED, ≈ 70 mA preload string). The overhead contributors were not separately measured. Efficiency at 3.3 V is poor mainly because the output power is only 1.1 W.

**Load (15 V in) — SIMULATED**
| Load | 3.3 V mode | 5 V mode | 12 V mode |
|---|---|---|---|
| 5 Ω | 3.164 V | 4.775 V | 11.464 V |
| 10 Ω | 3.303 | 4.966 | 11.944 |
| 20 Ω | 3.382 | 5.088 | 12.222 |
| 50 Ω | 3.463 | 5.178 | 12.432 |
| 100 Ω | 3.491 | 5.214 | 12.517 |
| none | 3.526 | 5.271 | 12.636 |

**Line (10 Ω) — SIMULATED**: Vin 12 V → inhibited (UV lockout); 14.25 V → 3.06 / 4.65 / 11.29 V; 15 V → 3.30 / 4.97 / 11.94 V; 15.75 V → 3.53 / 5.29 / 12.60 V. Sensitivity ≈ proportional to Vin (≈ ±7 % for ±5 % Vin).
**20 V input (outside design, not a PD profile used here)**: converter inhibited in the 3.3 V and 12 V modes after a brief start (12 V mode peaks at 14.9 V before being inhibited) — *unintended behaviour, not a designed protection*.

## 7. Fault simulations — SIMULATED
| Case | Result |
|---|---|
| Short at 90 ms | Hiccup: first trip within ≈ 0.2–1.5 ms; IL peak 4.28 / 4.04 / 3.75 A; Iin peak 3.1–3.3 A; RESET held low 68 % / 80 % / 95 % of the time in 3.3 / 5 / 12 V mode |
| 12 V mode, load stepped 10 → 2.5 Ω (≈ 4.8 A demand) | Trips at 3.08 A input; hiccup, output collapses (IL peak 3.39 A). Maximum continuous 12 V load is therefore below ≈ 1.9 A (≈ 6 Ω at 12 V) |
| 1 A injected into VOUT for 4 ms | 3.3 V mode: VOUT peaks **7.83 V** before the OV latch acts; 5 V mode: peaks **8.46 V**; 12 V mode: peaks 13.80 V and **does not trip**. The OV circuit stops *switching*; it cannot absorb energy pushed into the output (no crowbar) |
| Selector 3.3→12 V and 12→3.3 V | RESET asserted during break; VOUT follows monotonically; IL peak 2.04 A / 1.27 A; no overshoot |
| Input dropout 15→10 V for 5 ms (5 V mode) | UV pulls RESET low (5 ms); VOUT dips to 0.37 V and recovers to 4.96 V in ≈ 60 ms with the soft start |
| Vin = 12 V (PD fallback) | Inhibited, VOUT = 0 |
| Main FET failing short | **Not protected** (no crowbar/series disconnect): VOUT → Vin |

## 8. Protection — what is actually implemented
Implemented and simulated: UV lockout, selector-valid interlock, soft-start, OV (stop switching; 3.3/5 V modes), OC with hiccup, gate clamp (D10), TVS, polyfuse. **Not implemented:** reverse polarity on the USB side (USB-C is keyed; the PD controller handles polarity — no separate P-MOSFET), crowbar for FET failure, thermal shutdown, true OV protection in 12 V mode at 13.8 V, load-side protection. I do not claim the converter is "protected" beyond these simulated behaviours.

## 9. PCB notes (`kicad/buck555.kicad_pcb`)
* 2 layers; GND pours on both sides, 78 stitching vias; mounting holes M3 ×4; USB-C on the left edge, output terminal J2 at the right; test points TP1 PWM (OUT555), TP2 GATE, TP3 SW, TP4 VOUT, TP5 GND, TP6 +12 V, TP7 RESET bus, TP8 +15 V, TP9 HOLD.
* Track widths: +15V, VSRC, SW, VOUT = **1.2 mm throughout** (≈ 3.8 A at 20 K rise); +12V 0.5 mm; USB-side VBUS/VBUS_SW mostly **0.5 mm** (≈ 2 A) — below the 3 A fuse hold (fine up to ≈ 1.6 A input, marginal during overload); signals 0.25 mm; clearance 0.2 mm (0.25 mm power).
* Switch loop: M1 → D11 9.4 mm, Cin (C6) → M1 9.2 mm, M1 → L1 20.9 mm. **The hot loop is not as tight as it could be** (a manual re-placement would improve it); fine at 25 kHz, would matter for EMC.
* Thermal: SO-8 FET and SMA/SMC diode rely on copper pours; no heatsinking; estimated losses are 0.03–0.14 W (assumed device values).
* Autorouted; a human should review the routing before fabrication.
* Not done: 3D/mechanical fit check of J1, L1 (Ø21 mm), C20; controlled-impedance not needed.

## Design package contents
`kicad/` project (`.kicad_pro/.kicad_sch/.kicad_pcb`, `buck555.kicad_sym`, `buck555.pretty`, lib tables, `buck555_BOM.csv`, `buck555.net`, `.xml`, `buck555_schematic.pdf`, `buck555_pcb.pdf`, `buck555_drc.rpt`, `fab/` gerbers, drill, pos, `generators/` Python used to build it) · `multisim/` (SPICE netlists, table, README, results) · `sim_sources/` (generator, models, suites, raw result text) · `plots/` (A startup, B steady-state, D/E load & line, F1–F3 faults, schematic, PCB images).
