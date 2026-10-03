from build import *
import os
from chrome_render import render as chrome
OUT='/home/user/assest-creation/output/sfc-approved'
for d in ('assets','assets-cropped'): os.makedirs(OUT+'/'+d,exist_ok=True)
S=3840/H; PW=int(round(W*S)); PH=3840
L=build_layers()
JOBS=[]
def save(svg,path_svg,path_png,px,now=False):
    open(path_svg,'w').write(svg)
    chrome([(path_svg,path_png,px[0],px[1])])
frame=compose(L,[k for k in L if k!='SFC' and not k.startswith('letter-')],px=(PW,PH))
save(frame,OUT+'/frame-transparent.svg',OUT+'/frame-transparent_4K.png',(PW,PH))
# preview on black
im=Image.open(OUT+'/frame-transparent_4K.png').convert('RGBA'); bg=Image.new('RGBA',im.size,(0,0,0,255)); bg.alpha_composite(im); bg.convert('RGB').save(OUT+'/frame-on-black_4K.png')
info={}
for name,layers in GROUPS.items():
    svg=compose(L,layers,px=(PW,PH))
    save(svg,'%s/assets/%s.svg'%(OUT,name),'%s/assets/%s_4K.png'%(OUT,name),(PW,PH))
    a=np.array(Image.open('%s/assets/%s_4K.png'%(OUT,name)))[:,:,3]
    ys,xs=np.where(a>2); x0,x1,y0,y1=xs.min()/S,(xs.max()+1)/S,ys.min()/S,(ys.max()+1)/S
    pad=3; vb=(x0-pad,y0-pad,x1-x0+2*pad,y1-y0+2*pad); px=(int(round(vb[2]*S)),int(round(vb[3]*S)))
    svgc=compose(L,layers,vb=vb,px=px)
    save(svgc,'%s/assets-cropped/%s.svg'%(OUT,name),'%s/assets-cropped/%s_4K.png'%(OUT,name),px)
    info[name]=[round(v,1) for v in vb]; print(name,px)
# individual letters
for i,(ch,d) in enumerate(SFC):
    pass
json.dump(info,open(OUT+'/asset-bounds.json','w'),indent=1)
