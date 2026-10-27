import numpy as np, wave, sys, subprocess
from scipy import signal
S=sys.argv[1]; sr=48000
def rd(p):
    w=wave.open(p); return np.frombuffer(w.readframes(w.getnframes()),np.int16)/32768.
def wr(p,x):
    w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
def di():
    rng=np.random.default_rng(1); out=np.zeros(int(sr*10))
    def pluck(f,t0,dur,amp,mute):
        N=int(sr/f); buf=rng.uniform(-1,1,N); b,a=signal.butter(1, 3500 if not mute else 1200, fs=sr); buf=signal.lfilter(b,a,buf)
        i0=int(t0*sr); n=int(dur*sr); y=np.zeros(n); p=0; last=0.
        loss=0.994 if mute else 0.9985
        for i in range(n):
            s=buf[p]; nx=loss*0.5*(s+buf[(p+1)%N]); buf[p]=nx; p=(p+1)%N; y[i]=s
        env=np.ones(n); 
        if mute: env=np.exp(-np.arange(n)/sr*9)
        out[i0:i0+n]+=amp*y*env
    B1,Fs2,B2=61.735,92.5,123.47
    t=0.0
    for bar in range(4):
        for k in range(6):  # palm mutes en croches
            for f in (B1,Fs2,B2): pluck(f,t,0.24,0.20,True)
            t+=0.25
        for f in (B1,Fs2,B2,185.0): pluck(f,t,1.0,0.17,False)
        t+=1.0
    return out[:int(t*sr)+sr//2]
def cab(x):
    sos=np.vstack([signal.butter(2,80,'hp',fs=sr,output='sos'), signal.butter(4,4800,'lp',fs=sr,output='sos')])
    return signal.sosfilt(sos,x)
bands=[40,63,100,160,250,400,630,1000,1600,2500,4000,6300,10000]
def spec(x):
    n=8192; win=np.hanning(n); P=np.zeros(n//2+1); c=0
    for i in range(0,len(x)-n,n//2):
        s=x[i:i+n]
        if np.sqrt((s**2).mean())<0.003: continue
        P+=np.abs(np.fft.rfft(s*win))**2; c+=1
    P/=max(c,1); f=np.fft.rfftfreq(n,1/sr)
    v=np.array([10*np.log10(P[(f>=a)&(f<b)].mean()+1e-20) for a,b in zip(bands[:-1],bands[1:])])
    return v-v.max()
def env_spread(x):
    seg=int(sr*0.25); e=np.array([20*np.log10(np.sqrt((x[i:i+seg]**2).mean())+1e-9) for i in range(0,len(x)-seg,seg)])
    e=e[e>e.max()-30]; return e.std()
if __name__=='__main__':
    import os
    if not os.path.exists(S+'/ref/di.wav'): wr(S+'/ref/di.wav', di())
    ref=rd(S+'/ref/ref.wav'); r=spec(ref)
    args=sys.argv[2:]
    subprocess.run([S+'/process',S+'/ref/di.wav',S+'/ref/out.wav']+args,check=True)
    y=cab(rd(S+'/ref/out.wav')); p=spec(y)
    print('band  ', ' '.join(f'{b:>5}' for b in bands[:-1]))
    print('ref   ', ' '.join(f'{v:5.0f}' for v in r))
    print('doorn ', ' '.join(f'{v:5.0f}' for v in p))
    print('diff  ', ' '.join(f'{v:5.0f}' for v in p-r))
    print('env spread ref %.2f dB  doorn %.2f dB' % (env_spread(ref), env_spread(y)))
