# INCEPT-3 — Early Design Notes

**Status: simulation-only starting point.** Numbers below come from a behavioural Python model
(`buck555_sim.py`) because LTspice was not available while I worked. The netlist
`buck555_selectable.cir` has **not** been run in LTspice. Treat every figure as a prediction
to be confirmed there and then on the bench.

## 1. Recommended starting values

| Item | Spec starting value | Recommended | Why |
|---|---|---|---|
| Switching frequency | – | ~25 kHz | Easy for a 555 + NPN/PMOS driver; low switching loss |
| Timing C | 10 nF | **4.7 nF C0G/NP0** | Keeps RA/RB in the 1.5–10 kΩ range so diode drop errors stay modest |
| L1 | 220 µH | **1 mH** (Isat ≥ 3 A, DCR ≤ 0.15 Ω) | At 220 µH the 3.3 V mode ripple is 0.51 A p-p on a 0.33 A load; 1 mH gives 0.11 A |
| COUT | 100 µF | **220 µF**, low-ESR, ≥ 25 V | Ripple 6–8 mV with 50 mΩ ESR |
| R6 (base) | 4.7 kΩ | 4.7 kΩ | ≈2.4 mA base drive, ample for 15 mA collector current |
| R7 (gate pull-up) | 10 kΩ | **1 kΩ** | 10 kΩ turns the PMOS off too slowly, see §4 |
| D3 | generic | Schottky ≥ 40 V, ≥ 3 A (SS34 / SB340) | Freewheel current up to ~1.2 A average, higher on faults |
| Q1 | NPN | 2N2222A / MMBT2222A or BC337 | ~15 mA collector current |
| Q-gate | – | FDS4435A, |Vgs| max 25 V | OK at 15 V; add clamp if input can exceed ~20 V |

## 2. Timing network, calibrated for a 10 Ω load at 15 V in

Diode-steered: `VCC → RA → X → D1 → C`, and discharge `C → D2 → RB → X`, with the 555 DISCH pin on node X.
Both diodes 1N4148. Sum of times held at ≈ 40 µs so frequency stays near 25 kHz in every position.

| Position | RA (charge) | RB (discharge) | 555 OUT duty | PMOS ON duty | Predicted f |
|---|---|---|---|---|---|
| 3.3 V | 1.50 kΩ | 9.53 kΩ | 13.6 % | 24.4 % | 25.06 kHz |
| 5 V | 2.80 kΩ | 8.25 kΩ | 25.1 % | 35.6 % | 25.04 kHz |
| 12 V | 8.06 kΩ | 3.09 kΩ | 71.8 % | 81.8 % | 25.00 kHz |

The 555 output duty is lower than the PMOS duty because the 1 kΩ pull-up stretches the gate turn-off
(≈ 2.2 µs time constant) while the NPN pulls the gate down quickly. The ideal D = Vout/Vin targets
(22 / 33 / 80 %) are matched by the *PMOS* duty plus diode and switch losses.

## 3. Predicted results (15 V, 10 Ω load)

| Mode | Vout | Ripple p-p | IL min / max | Efficiency | PMOS loss | Diode loss |
|---|---|---|---|---|---|---|
| 3.3 V | 3.335 V | 6 mV | 0.28 / 0.39 A | 71 % | 17 mW | 86 mW |
| 5 V | 5.032 V | 8 mV | 0.43 / 0.57 A | 84 % | 37 mW | 116 mW |
| 12 V | 11.98 V | 8 mV | 1.15 / 1.24 A | 95 % | 139 mW | 94 mW |

Efficiency at 3.3 V is low mainly because the fixed overhead (555 ≈ 10 mA at 15 V, and the 1 kΩ gate
pull-up burning 15 mA while the NPN is on) is large next to a 1.1 W output.

## 4. Open-loop behaviour, the serious findings

1. **Line sensitivity is direct** (Vout ∝ Vin). At 12 V in the "12 V" mode gives 9.4 V, at 20 V in it gives 16.4 V.
   If the PD negotiation falls back to 5 V or 9 V, the output will be wrong, and the 555 may not run at all.
   Gate the load on a power-good signal from the PD sink.
2. **Light load runs away (discontinuous mode).** With a 100 Ω load, "3.3 V" gives 4.2 V and "5 V" gives 5.8 V.
   Add a permanent bleed/minimum load (e.g. 330 Ω–1 kΩ) or, better, feedback.
