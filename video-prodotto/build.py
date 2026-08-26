from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, math, os, shutil, subprocess, imageio_ffmpeg

W,H,FPS,DUR=1080,1920,30,10.0
N=int(FPS*DUR)
FF=imageio_ffmpeg.get_ffmpeg_exe()
ACID=(228,255,60); WHITE=(246,246,243); DARK=(16,16,18); SMOKE=(158,155,148)
ANTON='fonts/Anton.ttf'; ARCH='fonts/ArchivoBlack.ttf'

# suola gum reale solo su beige e grigio; sulle altre e' in tinta
VARIANTS=[
 dict(slug='grigio',   src='grigio-1024x1024.jpg',   label='SUOLA GUM',     sub='presa e ammortizzazione', lift=0),
 dict(slug='beige',    src='beige-1024x1024.jpg',    label='SUOLA GUM',     sub='presa e ammortizzazione', lift=0),
 dict(slug='marrone',  src='marrone-1024x1024.jpg',  label='ZEPPA INTERNA', sub='nascosta nella suola',    lift=20),
 dict(slug='bordeaux', src='bordeaux-1024x1024.jpg', label='ZEPPA INTERNA', sub='nascosta nella suola',    lift=28),
 dict(slug='nero',     src='nero-1024x1024.jpg',     label='SUOLA GUM',     sub='presa e ammortizzazione', lift=62, gain=1.45),
]

_F={}
def font(p,s):
    k=(p,int(s))
    if k not in _F: _F[k]=ImageFont.truetype(p,int(s))
    return _F[k]

def cutout(path,gain=1.0):
    src=Image.open(path).convert('RGB'); w,h=src.size
    g=np.asarray(src.convert('L'))
    # .copy() indispensabile: floodfill non scrive su un'immagine che condivide
    # il buffer di sola lettura di numpy, fallisce in silenzio riempiendo 0 pixel
    m=Image.fromarray(((g>238).astype(np.uint8)*255),'L').copy()
    for xy in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
        if m.getpixel(xy)==255: ImageDraw.floodfill(m,xy,128,thresh=0)
    alpha=np.where(np.asarray(m)==128,0,255).astype(np.uint8)
    a=Image.fromarray(alpha,'L').filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    a2=np.clip((np.asarray(a).astype(np.float32)/255-0.12)/0.80,0,1)
    rgb=np.asarray(src).astype(np.float32)
    if gain!=1.0: rgb=np.clip(255*np.power(rgb/255,1/gain),0,255)
    # il de-fringe deve scalare col guadagno, altrimenti schiarendo il prodotto
    # si schiarisce anche l'alone di fondo rimasto sui pixel di bordo
    rgb[(a2>0.05)&(a2<0.95)]*=0.93/gain
    out=Image.fromarray(rgb.astype(np.uint8),'RGB')
    out.putalpha(Image.fromarray((a2*255).astype(np.uint8),'L'))
    return out.crop(out.getbbox())

