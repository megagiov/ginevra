import numpy as np, wave, json
SR=44100; END=10.04; TH=0.30          # soglia di scarto oltre la quale si apre un nuovo gruppo
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768.0
el=rd('el_it44.wav')
E=[(w,s,e) for w,s,e in json.load(open('el_words.json'))]
H=[(w,s,e) for w,s,e in json.load(open('gen_words.json'))]
assert len(E)==len(H)

# raggruppa: si resta contigui finche' la deriva accumulata sta sotto la soglia
runs=[]; start=0
for i in range(1,len(E)):
    drift=(H[i][1]-H[start][1])-(E[i][1]-E[start][1])
    if abs(drift)>TH:
        runs.append((start,i-1)); start=i
runs.append((start,len(E)-1))
import os
OFF=json.load(open('goff.json')) if os.path.exists('goff.json') else [0.0]*len(runs)
if len(OFF)!=len(runs): OFF=[0.0]*len(runs)
json.dump(runs, open('runs.json','w'))
print(f"{len(runs)} gruppi contigui (dentro ciascuno l'audio non viene toccato):")

total=np.zeros(int(SR*END),np.float32); prev_end=0.0
for gi,(a,b) in enumerate(runs):
    s_el=E[a][1]-0.035; e_el=E[b][2]+0.045        # un filo di respiro ai bordi
    chunk=el[max(0,int(s_el*SR)):min(len(el),int(e_el*SR))].copy()
    d=len(chunk)/SR
    st=max(H[a][1]-0.035+OFF[gi], prev_end+0.02)
    if st+d>END: st=max(0,END-d)
    s=int(st*SR); e=min(len(total),s+len(chunk)); chunk=chunk[:e-s]
    f=int(0.010*SR)
    if len(chunk)>2*f: chunk[:f]*=np.linspace(0,1,f); chunk[-f:]*=np.linspace(1,0,f)
    total[s:e]+=chunk
    words=" ".join(w for w,_,_ in E[a:b+1])
    print(f"  [{st:5.2f}-{st+d:5.2f}] {words[:46]:48s} pausa prima {st-prev_end if prev_end else 0:.2f}s")
    prev_end=st+d
total/=max(1e-9,np.abs(total).max())/0.90
w=wave.open('out/voce_allineata.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(total,-1,1)*32767).astype(np.int16).tobytes()); w.close()
