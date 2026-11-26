"""Helpers: load stock KiCad symbols (flatten 'extends'), emit KiCad-7 schematic S-expressions."""
import copy, uuid, math, re, os
from pathlib import Path
from kiutils.symbol import SymbolLib, Symbol
SYM_DIR=os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')
_libs={}
def _lib(n):
    if n not in _libs:
        L=SymbolLib.from_file(f'{SYM_DIR}/{n}.kicad_sym'); _libs[n]=({s.entryName:s for s in L.symbols},L)
    return _libs[n][0]
def get_symbol(libid):
    """return flattened Symbol (no extends) with libraryNickname set"""
    lib,name=libid.split(':'); d=_lib(lib)
    s=d[name]
    if s.extends:
        par=copy.deepcopy(d[s.extends]); 
        # parent units are named after the parent; rename to child
        par.entryName=name; par.extends=None
        for u in par.units: u.entryName=name
        for p in s.properties:
            for q in par.properties:
                if q.key==p.key: q.value=p.value
        par.properties=[q for q in par.properties]
        s=par
    s=copy.deepcopy(s); s.libraryNickname=lib; 
    return s
def uid(): return str(uuid.uuid4())

def pins_of(sym):
    """list of dict(number,name,type,x,y,angle,length,unit,hide)"""
    out=[]
    for u in sym.units:
        for p in u.pins:
            out.append(dict(number=p.number,name=p.name,type=p.electricalType,x=p.position.X,y=p.position.Y,angle=p.position.angle or 0,length=p.length,unit=u.unitId,hide=bool(p.hide)))
    return out
def rot(x,y,deg):
    t=math.radians(deg); c,s=round(math.cos(t),6),round(math.sin(t),6)
    return x*c-y*s, x*s+y*c
def pin_abs(px,py,pang,X,Y,rotdeg,mirror=None):
    x,y=px,py
    if mirror=='x': y=-y; pang=-pang
    if mirror=='y': x=-x; pang=180-pang
    rx,ry=rot(x,y,rotdeg)
    # outward direction (screen coordinates, y down)
    ox,oy=rot(math.cos(math.radians(pang)),math.sin(math.radians(pang)),rotdeg)
    out=(-ox,+oy)   # y-up outward -> flip y for screen: outward_up=(-ox,-oy) -> screen (-ox,+oy)
    return (round(X+rx,4),round(Y-ry,4)),(round(out[0]),round(out[1]))
