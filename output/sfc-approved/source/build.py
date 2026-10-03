import sys; sys.path.insert(0,'.')
import numpy as np, io, math, json, cairosvg, fontlib
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, binary_dilation, binary_erosion
ref=np.array(Image.open('../images/1.png').convert('RGB')).astype(float)
H,W=ref.shape[:2]   # 1256 x 706
f2=lambda v:('%.2f'%v).rstrip('0').rstrip('.')
hx=lambda c:'#%02x%02x%02x'%tuple(int(round(min(255,max(0,v)))) for v in c)

# ---------- geometry (measured) ----------
CX,CY=364.90,743.31; RO,RI=199.32,127.18
SL_ANG,SL_C,SL_HW=45.71,2.0,36.47
PIECES={
 'plinth':[(130.86,791.4),(574.14,791.4),(574.14,807.4),(130.86,807.4)],
 'step':[(162.25,762.5),(542.8,762.5),(542.8,791.4),(162.25,791.4)],
 'base-block':[(183.15,714.2),(521.85,714.2),(521.85,762.5),(183.15,762.5)],
 'column-1':[(223.1,584.25),(245.85,584.25),(245.85,714.2),(223.1,714.2)],
 'column-2':[(342.6,584.25),(365.35,584.25),(365.35,714.2),(342.6,714.2)],
 'column-3':[(462.2,584.25),(485.2,584.25),(485.2,714.2),(462.2,714.2)],
 'architrave':[(183.1,536.5),(521.9,536.5),(521.9,584.25),(183.1,584.25)],
 'cornice':[(171.4,516.8),(533.4,516.8),(533.4,536.5),(171.4,536.5)],
 'roof':[(227.1,516.8),(318.4,447.2),(386.4,447.2),(477.7,516.8)],
}
def poly_d(pts): return 'M'+' L'.join('%s %s'%(f2(x),f2(y)) for x,y in pts)+' Z'
def poly_mask(pts,erode=1):
    ss=4; im=Image.new('L',(W*ss,H*ss),0)
    ImageDraw.Draw(im).polygon([(x*ss,y*ss) for x,y in pts],fill=255)
    a=np.array(im.resize((W,H),Image.BOX))>=254
    if erode: a=binary_erosion(a,iterations=erode)
    return a

# ---------- fonts ----------
def text_layout(text,w,size,x,by,track,rot=0):
    ds=[];cx=0;c,s=math.cos(math.radians(rot)),math.sin(math.radians(rot))
    for ch in text:
        gs,name,adv=fontlib.glyph(w,ch)
        d,_=fontlib.path(w,ch,size,x+cx*c,by+cx*s,rot); ds.append((ch,d))
        cx+=adv*size/1000+track
    return ds
SFC=[('S',fontlib.path(100,'S',195,160.2,496.4)[0]),('F',fontlib.path_F_adjusted(100,195,277.5,496.4,23,0)),('C',fontlib.path(100,'C',195,406.5,496.4)[0])]
GRANTED=text_layout('granted',500,33.414,283.229,165.728,0.485)
APPR=json.load(open('appr_params.json')) if __import__('os').path.exists('appr_params.json') else dict(w=100,size=52.26,x=284.54,by=848.04,tr=0,rot=-45.0)
APPROVED=text_layout('Approved',APPR['w'],APPR['size'],APPR['x'],APPR['by'],APPR['tr'],APPR['rot'])

def render_svg(svg,scale=1.0,bg=None):
    png=cairosvg.svg2png(bytestring=svg.encode(),output_width=int(round(W*scale)),output_height=int(round(H*scale)),background_color=bg)
    return np.array(Image.open(io.BytesIO(png)).convert('RGBA')).astype(float)
def wrap(defs,body,vb=(0,0,W,H),px=None):
    w,h=(px if px else (W,H))
    return '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s %s %s %s">\n<defs>%s</defs>\n%s\n</svg>'%(w,h,f2(vb[0]),f2(vb[1]),f2(vb[2]),f2(vb[3]),defs,body)

# ---------- piecewise-linear simplification ----------
def dp(xs,Y,tol):
    """Y: (n,k) -> indices of kept points so max |Y - interp| <= tol"""
    n=len(xs); keep=[0,n-1]; stack=[(0,n-1)]
    while stack:
        a,b=stack.pop()
        if b-a<2: continue
        t=(xs[a+1:b]-xs[a])/(xs[b]-xs[a]); interp=Y[a]+(Y[b]-Y[a])*t[:,None]
        err=np.abs(Y[a+1:b]-interp).max(1); i=int(err.argmax())
        if err[i]>tol: k=a+1+i; keep.append(k); stack+= [(a,k),(k,b)]
    return sorted(keep)