3. **Load droop.** 5 Ω load: 3.22 / 4.88 / 11.68 V. Re-calibrate RA/RB at the real operating load.
4. **Startup overshoot.** From 0 V into 10 Ω: 3.3 V mode peaks at 5.1 V, 5 V mode at 7.8 V,
   **12 V mode at 18.9 V**, with inductor current up to 5.5 A. Needs a soft start, an overvoltage
   clamp or crowbar on the output, and an inductor that does not saturate at that current.
5. **Short circuit.** Inductor current climbs past 10 A in 3 ms with no limiting (the 12 V duty is held
   regardless). Add input fuse/polyfuse plus a current-sense trip that forces the PMOS off
   (for instance a sense resistor at the source driving a transistor that pulls 555 RESET low).
6. **Rotary switch transitions.** While the selector is between positions the timing node is open, the 555 output
   stays latched in whichever state it was in. If that is HIGH the PMOS is held on and VOUT climbs to Vin;
   the model shows 17–19 V peaks and 4–5 A inductor current for 1–5 ms gaps. Use a make-before-break arrangement
   that never leaves RA or RB open **or** pull 555 RESET low (via a switch contact) between positions so
   the PMOS is forced off; and disconnect the load during changes.
7. **Gate clamp (optional).** |Vgs| ≈ 14.85 V at 15 V in, inside the ±25 V rating. If you want margin against
   input spikes, put a ~12 V zener across gate–source (anode on gate) **and** a 330 Ω–470 Ω resistor between
   the NPN collector and the gate node, otherwise the NPN fights the zener when it pulls the gate low.
   Keep R7 on the gate side so the pull-up still works.

## 5. Schematic connections (checked against your spec)

- **555:** pin 1 → GND; pin 8 → +15 V (or a filtered/regulated rail; NE555 max 16 V, a bipolar NE555 is
  tight at 15 V, prefer a CMOS TLC555/LMC555 rated higher, or put a 12 V LDO/zener on VCC);
  pin 4 → VCC; pin 5 → 10 nF to GND; pins 2 and 6 tied to the C node; pin 7 → node X;
  pin 3 → R6 → Q1 base.
- **Timing:** RA from VCC to X; D1 anode X, cathode C-node; D2 anode C-node, cathode to RB; RB other end → X.
- **Driver:** Q1 emitter → GND, collector → PMOS gate; R7 from +15 V to gate.
- **Power:** PMOS source → +15 V, drain → SW; D3 cathode → SW, anode → GND; L1 SW → VOUT; COUT and load VOUT → GND.
- **Compared with your first screenshot:** R1/R2/R3 were all in parallel (≈1.4 kΩ combined), so no selectable
  timing existed. The scheme above replaces them with one RA/RB pair per rotary position. I could not verify the
  D1/D2/R4 wiring from the image alone.

## 6. PD input

A 15 V contract needs a PD sink controller or trigger board (e.g. CH224K/CH224Q, STUSB4500, AP33772), configured for
15 V. Confirm the adapter advertises a 15 V PDO (many 65 W+ chargers do, many 18/20 W ones don't).
Fallback if negotiation fails: the controller stays at 5 V, so the output must be disabled (hold 555 RESET low via the
sink's power-good). Add: input fuse/polyfuse (≈ 3 A), TVS (e.g. SMAJ18A), a 100 µF + 0.1 µF bulk/decoupling at the
555 supply, and reverse-polarity protection if the input is not exclusively the PD connector.

## 7. Verification plan (your steps A–E)

A. Run the 555 alone: `V(tc)` must swing 5 V ↔ 10 V; expect f ≈ 25 kHz, duty as in §2.
B. Add Q1 + PMOS with 1 kΩ drain load; check Vsg ≈ 14.8 V when on and the drain 0 ↔ 15 V.
C. Add D3/L1/C3/R5 and plot V(out), V(gate), V(sw), V(lx), I(L1), Id(M1) over a few periods and over ~20 ms.
D. Fill in the §3 table from LTspice and trim RA/RB until each mode is on target at your real load.
E. Repeat for Vin = 12 / 15 / 20 V, loads 5–100 Ω, startup, mode changes, and a shorted output. Don't accept
   "average Vout correct" alone: look at start-up peak, inductor peak and gate waveform.

## 8. Limits of this model

No Miller plateau, Coss or diode reverse-recovery ringing, no inductor saturation or temperature,
and a fixed gate capacitance. Real turn-on/turn-off times and efficiency will differ; the efficiency
values in particular are indicative only.
