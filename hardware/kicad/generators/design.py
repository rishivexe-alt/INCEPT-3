"""Single source of truth for the hardware design: parts, values, footprints, nets, sections.
Everything (schematic, netlist check, BOM, PCB) is generated from this table."""

R0603='Resistor_SMD:R_0603_1608Metric'; R0805='Resistor_SMD:R_0805_2012Metric'
R1206='Resistor_SMD:R_1206_3216Metric'; R2512='Resistor_SMD:R_2512_6332Metric'
C0603='Capacitor_SMD:C_0603_1608Metric'; C0805='Capacitor_SMD:C_0805_2012Metric'
C1206='Capacitor_SMD:C_1206_3216Metric'; C1210='Capacitor_SMD:C_1210_3225Metric'
CEL63='Capacitor_SMD:CP_Elec_6.3x7.7'; CEL8='Capacitor_SMD:CP_Elec_8x10'
SOT23='Package_TO_SOT_SMD:SOT-23'; SOD123='Diode_SMD:D_SOD-123'; SMA='Diode_SMD:D_SMA'
SOIC8='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'; SOIC14='Package_SO:SOIC-14_3.9x8.7mm_P1.27mm'
TSSOP16='Package_SO:TSSOP-16_4.4x5mm_P0.65mm'

P=[]   # list of dicts
def add(ref,lib,value,fp,pins,sec,mfr='',mpn='',desc='',units=None,flags=None,bom=True,vf='gen'):
    P.append(dict(ref=ref,lib=lib,value=value,fp=fp,pins=pins,sec=sec,mfr=mfr,mpn=mpn,desc=desc,units=units,flags=flags or {},bom=bom,vf=vf))

# vf = verification status of the manufacturer part number:
#   'ds'  = datasheet for this exact part was read during this design session
#   'gen' = generic/common part, MPN from engineer's knowledge, NOT verified in this session (check before ordering)
#   'spec'= no MPN chosen: specification only (see notes)

def R(ref,val,a,b,sec,fp=R0603,mpn='',mfr='',desc='',tol='1%'):
    add(ref,'Device:R',val,fp,{'1':a,'2':b},sec,mfr,mpn,desc or f'Resistor {val} {tol}')
def C(ref,val,a,b,sec,fp=C0603,mpn='',mfr='',desc='',pol=False):
    add(ref,'Device:C_Polarized' if pol else 'Device:C',val,fp,{'1':a,'2':b},sec,mfr,mpn,desc or f'Capacitor {val}')
def NM(ref,d,g,s,sec,desc=''):   # 2N7002 SOT-23: 1=G 2=S 3=D
    add(ref,'Device:Q_NMOS_GSD','2N7002',SOT23,{'1':g,'2':s,'3':d},sec,'onsemi','2N7002',desc or 'N-MOSFET 60 V 115 mA',vf='gen')
def DD(ref,k,a,sec,val='1N4148W',fp=SOD123,mfr='Diodes Inc.',mpn='1N4148W-7-F',desc='Small-signal diode 100 V'):
    add(ref,'Device:D',val,fp,{'1':k,'2':a},sec,mfr,mpn,desc)

# ----------------------------------------------------------------- A: input / PD
S='A'
add('J1','Connector:USB_C_Receptacle_PowerOnly_6P','USB-C PD in','Connector_USB:USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal',
    {'A12':'GND','B12':'GND','A9':'VBUS','B9':'VBUS','A5':'CC1','B5':'CC2','S1':'SHIELD'},S,'GCT','USB4125-GF-A','USB-C power-only 6-pin receptacle',vf='gen')