def fill_nan(Y):
    Y=Y.copy(); n=len(Y); idx=np.arange(n)
    for c in range(Y.shape[1]):
        ok=~np.isnan(Y[:,c])
        if ok.sum()==0: Y[:,c]=0
        else: Y[:,c]=np.interp(idx,idx[ok],Y[ok,c])
    return Y

# ---------- text exclusion mask (Approved strokes baked in fits otherwise) ----------
def paths_mask(paths):
    svg=wrap('','<rect width="%d" height="%d" fill="#000"/>'%(W,H)+''.join('<path d="%s" fill="#fff"/>'%d for _,d in paths))
    return render_svg(svg)[:,:,0]>40
TEXTMASK=binary_dilation(paths_mask(APPROVED),iterations=2)

# ---------- banded gradient layer ----------
def band_matrix(data,mask,ix0,ix1,bands,nch):
    cols=np.arange(ix0,ix1+1); M=np.full((len(bands),len(cols),nch),np.nan)
    for bi,(ya,yb) in enumerate(bands):
        sub=data[ya:yb,ix0:ix1+1]; sm=mask[ya:yb,ix0:ix1+1]
        for j in range(len(cols)):
            v=sub[:,j][sm[:,j]]
            if len(v): M[bi,j]=np.median(v,axis=0)
    # fill: columns missing in a band -> interpolate along x; fully-missing bands -> neighbours along y
    for bi in range(len(bands)):
        if not np.isnan(M[bi]).all(): M[bi]=fill_nan(M[bi])
    ok=[bi for bi in range(len(bands)) if not np.isnan(M[bi]).any()]
    if not ok: M[:]=0
    else:
        for bi in range(len(bands)):
            if np.isnan(M[bi]).any():
                near=min(ok,key=lambda k:abs(k-bi)); M[bi]=M[near]
    return M
def band_layer(name,pts,mask,tol=1.0,band=1,alpha=False,ext=3.0,blur=(0.8,0.7),use_text_excl=True,sg=1.0,extend=None):
    """returns (defs, body). Piece = clip shape filled by horizontal gradient bands fitted to the reference."""
    xs_=[p[0] for p in pts]; ys_=[p[1] for p in pts]
    x0,x1,y0,y1=min(xs_),max(xs_),min(ys_),max(ys_)
    ix0,ix1=int(math.floor(x0)),int(math.ceil(x1)); cols=np.arange(ix0,ix1+1)
    m=mask.copy()
    if use_text_excl: m&=~TEXTMASK
    gx0,gx1=x0-ext,x1+ext
    bands=[(a,min(a+band,int(math.ceil(y1)))) for a in range(int(math.floor(y0)),int(math.ceil(y1)),band)]
    M=band_matrix(ref,m,ix0,ix1,bands,3)
    if sg>0 and len(bands)>2: M=gaussian_filter(M,(sg,0,0),mode='nearest')
    defs=[];rects=[];mrects=[]
    for bi,(ya,yb) in enumerate(bands):
        Y=M[bi]
        if alpha:
            a=np.clip(Y.max(1)/255.0,0,1)
            col=np.minimum(np.where(a[:,None]>0.02,Y/np.maximum(a[:,None],0.02),255.0),255)
            F=np.c_[Y,a*255]
        else: F=Y
        keep=dp(cols.astype(float),F,tol)
        gid='g%s-%03d'%(name,bi); stops='';mstops=''
        for k in keep:
            off=f2(min(1,max(0,(cols[k]+0.5-gx0)/(gx1-gx0))))
            if alpha:
                stops+='<stop offset="%s" stop-color="%s"/>'%(off,hx(col[k]))
                g=a[k]*255; mstops+='<stop offset="%s" stop-color="%s"/>'%(off,hx((g,g,g)))
            else: stops+='<stop offset="%s" stop-color="%s"/>'%(off,hx(Y[k]))
        defs.append('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%s" y1="0" x2="%s" y2="0">%s</linearGradient>'%(gid,f2(gx0),f2(gx1),stops))
        top=ya-(8 if bi==0 else 0); bot=yb+(8 if bi==len(bands)-1 else 0.5)
        rects.append('<rect x="%s" y="%s" width="%s" height="%s" fill="url(#%s)"/>'%(f2(gx0),f2(top),f2(gx1-gx0),f2(bot-top),gid))
        if alpha:
            defs.append('<linearGradient id="m%s" gradientUnits="userSpaceOnUse" x1="%s" y1="0" x2="%s" y2="0">%s</linearGradient>'%(gid,f2(gx0),f2(gx1),mstops))
            mrects.append('<rect x="%s" y="%s" width="%s" height="%s" fill="url(#m%s)"/>'%(f2(gx0),f2(top),f2(gx1-gx0),f2(bot-top),gid))
    cid='clip-'+name
    defs.append('<clipPath id="%s"><path d="%s"/></clipPath>'%(cid,poly_d(pts)))
    defs.append('<filter id="blur-%s" x="-5%%" y="-20%%" width="110%%" height="140%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="%s %s"/></filter>'%(name,f2(blur[0]),f2(blur[1])))
    inner='<g filter="url(#blur-%s)">%s</g>'%(name,''.join(rects))
    if alpha:
        defs.append('<mask id="mask-%s" maskUnits="userSpaceOnUse" x="%s" y="%s" width="%s" height="%s"><g filter="url(#blur-%s)">%s</g></mask>'%(name,f2(gx0),f2(y0-8),f2(gx1-gx0),f2(y1-y0+16),name,''.join(mrects)))
        inner='<g mask="url(#mask-%s)">%s</g>'%(name,inner)
    body='<g id="%s" clip-path="url(#%s)">%s</g>'%(name,cid,inner)
    return ''.join(defs),body

