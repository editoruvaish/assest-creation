import numpy as np, math, io, cv2
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, binary_erosion, binary_dilation, label
f2=lambda v:('%.2f'%v).rstrip('0').rstrip('.')
hx=lambda c:'#%02x%02x%02x'%tuple(int(round(min(255,max(0,v)))) for v in c)
def dp(xs,Y,tol):
    n=len(xs); keep=[0,n-1]; stack=[(0,n-1)]
    while stack:
        a,b=stack.pop()
        if b-a<2: continue
        t=(xs[a+1:b]-xs[a])/(xs[b]-xs[a]); interp=Y[a]+(Y[b]-Y[a])*t[:,None]
        err=np.abs(Y[a+1:b]-interp).max(1); i=int(err.argmax())
        if err[i]>tol: k=a+1+i; keep.append(k); stack+=[(a,k),(k,b)]
    return sorted(keep)
def fill_nan(Y):
    Y=Y.copy(); n=len(Y); idx=np.arange(n)
    for c in range(Y.shape[1]):
        ok=~np.isnan(Y[:,c])
        Y[:,c]=0 if ok.sum()==0 else np.interp(idx,idx[ok],Y[ok,c])
    return Y
def poly_d(pts): return 'M'+' L'.join('%s %s'%(f2(x),f2(y)) for x,y in pts)+' Z'
def band_matrix(data,mask,ix0,ix1,bands,nch):
    H,W=mask.shape
    cols=np.arange(ix0,ix1+1); M=np.full((len(bands),len(cols),nch),np.nan)
    for bi,(ya,yb) in enumerate(bands):
        ya_,yb_=max(ya,0),min(yb,H)
        if yb_<=ya_: continue
        cc=np.clip(cols,0,W-1)
        sub=data[ya_:yb_][:,cc]; sm=mask[ya_:yb_][:,cc]
        for j in range(len(cols)):
            v=sub[:,j][sm[:,j]]
            if len(v): M[bi,j]=np.median(v,axis=0)
    for bi in range(len(bands)):
        if not np.isnan(M[bi]).all(): M[bi]=fill_nan(M[bi])
    ok=[bi for bi in range(len(bands)) if not np.isnan(M[bi]).any()]
    if not ok: M[:]=0
    else:
        for bi in range(len(bands)):
            if np.isnan(M[bi]).any(): M[bi]=M[min(ok,key=lambda k:abs(k-bi))]
    return M
def wrap(defs,body,vb,px):
    return '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%s %s %s %s">\n<defs>%s</defs>\n%s\n</svg>'%(px[0],px[1],f2(vb[0]),f2(vb[1]),f2(vb[2]),f2(vb[3]),defs,body)

def extend_colors(ref,interior,sigmas=(2,4,8,16,32,64)):
    """Fill colour outside `interior` by normalised-convolution extension (smooth, no stair-steps)."""
    w0=interior.astype(float); out=np.zeros_like(ref); have=interior.copy()
    out[interior]=ref[interior]
    for sg in sigmas:
        num=np.stack([gaussian_filter(ref[:,:,c]*w0,sg) for c in range(3)],2); den=gaussian_filter(w0,sg)
        ok=(den>1e-3)&~have
        out[ok]=num[ok]/den[ok][:,None]; have|=ok
        if have.all(): break
    return out

