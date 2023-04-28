from stepper import Stepper
from u6 import U6
import numpy as np
import pandas as pd
from time import sleep
from futek import getFutekForce
from matplotlib import pyplot as plt
from datetime import datetime

def getSample(lj, n_samples = 1000, Ch_tenzo = 4, Ch_futek = 6, config = True):
    # make stream to acquire voltage on tenzometer
    AIN_tenzo = []
    AIN_futek = []
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    ChOpt_futek = 0b10110000
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 22.6ms/scan -> 44 Hz scan freq
    if config:
        lj.streamConfig(    NumChannels=2, ChannelNumbers= [Ch_tenzo, Ch_futek], ChannelOptions=[ChOpt_tenzo, ChOpt_futek], 
                            ResolutionIndex=8, ScanFrequency= 100, InternalStreamClockFrequency=1, SettlingFactor=0,
                        )
    try:
        lj.streamStart()
    except:
        lj.streamStop()
        lj.streamStart()
    
    for r in lj.streamData():
        if r is not None:
            AIN_tenzo += r["AIN%i" %Ch_tenzo]
            AIN_futek += r["AIN%i" %Ch_futek]
            if len(AIN_tenzo) >= n_samples:
                lj.streamStop()               
                u_tenzo = np.mean(np.array(AIN_tenzo)) # this is actual voltage on tenzometer
                F_futek = getFutekForce(np.mean(np.array(AIN_futek)))
                break
    return u_tenzo, F_futek
            



    # return u_tenzo/0.0002


lj = U6()
stpr = Stepper(lj, DO= [7,6,5,4])
F_futek = 0
calib = []
getSample(lj, n_samples=1)
while F_futek < 8:
    stpr.mv(1)
    while stpr.state == "idle":
        sleep(0.2)
        pass
    sleep(2)
    calib.append(getSample(lj,n_samples=200, config= False))
    F_futek = calib[-1][1]
    print("F =", F_futek, "N")
stpr.goto(0)
while stpr.state != "idle":
    sleep(0.2)

stpr.cmd("kill")
print(calib)
calib = np.array(calib)
pd.DataFrame(calib).to_csv("calibration/Tenzo_calibration-%s.csv" %datetime.now().strftime("%d-%m-%Y-%H-%M-%S"),index_label="i", header=["Voltage [V]","Force [N]"])
calib = calib.transpose()

plt.plot(calib[1], calib[0]*1000)
plt.xlabel("Force [N]")
plt.ylabel("Tenzometer voltage [mV]")

plt.show()
    