# ---------- ring / slash ----------
def ring_slash_paths():
    ang=math.radians(SL_ANG); u=(math.cos(ang),-math.sin(ang)); n=(math.sin(ang),math.cos(ang))
    k1,k2=SL_C-SL_HW,SL_C+SL_HW
    P=lambda k,t:(CX+k*n[0]+t*u[0],CY+k*n[1]+t*u[1])
    RS=RI+2.0
    t1=math.sqrt(RS**2-k1**2); t2=math.sqrt(RS**2-k2**2)
    a=P(k1,-t1);b=P(k1,t1);c=P(k2,t2);d=P(k2,-t2)
    def sweep(p,q):
        a1=math.atan2(p[1]-CY,p[0]-CX);a2=math.atan2(q[1]-CY,q[0]-CX); return 1 if ((a2-a1)%(2*math.pi))<math.pi else 0
    slash='M%s %s L%s %s A%s %s 0 0 %d %s %s L%s %s A%s %s 0 0 %d %s %s Z'%(f2(a[0]),f2(a[1]),f2(b[0]),f2(b[1]),f2(RS),f2(RS),sweep(b,c),f2(c[0]),f2(c[1]),f2(d[0]),f2(d[1]),f2(RS),f2(RS),sweep(d,a),f2(a[0]),f2(a[1]))
    ring='M%s %s A%s %s 0 1 0 %s %s A%s %s 0 1 0 %s %s Z M%s %s A%s %s 0 1 1 %s %s A%s %s 0 1 1 %s %s Z'%(
        f2(CX-RO),f2(CY),f2(RO),f2(RO),f2(CX+RO),f2(CY),f2(RO),f2(RO),f2(CX-RO),f2(CY),
        f2(CX-RI),f2(CY),f2(RI),f2(RI),f2(CX+RI),f2(CY),f2(RI),f2(RI),f2(CX-RI),f2(CY))
    return ring,slash

RING_RGB=(1,33,8); REFL_F=(178,255,227)
def sign_mask():
    yy,xx=np.mgrid[0:H,0:W]; rr=np.hypot(xx-CX,yy-CY)
    ang=math.radians(SL_ANG); d=(xx-CX)*math.sin(ang)+(yy-CY)*math.cos(ang)
    return ((rr<RO)&(rr>RI))|((rr<RI)&(np.abs(d-SL_C)<SL_HW))

def reflection_layer(tol=0.004,band=2,y0=808,y1=980,x0=100,x1=612,blur=1.2,sg=1.0):
    sh=sign_mask(); Bg=np.where(sh[:,:,None],np.array(RING_RGB,float)[None,None,:],0.0)
    F=np.array(REFL_F,float); D=F[None,None,:]-Bg
    a=((ref-Bg)*D).sum(2)/(D*D).sum(2); a=np.clip(a,0,1)
    bands=[(ya,min(ya+band,y1)) for ya in range(y0,y1,band)]
    M=band_matrix(a[:,:,None]*255,~TEXTMASK&np.ones((H,W),bool),x0,x1-1,bands,1)
    M=gaussian_filter(M,(sg,0,0),mode='nearest')/255.0
    cols=np.arange(x0,x1); defs=[];mrects=[]
    for bi,(ya,yb) in enumerate(bands):
        Y=M[bi]; keep=dp(cols.astype(float),Y*255,tol*255); gid='mrefl-%03d'%bi
        stops=''.join('<stop offset="%s" stop-color="%s"/>'%(f2((cols[k]-x0)/(x1-x0)),hx((Y[k,0]*255,)*3)) for k in keep)
        defs.append('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">%s</linearGradient>'%(gid,x0,x1,stops))
        top=ya-(6 if bi==0 else 0); bot=yb+0.5
        mrects.append('<rect x="%d" y="%s" width="%d" height="%s" fill="url(#%s)"/>'%(x0,f2(top),x1-x0,f2(bot-top),gid))
    defs.append('<filter id="blur-reflection" x="-2%%" y="-5%%" width="104%%" height="110%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="0.6 %s"/></filter>'%f2(blur))
    defs.append('<mask id="mask-reflection" maskUnits="userSpaceOnUse" x="%d" y="%d" width="%d" height="%d"><g filter="url(#blur-reflection)">%s</g></mask>'%(x0,y0-6,x1-x0,y1-y0+12,''.join(mrects)))
    return ''.join(defs),'<g id="reflection" mask="url(#mask-reflection)"><rect x="%d" y="%d" width="%d" height="%d" fill="%s"/></g>'%(x0,y0-6,x1-x0,y1-y0+12,hx(F))