def soft_layer(name,ref,pts,interior,sigma=1.5,band=2,tol=1.2,sg=1.0,blur_fill=(0.4,0.8),margin=10,cover=None,x_lim=None,xsm=1.5):
    """Opaque banded-gradient fill (fitted on `interior` pixels of ref) masked by a blurred polygon -> soft silhouette."""
    xs_=[p[0] for p in pts]; ys_=[p[1] for p in pts]
    x0,x1,y0,y1=min(xs_)-margin,max(xs_)+margin,min(ys_)-margin,max(ys_)+margin
    ix0,ix1=int(math.floor(x0)),int(math.ceil(x1)); cols=np.arange(ix0,ix1+1)
    bands=[(a,min(a+band,int(math.ceil(y1)))) for a in range(int(math.floor(y0)),int(math.ceil(y1)),band)]
    data=extend_colors(ref,interior)
    M=band_matrix(data,np.ones(interior.shape,bool),ix0,ix1,bands,3)
    M=gaussian_filter(M,(sg,xsm,0),mode='nearest')
    defs=[];rects=[]
    for bi,(ya,yb) in enumerate(bands):
        keep=dp(cols.astype(float),M[bi],tol); gid='g%s-%03d'%(name,bi)
        stops=''.join('<stop offset="%s" stop-color="%s"/>'%(f2(min(1,max(0,(cols[k]+0.5-x0)/(x1-x0)))),hx(M[bi][k])) for k in keep)
        defs.append('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%s" y1="0" x2="%s" y2="0">%s</linearGradient>'%(gid,f2(x0),f2(x1),stops))
        top=ya; bot=yb+0.5
        rects.append('<rect x="%s" y="%s" width="%s" height="%s" fill="url(#%s)"/>'%(f2(x0),f2(top),f2(x1-x0),f2(bot-top),gid))
    defs.append('<filter id="fb-%s" x="-2%%" y="-2%%" width="104%%" height="104%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="%s %s"/></filter>'%(name,f2(blur_fill[0]),f2(blur_fill[1])))
    defs.append('<filter id="mb-%s" x="-20%%" y="-20%%" width="140%%" height="140%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="%s"/></filter>'%(name,f2(sigma)))
    defs.append('<mask id="mask-%s" maskUnits="userSpaceOnUse" x="%s" y="%s" width="%s" height="%s"><g filter="url(#mb-%s)"><path d="%s" fill="#fff"/></g></mask>'%(name,f2(x0),f2(y0),f2(x1-x0),f2(y1-y0),name,poly_d(pts)))
    body='<g id="%s" mask="url(#mask-%s)"><g filter="url(#fb-%s)">%s</g></g>'%(name,name,name,''.join(rects))
    return ''.join(defs),body

def alpha_layer(name,ref,region,tol=1.5,band=1,sg=0.8,blur=(0.3,0.7),ext=0.0,data_mask=None):
    """Glow/streak layer over transparent bg: colour+alpha (premultiplied-on-black decomposition) via colour bands + luminance-mask bands."""
    x0,y0,x1,y1=region
    cols=np.arange(x0,x1); H,W=ref.shape[:2]
    bands=[(a,min(a+band,y1)) for a in range(y0,y1,band)]
    m=np.ones((H,W),bool) if data_mask is None else data_mask
    M=band_matrix(ref,m,x0,x1-1,bands,3)
    M=gaussian_filter(M,(sg,0,0),mode='nearest')
    defs=[];rects=[];mrects=[]
    for bi,(ya,yb) in enumerate(bands):
        Y=M[bi]; a=np.clip(Y.max(1)/255.0,0,1)
        col=np.minimum(np.where(a[:,None]>0.02,Y/np.maximum(a[:,None],0.02),255.0),255)
        keep=dp(cols.astype(float),np.c_[Y,a*255],tol); gid='g%s-%03d'%(name,bi)
        st=''.join('<stop offset="%s" stop-color="%s"/>'%(f2((cols[k]+0.5-x0)/(x1-x0)),hx(col[k])) for k in keep)
        ms=''.join('<stop offset="%s" stop-color="%s"/>'%(f2((cols[k]+0.5-x0)/(x1-x0)),hx((a[k]*255,)*3)) for k in keep)
        defs.append('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">%s</linearGradient>'%(gid,x0,x1,st))
        defs.append('<linearGradient id="m%s" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">%s</linearGradient>'%(gid,x0,x1,ms))
        top=ya-(4 if bi==0 else 0); bot=yb+(4 if bi==len(bands)-1 else 0.5)
        rects.append('<rect x="%d" y="%s" width="%d" height="%s" fill="url(#%s)"/>'%(x0,f2(top),x1-x0,f2(bot-top),gid))
        mrects.append('<rect x="%d" y="%s" width="%d" height="%s" fill="url(#m%s)"/>'%(x0,f2(top),x1-x0,f2(bot-top),gid))
    defs.append('<filter id="fb-%s" x="-1%%" y="-5%%" width="102%%" height="110%%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="%s %s"/></filter>'%(name,f2(blur[0]),f2(blur[1])))
    defs.append('<mask id="mask-%s" maskUnits="userSpaceOnUse" x="%d" y="%d" width="%d" height="%d"><g filter="url(#fb-%s)">%s</g></mask>'%(name,x0,y0-4,x1-x0,y1-y0+8,name,''.join(mrects)))
    body='<g id="%s" mask="url(#mask-%s)"><g filter="url(#fb-%s)">%s</g></g>'%(name,name,name,''.join(rects))
    return ''.join(defs),body

def contour_poly(mask,eps=1.2,pad=0):
    m=np.pad(mask,pad,mode='edge').astype(np.uint8)*255
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    c=max(cs,key=cv2.contourArea); ap=cv2.approxPolyDP(c,eps,True)[:,0,:].astype(float)-pad+0.5
    return [tuple(p) for p in ap]