R('R1','5.1k','CC1','GND',S,desc='CC1 Rd (per IP2721 datasheet figure - verify, see risks)',mpn='RC0603FR-075K1L',mfr='Yageo')
R('R2','5.1k','CC2','GND',S,desc='CC2 Rd (per IP2721 datasheet figure - verify, see risks)',mpn='RC0603FR-075K1L',mfr='Yageo')
R('R37','1M','SHIELD','GND',S,desc='USB shield bleed',mpn='RC0603FR-071ML',mfr='Yageo')
C('C22','4.7n','SHIELD','GND',S,fp=C0603,mpn='CC0603KRX7R9BB472',mfr='Yageo',desc='USB shield 50 V X7R')
add('U1','Interface_USB:IP2721','IP2721',TSSOP16,{'1':'VBUSG','2':'VBUS','5':'GND','11':'NC','12':'CC2','13':'CC1','16':'VBUS_SW'},S,
    'Injoinic','IP2721','USB-C PD sink (trigger), SEL floating = 15 V request',vf='ds')
add('Q1','Device:Q_NMOS_GSD','AO3400A',SOT23,{'1':'VBUSG','2':'VBUS_SW','3':'VBUS'},S,'Alpha & Omega','AO3400A','PD path NMOS 30 V 5.7 A',vf='gen')
C('C1','1u','VBUS','GND',S,mpn='GRM188R71H105KA61D',mfr='Murata',desc='IP2721 VIN cap 50 V X7R')
C('C2','1u','VBUS_SW','GND',S,mpn='GRM188R71H105KA61D',mfr='Murata',desc='IP2721 VBUS cap 50 V X7R')
add('D1','Diode:SMAJ15A','SMAJ15A',SMA,{'1':'VBUS','2':'GND'},S,'Littelfuse','SMAJ15A','TVS 15 V standoff, 24.4 V clamp',vf='gen')
add('F1','Device:Fuse','3A hold',"Fuse:Fuse_1812_4532Metric",{'1':'VBUS_SW','2':'+15V'},S,'Bourns','MF-MSMF300/16X-2','Resettable fuse 3 A hold, >=16 V (verify rating)',vf='gen')
C('C3','47u','+15V','GND',S,fp=CEL63,pol=True,mpn='EEE-FK1E470P',mfr='Panasonic',desc='Input bulk 25 V electrolytic')
C('C4','10u','+15V','GND',S,fp=C1210,mpn='GRM32ER71E106KA12L',mfr='Murata',desc='Input ceramic 25 V X7R')
C('C5','100n','+15V','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo',desc='Input HF decoupling 50 V X7R')
R('R3','0.15','+15V','VSRC',S,fp=R2512,mpn='CRM2512-FX-R150ELF',mfr='Bourns',desc='Current-sense resistor 1 W 1%')
C('C6','2.2u','VSRC','GND',S,fp=C1206,mpn='GRM31CR71E225KA73L',mfr='Murata',desc='Switch-node input cap 25 V X7R')
C('C7','100n','VSRC','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo',desc='Switch HF cap')

# ----------------------------------------------------------------- B: aux rails
S='B'
add('U2','Regulator_Linear:L78L12_SO8','L78L12',SOIC8,{'1':'+12V','2':'GND','3':'GND','4':'NC','5':'NC','6':'GND','7':'GND','8':'+15V'},S,
    'STMicroelectronics','L78L12ACD13TR','12 V timer/logic rail (555 max supply 15 V)',vf='gen')
C('C8','100n','+15V','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo')
C('C9','10u','+12V','GND',S,fp=C1206,mpn='GRM31CR71E106KA12L',mfr='Murata',desc='12 V rail 25 V X7R')
C('C10','100n','+12V','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo')
add('U3','Reference_Voltage:TL431D','TL431',SOIC8,{'1':'VREF','8':'VREF','2':'GND','3':'GND','6':'GND','7':'GND'},S,'Texas Instruments','TL431AIDR','2.495 V reference (K tied to REF)',vf='gen')
R('R4','3.9k','+12V','VREF',S,mpn='RC0603FR-073K9L',mfr='Yageo',desc='TL431 bias ~2.4 mA')
C('C11','100n','VREF','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo')