def make_bg(lift):
    y=np.linspace(0,1,H)[:,None]; x=np.linspace(0,1,W)[None,:]
    r=np.broadcast_to(22+14*(1-y)+6*x,(H,W)); g=np.broadcast_to(22+13*(1-y)+5*x,(H,W)); b=np.broadcast_to(25+12*(1-y)+4*x,(H,W))
    base=np.dstack([r,g,b]).astype(np.float32)+lift
    rng=np.random.default_rng(7); blot=rng.normal(0,1,(H//8,W//8))
    blot=np.array(Image.fromarray(((blot-blot.min())/np.ptp(blot)*255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(np.float32)
    base+=((blot-128)*(0.055+lift*0.0016))[:,:,None]
    yy,xx=np.mgrid[0:H,0:W]
    d=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    base*=np.clip(1.12-0.46*d**1.7,0,1.3)[:,:,None]
    return np.clip(base,0,255)

GR=[np.array(Image.fromarray(np.clip(np.random.default_rng(100+i).normal(0,6.5,(H//2,W//2))+128,0,255).astype(np.uint8)).resize((W,H),Image.BILINEAR)).astype(np.float32)-128 for i in range(6)]
SCRIM=Image.new('RGBA',(W,H),(0,0,0,0))
_s=np.zeros((H,W),np.float32); _s[int(H*0.70):]=np.linspace(0,205,H-int(H*0.70))[:,None]
SCRIM.putalpha(Image.fromarray(_s.astype(np.uint8),'L'))

def eo(t,p=3): return 1-(1-min(max(t,0),1))**p
def cl(t): return min(max(t,0.0),1.0)

def line(d,x,y,s,f,fill=WHITE,track=0,off=5):
    if track==0:
        d.text((x+off,y+off),s,font=f,fill=(0,0,0,190),anchor='mm'); d.text((x,y),s,font=f,fill=fill,anchor='mm'); return
    ws=[d.textlength(c,font=f)+track for c in s]; tot=sum(ws)-track; sx=x-tot/2
    for c,wd in zip(s,ws):
        d.text((sx+off,y+off),c,font=f,fill=(0,0,0,190),anchor='lm'); d.text((sx,y),c,font=f,fill=fill,anchor='lm'); sx+=wd

def band(d,x,y,s,f,bg=ACID,fg=DARK,padx=30,pady=16):
    bb=d.textbbox((0,0),s,font=f,anchor='lt'); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
    x0,y0,x1,y1=x-tw/2-padx,y-th/2-pady,x+tw/2+padx,y+th/2+pady
    d.rectangle([x0,y0,x1,y1],fill=bg)
    d.text((x-tw/2-bb[0],y-th/2-bb[1]),s,font=f,fill=fg,anchor='lt')
    return x0,y0,x1,y1

A1,B1,C1,D1,E0=2.02,4.45,5.62,6.85,6.85

def build(v):
    shoe=cutout(v['src'],v.get('gain',1.0)); SW,SH=shoe.size
    BG=make_bg(v['lift'])
    fd=f"frames_{v['slug']}"; shutil.rmtree(fd,ignore_errors=True); os.makedirs(fd)
    cache={}
    def sh(scale,rot):
        k=(round(scale,3),round(rot,1))
        if k not in cache:
            im=shoe.resize((max(2,int(SW*scale)),max(2,int(SH*scale))),Image.LANCZOS)
            if abs(rot)>0.05: im=im.rotate(rot,resample=Image.BICUBIC,expand=True)
            cache[k]=im
            if len(cache)>150: cache.pop(next(iter(cache)))
        return cache[k]
    def at(cv,scale,cx,cy,rot=0.0,shadow=True):
        im=sh(scale,rot); w,h=im.size; px,py=int(cx-w/2),int(cy-h/2)
        if shadow:
            s=Image.new('RGBA',(w,h),(0,0,0,0)); s.paste((0,0,0,150),(0,0),im.getchannel('A'))
            cv.alpha_composite(s.filter(ImageFilter.GaussianBlur(26)),(px+10,py+30))
        cv.alpha_composite(im,(px,py))
    def roi(cv,scale,rx,ry,cx,cy,rot=0.0):
        at(cv,scale,cx-(rx-0.5)*SW*scale,cy-(ry-0.5)*SH*scale,rot,shadow=False)

    for i in range(N):
        t=i/FPS
        cv=Image.fromarray(np.clip(BG+GR[i%6][:,:,None]*0.85,0,255).astype(np.uint8),'RGB').convert('RGBA')
        d=ImageDraw.Draw(cv,'RGBA')
        jx=math.sin(t*7.3)*2.2+math.sin(t*17.1)*1.1
        jy=math.cos(t*6.1)*2.0+math.cos(t*13.7)*0.9
        if t<A1:
            p=cl(t/A1)
            at(cv,0.90+0.085*eo(cl(t/0.42),4)+0.03*p,W/2+jx,H*0.40+jy-12*p,rot=-4+1.5*p)
            if t>0.34:
                q=eo(cl((t-0.34)/0.16),4); line(d,W/2+jx,H*0.755+jy,"FERMATI",font(ANTON,100*(0.82+0.18*q)),track=4)
            if t>0.52:
                q=eo(cl((t-0.52)/0.16),4); line(d,W/2+jx,H*0.755+112+jy,"UN SECONDO",font(ANTON,100*(0.82+0.18*q)),track=4)
        elif t<B1:
            p=cl((t-A1)/(B1-A1))
            at(cv,1.00+0.055*p,W*0.52+jx,H*0.315+jy,rot=-2.5-2*p)
            if t>A1+0.06: line(d,W/2+jx,1150+jy,"IL PRODOTTO",font(ANTON,86),track=3)
            if t>A1+0.30:
                q=eo(cl((t-A1-0.30)/0.14),4)
                band(d,W/2+jx,1300+jy,"PIÙ VENDUTO",font(ANTON,104*(0.86+0.14*q)),padx=32,pady=18)
            if t>A1+0.62: line(d,W/2+jx,1408+jy,"DEL WEB",font(ANTON,86),track=3)
        elif t<C1:
            p=cl((t-B1)/(C1-B1))
            roi(cv,3.05,0.46+0.05*p,0.885,W/2+jx*2,H*0.44+jy*2,rot=-2)
            cv.alpha_composite(SCRIM)
            band(d,W/2+jx,H*0.845+jy,v['label'],font(ARCH,46),padx=32,pady=18)
            line(d,W/2+jx,H*0.905+jy,v['sub'],font(ARCH,30),fill=SMOKE,off=3)
        elif t<D1:
            p=cl((t-C1)/(D1-C1))
            roi(cv,2.60,0.30,0.52-0.05*p,W/2+jx*2,H*0.40+jy*2,rot=-2)
            cv.alpha_composite(SCRIM)
            band(d,W/2+jx,H*0.845+jy,"EFFETTO CAMOSCIO",font(ARCH,44),bg=WHITE,fg=DARK,padx=30,pady=18)
            line(d,W/2+jx,H*0.905+jy,"inserti a contrasto",font(ARCH,30),fill=SMOKE,off=3)
        else:
            p=cl((t-E0)/(DUR-E0))
            at(cv,0.88-0.03*p,W/2+jx,H*0.285+jy,rot=-3)
            f=font(ANTON,88)
            line(d,W/2+jx,1085+jy,"NON LASCIARTELO",f,track=3)
            line(d,W/2+jx,1183+jy,"SFUGGIRE",f,track=3)
            if t>E0+0.75:
                q=eo(cl((t-E0-0.75)/0.18),4); pulse=1+0.035*math.sin((t-E0-0.75)*9.0)
                x0,y0,x1,y1=band(d,W/2+jx,1400+jy,"CLICCA QUI",font(ANTON,80*(0.8+0.2*q)*pulse),padx=56,pady=26)
                d.rectangle([x0-9,y0-9,x1+9,y1+9],outline=(228,255,60,95),width=3)
            line(d,W/2+jx,1600+jy,"BELLAMICA · SNEAKERS ISA",font(ARCH,32),fill=SMOKE,off=3)
            line(d,W/2+jx,1668+jy,"TAGLIE 36 – 41",font(ARCH,30),fill=SMOKE,off=3)
            line(d,W/2+jx,1770+jy,"23,00 €",font(ANTON,76),track=2)
        cv.convert('RGB').save(f'{fd}/f{i:04d}.jpg',quality=95)
    outp=f"spot-isa-{v['slug']}-10s.mp4"
    subprocess.run([FF,'-y','-loglevel','error','-framerate','30','-i',f'{fd}/f%04d.jpg','-i','out/mix.wav',
        '-c:v','libx264','-profile:v','high','-pix_fmt','yuv420p','-crf','19','-preset','medium',
        '-c:a','aac','-b:a','192k','-ar','44100','-movflags','+faststart','-shortest',outp],check=True)
    shutil.rmtree(fd,ignore_errors=True)
    print('OK',outp,os.path.getsize(outp)//1024,'KB',flush=True)

import sys
sel=sys.argv[1:] 
for v in VARIANTS:
    if not sel or v['slug'] in sel: build(v)
print('TUTTE FATTE')
