import numpy as np,sys
sr=44100
x=np.fromfile('out.raw',np.float32)
seg=x[int(1.5*sr):int(5.0*sr)]
from scipy import signal
f,t,S=signal.spectrogram(seg,sr,nperseg=8192,noverlap=4096)
def flat(a,b):
    m=(f>=a)&(f<b); P=S[m]+1e-20
    return np.mean(np.exp(np.mean(np.log(P),0))/np.mean(P,0))
tot=S[(f>80)&(f<10000)].sum()
def lv(a,b): return 10*np.log10(S[(f>=a)&(f<b)].sum()/tot)
print("flat 1-2.5k %.2f  2.5-6k %.2f  6-10k %.2f | lvl 100-1k %.1f 1-2.5k %.1f 2.5-6k %.1f 6-10k %.1f"%(flat(1000,2500),flat(2500,6000),flat(6000,10000),lv(100,1000),lv(1000,2500),lv(2500,6000),lv(6000,10000)))
