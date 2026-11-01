"""Generate an original, short bark-like sound with no external audio file."""
import math,random,struct,wave
from pathlib import Path

def generate_bark(path):
    path=Path(path)
    if path.exists():return path
    rate=22050
    rand=random.Random(88)
    samples=[]
    for i in range(int(rate*0.52)):
        t=i/rate
        start=0.03 if t<0.23 else 0.29
        x=t-start
        if x<0 or x>0.18: val=0
        else:
            env=min(1,x/0.012)*math.exp(-x*18)
            freq=240-470*x
            val=(0.55*math.sin(2*math.pi*freq*x)+0.28*math.sin(2*math.pi*2.05*freq*x)+0.22*(2*rand.random()-1))*env
        samples.append(struct.pack("<h",int(max(-1,min(1,val))*23500)))
    with wave.open(str(path),"wb") as file:
        file.setnchannels(1);file.setsampwidth(2);file.setframerate(rate)
        file.writeframes(b"".join(samples))
    return path
