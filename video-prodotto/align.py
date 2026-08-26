import numpy as np, wave, json, subprocess, os, imageio_ffmpeg
FF=imageio_ffmpeg.get_ffmpeg_exe(); SR=44100
os.makedirs('warp', exist_ok=True)

def rd(p):
    w=wave.open(p); a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768.0
    return a, w.getframerate()
def wr(p,a,sr=SR):
    w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(a,-1,1)*32767).astype(np.int16).tobytes()); w.close()

def atempo_chain(f):
    """atempo accetta 0.5-2.0: concatena piu' stadi per fattori estremi"""
    out=[]
    while f<0.5: out.append(0.5); f/=0.5
    while f>2.0: out.append(2.0); f/=2.0
    out.append(f); return out

def warp(src, dst, factor):
    ch=atempo_chain(factor)
    filt=','.join(f'atempo={c:.6f}' for c in ch)
    subprocess.run([FF,'-y','-loglevel','error','-i',src,'-filter:a',filt,'-ar',str(SR),'-ac','1',dst],check=True)

her=[(w,float(s),float(e)) for w,s,e in json.load(open('gen_words.json'))]
import os
CORR=json.load(open('corr.json')) if os.path.exists('corr.json') else [0.0]*4
mine=json.load(open('my_words.json'))
groups=[(0,4),(4,13),(13,19),(19,24)]

total=np.zeros(int(SR*10.04),np.float32)
for p,(g0,g1) in enumerate(groups):
    a,sr=rd(f'out/nat{p}.wav')
    if sr!=SR:
        subprocess.run([FF,'-y','-loglevel','error','-i',f'out/nat{p}.wav','-ar',str(SR),'-ac','1',f'warp/p{p}.wav'],check=True)
        a,sr=rd(f'warp/p{p}.wav')
    mw=mine[p]; hw=her[g0:g1]
    assert len(mw)==len(hw), (len(mw),len(hw))
    # punti di taglio sugli attacchi di parola, piu' la coda
    mb=[w[1] for w in mw]+[len(a)/SR]
    hb=[w[1] for w in hw]+[hw[-1][2]]
    hb=[t-hb[0] for t in hb]                       # relativi all'attacco della frase
    pieces=[]
    for j in range(len(mb)-1):
        ms,me=mb[j],mb[j+1]; td=hb[j+1]-hb[j]
        chunk=a[int(ms*SR):int(me*SR)]
        if len(chunk)<64 or td<=0.01: pieces.append(chunk); continue
        wr(f'warp/c.wav',chunk)
        warp('warp/c.wav','warp/cw.wav', (len(chunk)/SR)/td)
        cw,_=rd('warp/cw.wav'); pieces.append(cw)
    # ricomposizione con dissolvenze brevi ai giunti
    xf=int(0.006*SR); out=pieces[0]
    for c in pieces[1:]:
        if len(out)>xf and len(c)>xf:
            head=out[-xf:]*np.linspace(1,0,xf)+c[:xf]*np.linspace(0,1,xf)
            out=np.concatenate([out[:-xf],head,c[xf:]])
        else: out=np.concatenate([out,c])
    # la frase warpata parte dalla prima parola: la durata totale viene forzata
    # sulla campata di lei, per annullare l'accorciamento dei giunti in dissolvenza
    span=her[g1-1][2]-her[g0][1]
    if span>0.05 and len(out)>SR*0.05:
        wr('warp/ph.wav', out)
        warp('warp/ph.wav','warp/phw.wav',(len(out)/SR)/span)
        out=rd('warp/phw.wav')[0]
    # correzione per frase, misurata e reiniettata (vedi corr.json)
    start=max(0,int((her[g0][1]+CORR[p])*SR))
    e=min(len(total),start+len(out)); out=out[:e-start].copy()
    f=int(0.008*SR)
    if len(out)>2*f: out[:f]*=np.linspace(0,1,f); out[-f:]*=np.linspace(1,0,f)
    total[start:e]+=out
    print(f'frase {p}: {len(out)/SR:.2f}s posata a {start/SR:.2f}s')
wr('out/voce_allineata.wav', total/max(1e-9,np.abs(total).max())*0.90)
print('ok')
