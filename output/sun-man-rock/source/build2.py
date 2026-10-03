import sys; sys.path.insert(0,'.')
from lib import *
from scipy.ndimage import maximum_filter
import json, os
ref=np.array(Image.open('../images/2.png').convert('RGB')).astype(float)
H,W=ref.shape[:2]; L=ref.max(2)
yy,xx=np.mgrid[0:H,0:W]
SUN=(216.26,529.81,160.59); HORIZON=529.81
def conn(mask,seed):
    lab,n=label(mask); return lab==lab[seed] if lab[seed] else np.zeros_like(mask)
# ---- rock ----
Lmax=maximum_filter(L,size=25)
rock_m=(L>0.45*Lmax)&(L>3)&(yy>=738)
rock_m[:744,436:586]=False
rock_m=conn(rock_m,(1200,600))
rock_top=np.full(W,H,int)
for x in range(W):
    ys=np.where(rock_m[:,x])[0]
    if len(ys): rock_top[x]=ys.min()
# ---- man ----
from scipy.ndimage import binary_closing
man_m=(L>12)&(L>0.3*maximum_filter(L,size=15))&(xx>=433)&(xx<=590)&(yy>=415)&(yy<746)
man_m=binary_closing(man_m,iterations=1)
man_m=conn(man_m,(520,520))
# ---- stick + knob ----
stick_m=np.zeros((H,W),bool)
stick_m[550:748,411:437]=(L[550:748,411:437]>22)
knob=(L>0.45*maximum_filter(L,size=15))&(L>32)&(xx>=400)&(xx<=440)&(yy>=525)&(yy<=562)
stick_m|=knob
stick_m[746:,:]=False
stick_m=conn(stick_m,(650,422))
# arm touching knob -> belongs to man; ensure stick excludes x>436
stick_m&=(xx<=437)
def er(m,k): return binary_erosion(m,iterations=k)
from lib import extend_colors
from scipy.ndimage import binary_fill_holes
def refine(mask0,core_k,grow=9,thr=0.5):
    """core -> smooth colour extension -> sub-pixel matte (L / extended core L) -> cleaner silhouette polygon."""
    core=er(mask0,core_k)
    ext=extend_colors(ref,core,sigmas=(2,3,5,8,16,32))
    a=np.clip(L/np.maximum(ext.max(2),1.0),0,1.2)
    near=binary_dilation(mask0,iterations=grow)
    m=(a>thr)&near
    m=binary_fill_holes(m)
    lab,n=label(m); 
    if n>1:
        sizes=np.bincount(lab.ravel()); sizes[0]=0; m=lab==sizes.argmax()
    return m,core
def build_layers(P=None):
    P=P or dict(rock_sig=2.0,man_sig=1.4,stick_sig=1.8)
    Lr={}
    cx,cy,r=SUN
    sun='M%s %s A%s %s 0 0 1 %s %s Z'%(f2(cx-r),f2(HORIZON),f2(r),f2(r),f2(cx+r),f2(HORIZON))
    Lr['sun']=('','<path id="sun" d="%s" fill="#ffffff"/>'%sun)
    wm=np.ones((H,W),bool); wm[:,417:]=False
    kn=np.zeros((H,W),bool); kn[525:566,402:441]=binary_dilation(L[525:566,402:441]>70,iterations=2); wm&=~kn
    wref=ref*np.clip((417-xx)/13.0,0,1)[:,:,None]
    Lr['water-glow']=alpha_layer('water-glow',wref,(0,530,417,745),tol=1.5,band=1,data_mask=wm,blur=(0.0,0.7))
    rm,rc=refine(rock_m,7); rm[:744,436:586]=False
    rp=contour_poly(rm,eps=1.3,pad=20)
    Lr['rock']=soft_layer('rock',ref,rp,rc,sigma=P['rock_sig'],band=2,tol=1.0,xsm=3.5)
    sp=contour_poly(stick_m,eps=0.8)
    Lr['walking-stick']=soft_layer('walking-stick',ref,sp,er(stick_m,1),sigma=P['stick_sig'],band=2,tol=1.0,margin=6)
    mp=contour_poly(man_m,eps=1.0)
    Lr['man']=soft_layer('man',ref,mp,er(man_m,2),sigma=P['man_sig'],band=2,tol=1.0)
    return Lr
def compose(Lr,names,vb=(0,0,W,H),px=None):
    px=px or (W,H)
    return wrap(''.join(Lr[n][0] for n in names),'\n'.join(Lr[n][1] for n in names),vb,px)
ORDER=['sun','water-glow','rock','walking-stick','man']
if __name__=='__main__':
    Lr=build_layers(); svg=compose(Lr,ORDER); open('frame2.svg','w').write(svg); print('svg',len(svg))
    from chrome_render import render
    render([(os.path.abspath('frame2.svg'),os.path.abspath('frame2_chrome.png'),W,H)])
    r=Image.open('frame2_chrome.png').convert('RGBA'); bg=Image.new('RGBA',r.size,(0,0,0,255)); bg.alpha_composite(r); bg=bg.convert('RGB'); bg.save('comp2.png')
    b=np.array(bg).astype(float); d=np.abs(b-ref)
    print('mean diff',d.mean().round(3))
    regs={'sun':(40,360,390,530),'water':(0,530,410,745),'man':(430,415,590,750),'stick':(400,525,440,750),'rock':(150,740,703,1259)}
    for k,(x0,y0,x1,y1) in regs.items(): print(k,d[y0:y1,x0:x1].mean().round(2),'p99',np.percentile(d[y0:y1,x0:x1],99).round(1))
    Image.fromarray(np.clip(d*4,0,255).astype(np.uint8)).save('diff2.png')