def text_body(gid,items,fill='#ffffff',extra=''):
    return '<g id="%s" fill="%s"%s>'%(gid,fill,extra)+''.join('<path id="%s-%s" d="%s"/>'%(gid,('%s%d'%(ch,i)),d) for i,(ch,d) in enumerate(items))+'</g>'

def build_layers():
    L={}   # name -> (defs, body)  in z-order
    ring,slash=ring_slash_paths()
    L['no-sign']=('','<g id="no-sign" fill="%s"><path id="no-sign-ring" fill-rule="evenodd" d="%s"/><path id="no-sign-slash" d="%s"/></g>'%(hx(RING_RGB),ring,slash))
    L['reflection']=reflection_layer()
    L['SFC']=('',text_body('SFC',SFC))
    for i,(ch,d) in enumerate(SFC): L['letter-'+ch]=('',text_body('letter-'+ch,[(ch,d)]))
    rp=poly_d(PIECES['roof'][::-1])
    L['SFC-frame']=('<clipPath id="clip-above-roof"><path d="M0 0 H%d V%d H0 Z %s"/></clipPath>'%(W,H,rp),
        '<g id="SFC" fill="#ffffff">'+''.join('<path id="SFC-%s%d" d="%s"%s/>'%(ch,i,d,' clip-path="url(#clip-above-roof)"' if ch=='F' else '') for i,(ch,d) in enumerate(SFC))+'</g>')
    order=['plinth','step','base-block','column-1','column-2','column-3','architrave','cornice','roof']
    for k in order:
        pts=PIECES[k]; mask=poly_mask(pts,erode=1)
        eb=0.5 if k not in ('plinth','roof') else 0.0
        ypts=max(p[1] for p in pts); pts=[(x,y+eb) if abs(y-ypts)<1e-6 else (x,y) for x,y in pts]
        if k=='roof': dfs,body=band_layer(k,pts,mask,alpha=True,tol=1.5,band=2,blur=(0.6,0.9))
        elif k.startswith('column'): dfs,body=band_layer(k,pts,mask,tol=1.0,band=3,ext=1.0,blur=(0.3,1.3))
        else: dfs,body=band_layer(k,pts,mask,tol=1.0,band=1,blur=(0.8,0.7))
        L[k]=(dfs,body)
    L['Approved']=('',text_body('Approved',APPROVED))
    L['granted']=('',text_body('granted',GRANTED))
    return L

GROUPS={'letter-S':['letter-S'],'letter-F':['letter-F'],'letter-C':['letter-C'], # asset name -> list of layer names
 'granted':['granted'],'SFC':['SFC'],'approved':['Approved'],'no-sign':['no-sign'],'reflection':['reflection'],
 'roof':['roof'],'cornice':['cornice'],'architrave':['architrave'],'column-1':['column-1'],'column-2':['column-2'],'column-3':['column-3'],
 'base-block':['base-block'],'step':['step'],'plinth':['plinth'],
 'building':['plinth','step','base-block','column-1','column-2','column-3','architrave','cornice','roof'],
}
def compose(L,names,vb=(0,0,W,H),px=None):
    defs=''.join(L[n][0] for n in names); body='\n'.join(L[n][1] for n in names)
    return wrap(defs,body,vb,px)

if __name__=='__main__':
    L=build_layers()
    svg=compose(L,[k for k in L.keys() if k!='SFC' and not k.startswith('letter-')])
    open('frame.svg','w').write(svg); print('svg bytes',len(svg))
    R=render_svg(svg,1.0)
    a=R[:,:,3:4]/255.0; comp=R[:,:,:3]*a   # over black
    diff=np.abs(comp-ref)
    print('mean abs diff',diff.mean().round(3))
    Image.fromarray(np.clip(comp,0,255).astype(np.uint8)).save('comp.png')
    Image.fromarray(np.clip(diff*4,0,255).astype(np.uint8)).save('diff.png')
