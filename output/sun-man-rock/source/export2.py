from build2 import *
from chrome_render import render as chrome
OUT='/home/user/assest-creation/output/sun-man-rock'
for d in ('assets','assets-cropped'): os.makedirs(OUT+'/'+d,exist_ok=True)
S=3840/H; PW=int(round(W*S)); PH=3840
Lr=build_layers()
def save(svg,ps,pp,px):
    open(ps,'w').write(svg); chrome([(ps,pp,px[0],px[1])])
save(compose(Lr,ORDER,px=(PW,PH)),OUT+'/frame-transparent.svg',OUT+'/frame-transparent_4K.png',(PW,PH))
im=Image.open(OUT+'/frame-transparent_4K.png').convert('RGBA'); bg=Image.new('RGBA',im.size,(0,0,0,255)); bg.alpha_composite(im); bg.convert('RGB').save(OUT+'/frame-on-black_4K.png')
info={}
for name in ORDER:
    save(compose(Lr,[name],px=(PW,PH)),'%s/assets/%s.svg'%(OUT,name),'%s/assets/%s_4K.png'%(OUT,name),(PW,PH))
    a=np.array(Image.open('%s/assets/%s_4K.png'%(OUT,name)))[:,:,3]
    ys,xs=np.where(a>3); x0,x1,y0,y1=xs.min()/S,(xs.max()+1)/S,ys.min()/S,(ys.max()+1)/S
    pad=3; vb=(x0-pad,y0-pad,x1-x0+2*pad,y1-y0+2*pad); px=(int(round(vb[2]*S)),int(round(vb[3]*S)))
    save(compose(Lr,[name],vb=vb,px=px),'%s/assets-cropped/%s.svg'%(OUT,name),'%s/assets-cropped/%s_4K.png'%(OUT,name),px)
    info[name]=[round(v,1) for v in vb]; print(name,px)
json.dump(info,open(OUT+'/asset-bounds.json','w'),indent=1)
