from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, math, os, shutil, subprocess, imageio_ffmpeg
exec(open('build.py').read().split('A1,B1,C1,D1,E0')[0])   # cutout, band, line, eo, cl, font, SCRIM-free helpers

FPS,DUR=30,10.0; N=int(FPS*DUR)
FF=imageio_ffmpeg.get_ffmpeg_exe()
A1,B1,C1,D1,E0=2.02,4.45,5.62,6.85,6.85
V=dict(slug='grigio',src='grigio-1024x1024.jpg',label='SUOLA GUM',sub='presa e ammortizzazione',lift=0,gain=1.0)

FORMATS=[
  dict(name='16x9',W=1920,H=1080, k=0.78, side=True),
]

def grain(W,H):
    return [np.array(Image.fromarray(np.clip(np.random.default_rng(100+i).normal(0,6.5,(H//2,W//2))+128,0,255).astype(np.uint8)).resize((W,H),Image.BILINEAR)).astype(np.float32)-128 for i in range(6)]

def bg(W,H,lift):
    y=np.linspace(0,1,H)[:,None]; x=np.linspace(0,1,W)[None,:]
    r=np.broadcast_to(22+14*(1-y)+6*x,(H,W)); g=np.broadcast_to(22+13*(1-y)+5*x,(H,W)); b=np.broadcast_to(25+12*(1-y)+4*x,(H,W))
    base=np.dstack([r,g,b]).astype(np.float32)+lift
    yy,xx=np.mgrid[0:H,0:W]
    d=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
    return np.clip(base*np.clip(1.12-0.46*d**1.7,0,1.3)[:,:,None],0,255)

def scrim(W,H,frm=0.62):
    s=Image.new('RGBA',(W,H),(0,0,0,0)); a=np.zeros((H,W),np.float32)
    a[int(H*frm):]=np.linspace(0,205,H-int(H*frm))[:,None]
    s.putalpha(Image.fromarray(a.astype(np.uint8),'L')); return s

def build(fmt):
    W,H,k,side=fmt['W'],fmt['H'],fmt['k'],fmt['side']
    shoe=cutout(V['src'],V.get('gain',1.0)); SW,SH=shoe.size
    BG=bg(W,H,V['lift']); GRN=grain(W,H); SC=scrim(W,H)
    fd=f"fr_{fmt['name']}"; shutil.rmtree(fd,ignore_errors=True); os.makedirs(fd)
    cache={}
    def sh(s,rot):
        key=(round(s,3),round(rot,1))
        if key not in cache:
            im=shoe.resize((max(2,int(SW*s)),max(2,int(SH*s))),Image.LANCZOS)
            if abs(rot)>0.05: im=im.rotate(rot,resample=Image.BICUBIC,expand=True)
            cache[key]=im
            if len(cache)>150: cache.pop(next(iter(cache)))
        return cache[key]
    def at(cv,s,cx,cy,rot=0.0,shadow=True):
        im=sh(s,rot); w,h=im.size; px,py=int(cx-w/2),int(cy-h/2)
        if shadow:
            g=Image.new('RGBA',(w,h),(0,0,0,0)); g.paste((0,0,0,150),(0,0),im.getchannel('A'))
            cv.alpha_composite(g.filter(ImageFilter.GaussianBlur(26)),(px+10,py+30))
        cv.alpha_composite(im,(px,py))
    def roi(cv,s,rx,ry,cx,cy,rot=0.0):
        at(cv,s,cx-(rx-0.5)*SW*s,cy-(ry-0.5)*SH*s,rot,shadow=False)

    # ancoraggi: in orizzontale scarpa a sinistra e testo a destra, altrimenti impilati
    TX = W*0.66 if side else W*0.5
    SX = W*0.27 if side else W*0.5
    SY = H*0.50 if side else H*0.34
    BASE = H*0.42 if side else H*0.62
    SS = 1.02*k if side else 0.80*k

    for i in range(N):
        t=i/FPS
        cv=Image.fromarray(np.clip(BG+GRN[i%6][:,:,None]*0.85,0,255).astype(np.uint8),'RGB').convert('RGBA')
        d=ImageDraw.Draw(cv,'RGBA')
        jx=math.sin(t*7.3)*2.2+math.sin(t*17.1)*1.1
        jy=math.cos(t*6.1)*2.0+math.cos(t*13.7)*0.9
        if t<A1:
            p=cl(t/A1)
            at(cv,SS*(1.0+0.10*eo(cl(t/0.42),4)+0.03*p),SX+jx,SY+jy,rot=-4+1.5*p)
            if t>0.34:
                q=eo(cl((t-0.34)/0.16),4); line(d,TX+jx,BASE+jy,"FERMATI",font(ANTON,100*k*(0.82+0.18*q)),track=4)
            if t>0.52:
                q=eo(cl((t-0.52)/0.16),4); line(d,TX+jx,BASE+112*k+jy,"UN SECONDO",font(ANTON,100*k*(0.82+0.18*q)),track=4)
        elif t<B1:
            p=cl((t-A1)/(B1-A1))
            at(cv,SS*(1.05+0.05*p),SX+jx,SY*0.97+jy,rot=-2.5-2*p)
            if t>A1+0.06: line(d,TX+jx,BASE-40*k+jy,"IL PRODOTTO",font(ANTON,86*k),track=3)
            if t>A1+0.30:
                q=eo(cl((t-A1-0.30)/0.14),4)
                band(d,TX+jx,BASE+110*k+jy,"PIÙ VENDUTO",font(ANTON,104*k*(0.86+0.14*q)),padx=32*k,pady=18*k)
            if t>A1+0.62: line(d,TX+jx,BASE+218*k+jy,"DEL WEB",font(ANTON,86*k),track=3)
        elif t<C1:
            p=cl((t-B1)/(C1-B1))
            roi(cv,3.05*k*1.15,0.46+0.05*p,0.885,W/2+jx*2,H*0.42+jy*2,rot=-2)
            cv.alpha_composite(SC)
            band(d,W/2+jx,H*0.80+jy,V['label'],font(ARCH,46*k),padx=32*k,pady=18*k)
            line(d,W/2+jx,H*0.875+jy,V['sub'],font(ARCH,30*k),fill=SMOKE,off=3)
        elif t<D1:
            p=cl((t-C1)/(D1-C1))
            roi(cv,2.60*k*1.15,0.30,0.52-0.05*p,W/2+jx*2,H*0.40+jy*2,rot=-2)
            cv.alpha_composite(SC)
            band(d,W/2+jx,H*0.80+jy,"EFFETTO CAMOSCIO",font(ARCH,44*k),bg=WHITE,fg=DARK,padx=30*k,pady=18*k)
            line(d,W/2+jx,H*0.875+jy,"inserti a contrasto",font(ARCH,30*k),fill=SMOKE,off=3)
        else:
            p=cl((t-E0)/(DUR-E0))
            at(cv,SS*(0.98-0.03*p),SX+jx,SY*0.94+jy,rot=-3)
            f=font(ANTON,88*k)
            line(d,TX+jx,BASE-60*k+jy,"NON LASCIARTELO",f,track=3)
            line(d,TX+jx,BASE+38*k+jy,"SFUGGIRE",f,track=3)
            if t>E0+0.75:
                q=eo(cl((t-E0-0.75)/0.18),4); pulse=1+0.035*math.sin((t-E0-0.75)*9.0)
                x0,y0,x1,y1=band(d,TX+jx,BASE+200*k+jy,"CLICCA QUI",font(ANTON,80*k*(0.8+0.2*q)*pulse),padx=56*k,pady=26*k)
                d.rectangle([x0-9,y0-9,x1+9,y1+9],outline=(228,255,60,95),width=3)
            line(d,TX+jx,BASE+330*k+jy,"BELLAMICA · ISA · TAGLIE 36–41",font(ARCH,30*k),fill=SMOKE,off=3)
            line(d,TX+jx,BASE+420*k+jy,"23,00 €",font(ANTON,76*k),track=2)
        cv.convert('RGB').save(f'{fd}/f{i:04d}.jpg',quality=95)
    out=f"spot-isa-grigio-{fmt['name']}.mp4"
    subprocess.run([FF,'-y','-loglevel','error','-framerate','30','-i',f'{fd}/f%04d.jpg','-i','out/mix.wav',
      '-c:v','libx264','-profile:v','high','-pix_fmt','yuv420p','-crf','19','-preset','medium',
      '-c:a','aac','-b:a','192k','-ar','44100','-movflags','+faststart','-shortest',out],check=True)
    shutil.rmtree(fd,ignore_errors=True); print('OK',out,flush=True)

for f in FORMATS: build(f)
