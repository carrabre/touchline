"""Sunday Rise: original instrumental composition and synthesizer, dedicated to CC0.
Four-chord D-major progression, pulse, bass and rising arpeggios at 108 BPM.
No samples or external copyrighted melodies. Not AI service output.
"""
import numpy as np,wave
RATE=44100
def compose(path,seconds=32):
 t=np.arange(int(RATE*seconds))/RATE;y=np.zeros_like(t);beat=60/108
 chords=[(50,54,57),(57,61,64),(59,62,66),(55,59,62)]
 def hz(n):return 440*2**((n-69)/12)
 for bar in range(int(seconds/(beat*4))+1):
  start=bar*beat*4;notes=chords[bar%4]
  local=t-start;mask=(local>=0)&(local<beat*4);v=local[mask]
  env=np.minimum(v/.15,1)*np.minimum((beat*4-v)/.3,1)
  for n in notes:y[mask]+=.07*np.sin(2*np.pi*hz(n+12)*v)*env
  y[mask]+=.12*np.sin(2*np.pi*hz(notes[0]-12)*v)*env
  for step in range(8):
   local=t-(start+step*beat/2);mask=(local>=0)&(local<beat*.7);v=local[mask];env=np.exp(-v*9)*np.minimum(v/.015,1)
   n=notes[step%3]+24+(12 if step==7 else 0);y[mask]+=.11*np.sin(2*np.pi*hz(n)*v)*env
  for step in range(4):
   local=t-(start+step*beat);mask=(local>=0)&(local<.22);v=local[mask]
   phase=2*np.pi*(48*v+45*(1-np.exp(-v*22))/22);y[mask]+=.13*np.sin(phase)*np.exp(-v*22)
 y=np.tanh(y)*.8;fade=np.minimum(t/1,1)*np.minimum((seconds-t)/1,1);y*=np.maximum(0,fade)
 with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(np.repeat((y*32767).astype('<i2')[:,None],2,axis=1).tobytes())
