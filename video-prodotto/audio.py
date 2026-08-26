import numpy as np, wave
SR=22050; DUR=10.0; n=int(SR*DUR)
mix=np.zeros(n,np.float32)

def rd(p):
    w=wave.open(p); a=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768.0
    return a

# --- voce, piazzata sulla timeline ---
starts=[0.30,2.10,4.55,6.95]
for i,st in enumerate(starts):
    a=rd(f'out/seg{i}.wav'); s=int(st*SR); e=min(n,s+len(a))
    # micro fade per evitare click di giunzione
    a=a[:e-s].copy(); f=int(0.008*SR)
    a[:f]*=np.linspace(0,1,f); a[-f:]*=np.linspace(1,0,f)
    mix[s:e]+=a
vo_peak=np.abs(mix).max(); mix/= (vo_peak/0.82)
print(f'voce: picco normalizzato, ultima battuta finisce a {starts[3]+len(rd("out/seg3.wav"))/SR:.2f}s')

# --- kick sugli stacchi di montaggio ---
def kick(dur=0.38,f0=105,f1=44,tau=0.105):
    t=np.arange(int(SR*dur))/SR
    f=f1+(f0-f1)*np.exp(-t/0.035)
    env=np.exp(-t/tau)
    body=np.sin(2*np.pi*np.cumsum(f)/SR)*env
    click=np.random.default_rng(3).normal(0,1,len(t))*np.exp(-t/0.006)*0.28
    return (body+click).astype(np.float32)
K=kick()
for cut in [0.00,2.02,4.45,5.62,6.85,8.60]:
    s=int(cut*SR); e=min(n,s+len(K)); mix[s:e]+=K[:e-s]*0.30

# --- limiter morbido + fade finale ---
mix=np.tanh(mix*1.06)*0.94
fo=int(0.18*SR); mix[-fo:]*=np.linspace(1,0,fo)
mix[:int(0.01*SR)]*=np.linspace(0,1,int(0.01*SR))

st=np.stack([mix,mix],1)
w=wave.open('out/mix.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(st,-1,1)*32767).astype(np.int16).tobytes()); w.close()
print(f'mix: {n/SR:.2f}s  picco {np.abs(mix).max():.3f}')