# ----------------------------------------------------------------- C: interlocks
S='C'
add('U4','Comparator:LM339','LM339',SOIC14,{'4':'VREF','5':'UVS','2':'RST',   # unit A  UV
    '6':'VH','7':'VAL','1':'RST',                                              # unit B  position valid
    '10':'VREF','11':'OVS','13':'OVF',                                         # unit C  OV
    '8':'OCB','9':'OCA','14':'OCF',                                            # unit D  OC
    '3':'+12V','12':'GND'},S,'Texas Instruments','LM339DR','Quad comparator, open-collector (UV, selector-valid, OV, OC)',vf='gen')
R('R15','100k','+12V','RST',S,mpn='RC0603FR-07100KL',mfr='Yageo',desc='RESET pull-up (OR-wired interlock bus)')
R('R16','100k','+15V','UVS',S,mpn='RT0603BRD07100KL',mfr='Yageo',desc='UV divider top 0.1%')
R('R17','22.6k','UVS','GND',S,mpn='RT0603BRD0722K6L',mfr='Yageo',desc='UV divider bottom 0.1%')
C('C15','10n','UVS','GND',S,mpn='CC0603KRX7R9BB103',mfr='Yageo')
R('R18','10k','+12V','VH',S,mpn='RC0603FR-0710KL',mfr='Yageo')
R('R19','10k','VH','GND',S,mpn='RC0603FR-0710KL',mfr='Yageo')

# ----------------------------------------------------------------- D: timer + selector
S='D'
add('U5','Timer:TLC555xD','TLC555',SOIC8,{'1':'GND','8':'+12V','2':'TC','3':'OUT555','4':'RST','5':'CTRL','6':'TC','7':'X'},S,
    'Texas Instruments','TLC555CDR','CMOS 555 astable PWM generator (2-15 V)',vf='ds')
C('C12','4.7n','TC','GND',S,mpn='GCM1885C1H472JA16D',mfr='Murata',desc='Timing cap C0G/NP0 50 V')
C('C13','10n','CTRL','GND',S,mpn='CC0603KRX7R9BB103',mfr='Yageo',desc='CONTROL pin 10 nF')
C('C14','2.2u','CTRL','GND',S,fp=C0805,mpn='GRM21BR71A225KA01L',mfr='Murata',desc='Soft-start cap 10 V X7R')
DD('D2','TC','X',S,desc='Charge-steering diode (X -> TC)')
DD('D3','Y','TC',S,desc='Discharge-steering diode (TC -> Y)')
DD('D4','RST','CTRL',S,desc='Soft-start reset diode (CTRL -> RST)')
for i,(ra,rb,rav,rbv) in enumerate((('953','9.76k','RC0603FR-07953RL','RC0603FR-079K76L'),('2.21k','8.66k','RC0603FR-072K21L','RC0603FR-078K66L'),('7.5k','3.4k','RC0603FR-077K5L','RC0603FR-073K4L')),1):
    R(f'R{4+i}',ra,'+12V',f'A{i}',S,mpn=rav,mfr='Yageo',desc=f'RA mode {i}')
    NM(f'Q{1+i}',f'A{i}',f'M{i}','X',S,desc=f'RA select mode {i}')
    R(f'R{7+i}',rb,'Y',f'B{i}',S,mpn=rbv,mfr='Yageo',desc=f'RB mode {i}')
    NM(f'Q{4+i}',f'B{i}',f'M{i}','X',S,desc=f'RB select mode {i}')
