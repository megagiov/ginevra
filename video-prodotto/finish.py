import numpy as np, wave
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768.0
def wr(p,a):
    w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(a,-1,1)*32767).astype(np.int16).tobytes()); w.close()

orig=rd('orig_44k.wav'); voce=rd('out/voce_allineata.wav')
N=min(len(orig),len(voce)); orig,voce=orig[:N],voce[:N]

# --- 1. stima del rumore d'ambiente del negozio dai fotogrammi piu' silenziosi ---
F=1024; H=512
frames=np.array([orig[i:i+F] for i in range(0,len(orig)-F,H)])
en=(frames**2).mean(1)
quiet=frames[en<=np.quantile(en,0.10)]           # il 10% piu' silenzioso = fondo sala
spec=np.abs(np.fft.rfft(quiet*np.hanning(F),axis=1)).mean(0)
rng=np.random.default_rng(11)
noise=rng.normal(0,1,N)
Nf=np.fft.rfft(noise)
env=np.interp(np.linspace(0,1,len(Nf)), np.linspace(0,1,len(spec)), spec)
bed=np.fft.irfft(Nf*env/ (np.abs(env).mean()+1e-9), n=N).astype(np.float32)
bed*= np.sqrt(en[en<=np.quantile(en,0.10)].mean())/ (bed.std()+1e-9)
print(f'fondo sala ricostruito, livello {20*np.log10(bed.std()+1e-9):.1f} dBFS')

# --- 2. trattamento voce: passa-alto, taglio degli acuti da microfono di telefono ---
v=sosfilt(butter(2, 85/(SR/2), 'hp', output='sos'), voce)
v=sosfilt(butter(2, 9000/(SR/2), 'lp', output='sos'), v)*0.75 + v*0.25

# --- 3. compressione morbida ---
env_v=np.abs(v); a,r=int(0.005*SR),int(0.08*SR)
sm=np.copy(env_v)
for i in range(1,len(sm)):
    k=1/a if sm[i-1]<env_v[i] else 1/r
    sm[i]=sm[i-1]+(env_v[i]-sm[i-1])*k
thr,ratio=0.16,3.2
gain=np.where(sm>thr,(thr+(sm-thr)/ratio)/(sm+1e-9),1.0)
v=v*gain*1.5

# --- 4. riverbero corto della stanza ---
ir_len=int(0.22*SR); t=np.arange(ir_len)/SR
ir=rng.normal(0,1,ir_len)*np.exp(-t/0.055); ir[0]=1.0
ir=sosfilt(butter(2,5200/(SR/2),'lp',output='sos'),ir); ir/=np.abs(ir).sum()/2.2
wet=fftconvolve(v,ir)[:N]
v=v*0.90+wet*0.11

# --- 5. mix ---
v/=max(1e-9,np.abs(v).max())/0.88
mix=v+bed*1.25
f=int(0.15*SR); mix[-f:]*=np.linspace(1,0,f)
mix=np.tanh(mix*1.05)*0.95
wr('out/mix_finale.wav', mix)
print(f'mix finale: picco {np.abs(mix).max():.3f}, RMS {20*np.log10(mix.std()):.1f} dBFS')
