# Compare Doorn a la vraie Thorn de la video de reference (tools/video_reference.json).
# Prerequis (non inclus dans le depot) :
#   - une guitare DI 48 kHz mono : data/ts9_test1_in_FP32.wav de github.com/GuitarML/GuitarLSTM, resample a 48 kHz
#     et transpose de 5 demi-tons vers le bas (accordage B de la video)
#   - deux reponses de baffle 4x12 SM57 de github.com/orodamaral/Speaker-Cabinets-IRs :
#     JSX/C_Bogner greenback.wav et Kalthallen/001a-SM57-V30-4x12.wav (convertis en 48 kHz)
#   - tools/process.cpp compile : g++ -O2 -std=c++17 tools/process.cpp -o process
# Usage : python3 tools/video_match.py process di_B_48k.wav greenback_48k.wav v30_48k.wav
import json, sys, subprocess, numpy as np
from scipy.io import wavfile; from scipy import signal
R = json.load(open(__file__.replace('video_match.py', 'video_reference.json'))); CTR = np.array(R['ctr'], float)
SET = {'A':[3.8,2,6,6.5,5,8,1,2,0], 'B':[3.8,2,6,6.5,5,8,1,2,1], 'Z':[4.2,2,8,3.3,6.5,6.5,1,2,0], 'Y':[3.3,2,7.5,3.5,6.5,6.5,1,2,1]}
EV = slice(4, 25)
def bands(y):
    N=8192; sr=48000; w=np.hanning(N); P=np.zeros(N//2); n=0
    bl=[y[o:o+N] for o in range(0,len(y)-N,N)]; e=np.array([(b**2).mean() for b in bl])
    for b,eb in zip(bl,e):
        if eb>=e.max()*1e-3: P+=np.abs(np.fft.rfft(b*w)[:N//2])**2; n+=1
    return np.array([10*np.log10(P[int(np.ceil(f/2**(1/6)*N/sr)):int(f*2**(1/6)*N/sr)+1].mean()/n+1e-20) for f in CTR])
def ir(p):
    sr,h=wavfile.read(p); h=h.astype(float); h=h[:,0] if h.ndim>1 else h; return h/np.sqrt((h**2).sum())
exe, dip = sys.argv[1], sys.argv[2]; irs = [ir(p) for p in sys.argv[3:]]
print('band   '+' '.join(f'{int(c):>5}' for c in CTR[EV]))
for k,a in SET.items():
    subprocess.run([exe,dip,'vm_out.wav']+[str(v) for v in a],check=True); _,y=wavfile.read('vm_out.wav'); y=y/32768.
    d=np.mean([bands(signal.fftconvolve(y,h)[:len(y)]) for h in irs],axis=0)-np.array(R[k]); d-=d[EV].mean()
    print(k,'    ',' '.join(f'{v:5.1f}' for v in d[EV]),' rms %.2f dB'%np.sqrt((d[EV]**2).mean()))