add('J3','Connector:Conn_01x04_Pin','ROTARY','Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    {'1':'+12V','2':'M1','3':'M2','4':'M3'},S,'Generic','2.54mm 1x4 header','Off-board rotary switch: 1 pole x 3 pos, NON-shorting (break-before-make)',vf='spec')
add('SW1','Switch:SW_Rotary_1x3_MP','3.3V / 5V / 12V','',{'4':'+12V','1':'M1','2':'M2','3':'M3','MP':'NC'},S,'','','Documentation symbol of the off-board rotary switch (not placed on PCB)',bom=False,flags={'no_board':True})
for i in (1,2,3): R(f'R{10+i}','100k',f'M{i}','GND',S,mpn='RC0603FR-07100KL',mfr='Yageo',desc=f'M{i} pull-down')
for i in (1,2,3): DD(f'D{4+i}',  'VAL',f'M{i}',S,desc='Selector-valid OR diode')
R('R14','100k','VAL','GND',S,mpn='RC0603FR-07100KL',mfr='Yageo',desc='VAL pull-down')

# ----------------------------------------------------------------- E: protections
S='E'
for i,(rv,mp) in enumerate((('18.2','RC1206FR-0718R2L'),('44.2','RC1206FR-0744R2L'),('147','RC1206FR-07147RL')),1):
    R(f'R{19+i}',rv,'VOUT',f'T{i}',S,fp=R2512,mpn=mp.replace('RC1206','RC2512'),mfr='Yageo',desc=f'Preload/OV-sense top resistor mode {i} (1 W)')
    NM(f'Q{7+i}',f'T{i}',f'M{i}','OVS',S,desc=f'Preload/OV string select mode {i}')
R('R23','30.1','OVS','GND',S,fp=R2512,mpn='RC2512FK-0730R1L',mfr='Yageo',desc='OV sense low-side 1 W')
C('C16','100n','OVS','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo')
R('R24','2.2k','+12V','OVF',S,mpn='RC0603FR-072K2L',mfr='Yageo')
DD('D8','HOLD','OVF',S,desc='OV -> hold-off')
R('R25','2.2k','+12V','OCF',S,mpn='RC0603FR-072K2L',mfr='Yageo')
DD('D9','HOLD','OCF',S,desc='OC -> hold-off')
R('R26','10.6k','+15V','OCA',S,mpn='RT0603BRD0710K6L',mfr='Yageo',desc='OC divider 0.1%')
R('R27','10k','OCA','GND',S,mpn='RT0603BRD0710KL',mfr='Yageo',desc='OC divider 0.1%')
C('C17','1n','OCA','GND',S,mpn='CC0603KRX7R9BB102',mfr='Yageo')
R('R28','10k','VSRC','OCB',S,mpn='RT0603BRD0710KL',mfr='Yageo',desc='OC divider 0.1%')
R('R29','10k','OCB','GND',S,mpn='RT0603BRD0710KL',mfr='Yageo',desc='OC divider 0.1%')
C('C18','1n','OCB','GND',S,mpn='CC0603KRX7R9BB102',mfr='Yageo')
C('C19','22n','HOLD','GND',S,mpn='CC0603KRX7R9BB223',mfr='Yageo',desc='Hold-off timing cap')
R('R30','1.5M','HOLD','GND',S,mpn='RC0603FR-071M5L',mfr='Yageo',desc='Hold-off timing resistor')
NM('Q11','RST','HOLD','GND',S,desc='Hold-off RESET pull-down')
R('R31','1M','RST','BL',S,mpn='RC0603FR-071ML',mfr='Yageo')
add('Q12','Device:Q_NPN_BEC','MMBT2222A',SOT23,{'1':'BL','2':'GND','3':'LC'},S,'onsemi','MMBT2222ALT1G','Run-LED driver',vf='gen')
add('D12','Device:LED','GREEN',"LED_SMD:LED_0603_1608Metric",{'1':'LC','2':'LK'},S,'Wurth','150060GS75000','Run indicator',vf='gen')
R('R32','2.7k','+12V','LK',S,mpn='RC0603FR-072K7L',mfr='Yageo')

# ----------------------------------------------------------------- F: driver + power
S='F'
R('R33','4.7k','OUT555','NB',S,mpn='RC0603FR-074K7L',mfr='Yageo',desc='NPN base resistor R6')
add('Q13','Device:Q_NPN_BEC','MMBT2222A',SOT23,{'1':'NB','2':'GND','3':'GD'},S,'onsemi','MMBT2222ALT1G','Gate driver NPN (2N2222A class)',vf='gen')
R('R34','470','GD','GATE',S,mpn='RC0603FR-07470RL',mfr='Yageo',desc='Gate series resistor (limits clamp current)')
R('R35','1k','VSRC','GATE',S,mpn='RC0603FR-071KL',mfr='Yageo',desc='Gate pull-up R7')
add('D10','Device:D_Zener','12V',SOD123,{'1':'VSRC','2':'GATE'},S,'Diodes Inc.','MMSZ5242B-7-F','Gate-source clamp 12 V (FDS4435A VGS max 20 V)',vf='gen')
add('M1','buck555:FDS4435A','FDS4435A',SOIC8,{'1':'VSRC','2':'VSRC','3':'VSRC','4':'GATE','5':'SW','6':'SW','7':'SW','8':'SW'},S,'onsemi','FDS4435A','P-MOSFET -30 V -8.8 A 20 mohm SO-8 (verify pinout vs datasheet drawing)',vf='ds')
add('D11','Diode:SS34','SS34',SMA,{'1':'SW','2':'GND'},S,'Vishay','SS34-E3/57T','Schottky 40 V 3 A freewheel diode',vf='gen')
add('L1','Device:L','1mH','Inductor_THT:L_Radial_D21.0mm_P19.00mm',{'1':'SW','2':'VOUT'},S,'','','1 mH, Isat >= 4.5 A (-30% L), Irms >= 2 A, DCR <= 0.12 ohm. NO MPN CHOSEN - see notes',vf='spec')
C('C20','220u','VOUT','GND',S,fp=CEL8,pol=True,mpn='EEE-FK1E221P',mfr='Panasonic',desc='Output bulk 25 V low-ESR (check ripple current)')
C('C21','100n','VOUT','GND',S,mpn='CC0603KRX7R9BB104',mfr='Yageo')
add('J2','Connector:Screw_Terminal_01x02','VOUT','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',{'1':'VOUT','2':'GND'},S,'Phoenix Contact','1729128','Output terminal 5.08 mm',vf='gen')
tp=[('TP1','OUT555','PWM (555 OUT)'),('TP2','GATE','PMOS gate'),('TP3','SW','Switch node'),('TP4','VOUT','Output'),('TP5','GND','GND'),('TP6','+12V','12 V rail'),('TP7','RST','Interlock bus'),('TP8','+15V','Input rail'),('TP9','HOLD','Hold-off')]
for ref,net,d in tp:
    add(ref,'Connector:TestPoint',d,'TestPoint:TestPoint_Pad_D2.0mm',{'1':net},'F','','','Test point '+d,vf='spec')
for k in range(1,5):
    add(f'MH{k}','Mechanical:MountingHole','M3','MountingHole:MountingHole_3.2mm_M3_Pad_Via',{},'F','','','M3 mounting hole',bom=False,flags={'mh':True})

SECTIONS={'A':'A  INPUT: USB-C PD SINK (15 V), PROTECTION, SENSE','B':'B  AUXILIARY RAILS: 12 V TIMER RAIL, 2.495 V REFERENCE',
 'C':'C  INTERLOCK COMPARATORS (OPEN-COLLECTOR, OR-WIRED ON RESET)','D':'D  555 PWM, DIODE-STEERED TIMING, MODE SELECTOR (ROTARY)',
 'E':'E  PROTECTION: OVERVOLTAGE, OVERCURRENT, HOLD-OFF, MIN-LOAD','F':'F  GATE DRIVER + BUCK POWER STAGE + TEST POINTS'}
POWER_NETS={'GND':'power:GND','+12V':'power:+12V','+15V':'power:+15V','VBUS':'power:VBUS'}
