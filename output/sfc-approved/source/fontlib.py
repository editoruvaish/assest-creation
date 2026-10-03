from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import functools
SRC='fonts/Montserrat.ttf'
@functools.lru_cache(None)
def inst(w):
    f=TTFont(SRC); return instancer.instantiateVariableFont(f,{'wght':w})
def glyph(w,ch):
    f=inst(w); gs=f.getGlyphSet(); name=f.getBestCmap()[ord(ch)]
    return gs,name,gs[name].width
def path(w,ch,size,x,y,rot=0):
    """svg path d for glyph at baseline origin (x,y), font size px, rotation deg about origin"""
    import math
    gs,name,adv=glyph(w,ch); s=size/1000.0
    c,sn=math.cos(math.radians(rot)),math.sin(math.radians(rot))
    # glyph coords (gx,gy) y-up -> svg: X=x+s*(gx*c + gy*sn), Y=y+s*(gx*sn - gy*c)
    t=(s*c, s*sn, s*sn, -s*c, x, y)
    # fontTools Transform order (xx,xy,yx,yy,dx,dy): X=xx*gx+yx*gy+dx ; Y=xy*gx+yy*gy+dy
    t=(s*c, s*sn, s*sn, -s*c, x, y)
    pen=SVGPathPen(gs, ntos=lambda v:'%.2f'%v); tp=TransformPen(pen,t); gs[name].draw(tp)
    return pen.getCommands(), adv*s

def path_F_adjusted(w,size,x,y,dy_units,dx_units):
    from fontTools.pens.recordingPen import RecordingPen
    gs,name,adv=glyph(w,'F'); rp=RecordingPen(); gs[name].draw(rp)
    def adj(p):
        px,py=p
        if 250<py<420:
            py+=dy_units
            if px>300: px-=dx_units
        return (px,py)
    pen=SVGPathPen(gs, ntos=lambda v:'%.2f'%v); s=size/1000.0
    tp=TransformPen(pen,(s,0,0,-s,x,y))
    for op,args in rp.value:
        getattr(tp,op)(*[adj(a) for a in args])
    return pen.getCommands()
