from u6 import U6
from futek import getFutekForce
import numpy as np

Ch_futek = [3,4]
ChOpt_futek = 0b00000000

lj = U6()
lj.getCalibrationData()
lj.streamConfig(NumChannels=2, ChannelNumbers= [3,4], ChannelOptions=[ChOpt_futek, ChOpt_futek], 
                ResolutionIndex=8, ScanFrequency= 44, InternalStreamClockFrequency=1, SettlingFactor=0,
                )
try:
    lj.streamStart()
except:
    lj.streamStop()
    lj.streamStart()
    
i = 0
print("AIN%i" %Ch_futek[0])
for r in lj.streamData():
    if r is not None:
        AIN0 = r["AIN%i" %Ch_futek[0]]
        AIN1 = r["AIN%i" %Ch_futek[1]]
        print(np.mean(AIN0))
        print(np.mean(AIN1))
        u=np.mean(np.array(AIN1[0:10]) - np.array(AIN0[0:10]))
        F_futek = getFutekForce(u)
        print(u)
        print("")

        i += 1
        if i > 100:
            lj.streamStop()
            break
