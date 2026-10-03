"""Physics-only passive brake capacity; never an actor/control input.

The startup and groove locations describe the physical rail. A zero-velocity
solver drive opposes motion up to this capacity. No blade position is commanded.
"""
import numpy as np


def brake_capacity_numpy(travel, time, amplitude, detent, frequency, phase, profile):
    angle=frequency*time+phase
    factor=.25+.75*np.sin(angle)**2
    factor=np.where(profile==0,1.,factor)
    factor=np.where(profile==2,.25+.75*np.abs(2*np.remainder(angle/(2*np.pi),1)-1),factor)
    factor=np.where(profile==3,np.where(np.sin(angle)>.5,1.,.25),factor)
    startup=detent*np.sin(np.clip(travel/.004,0,1)*np.pi)*((travel>=0)&(travel<=.004))
    x=(travel-.021)/.0015
    groove=detent*np.pi*.5*np.abs(np.sin(np.pi*x))*(np.abs(x)<1)
    return np.maximum(0.,amplitude*factor+startup+groove)
