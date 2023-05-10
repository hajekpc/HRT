from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from u6 import U6
from datetime import datetime
import os

calibration_data0 = [   np.array([0, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]),
                        np.array([-0.00012013985613362963, -0.0003329228642437037, -0.0005608490333823703, -0.0007933885404334814, -0.0010211578983465187, -0.0012503398049180739, -0.0014779138310955554, -0.0017170361346, -0.0019502189497622219, -0.002177925458422222, -0.0024032938345111107])
                    ]
calibration_data0 = [    np.linspace(0, 200, 21),
                        np.array([2.844225805542777e-05, 0.00014534961022150128, 0.00025365125494269947, 0.00037201920887985906, 0.00047609695119499307, 0.0006025771660795876, 0.0007256032552835912,  0.0008311218614998062, 0.0009558651446543998, 0.001067107730627459, 0.0011721131525015416, 0.0012797239721069609, 0.0014142374964736248, 0.0015108148514935138, 0.0016349265229753662, 0.001761584378592751, 0.0018642804707158511, 0.0019872078706759666, 0.002095884534875303, 0.002232095515302568, 0.002336568014825957]),
                        
                        ] # [weights, actual meassured voltages]
def getSample(lj, Ch_futek = 6, n_samples = 4000, config = True):
    ChOpt_futek = 0b10110000 # gain 1000 - range +/- 0.01 V, differential measurement 
    AIN_futek = []
    # for ResolutionIndex 8 and gain > 1000 it need 11.3 ms/channel/scan = 11.3 ms/scan -> 88 Hz scan freq
    if config:
        lj.streamConfig(    NumChannels=1, ChannelNumbers= [Ch_futek], ChannelOptions=[ChOpt_futek], 
                            ResolutionIndex=8, ScanFrequency= 88, InternalStreamClockFrequency=1, SettlingFactor=0,
                        )
    try:
        lj.streamStart()
    except:
        lj.streamStop()
        lj.streamStart()
    
    for r in lj.streamData():
        if r is not None:
            AIN_futek += r["AIN%i" %Ch_futek]
            if len(AIN_futek) >= n_samples:
                lj.streamStop()               
                u_futek = np.mean(np.array(AIN_futek))
                break
    return u_futek

def proceedCalibration(lj, Ch_futek = 6):
    u_calib = []
    weight = []
    getSample(lj)
    print("Type \x1B[3mstop\x1B[0m to end calibration.")
    while True:
        w = input("Weight [g]: ")
        if w == "stop":
            break

        weight.append(int(w))
        u_calib.append(getSample(lj, config= False))

    print(weight)
    print(u_calib)

    pd.DataFrame(np.array([weight,u_calib]).transpose()).to_csv("calibration/Futek_calibration-%s.csv" %datetime.now().strftime("%d-%m-%Y-%H-%M-%S"),index_label="i", header=["Weight [g]","voltage [V]"])


def getLastCalibration(appendix= "Futek"):
    lastDatetime = datetime(1,1,1)    
    for file in os.listdir("calibration/"):
        if file.startswith(appendix):
            currentDatetime = datetime.strptime(file[-23:-4], "%d-%m-%Y-%H-%M-%S")
            if currentDatetime > lastDatetime:
                lastDatetime = currentDatetime
                lastFile = file
    return lastFile


def plotCalibration(CalibrationFile = None):
    if CalibrationFile is None:
        CalibrationFile = "calibration/" + getLastCalibration()
    
    # TODO raed file + read last calibration file when None
    calibrationData = pd.read_csv(CalibrationFile)

    weight = calibrationData["W"]
    voltage = calibrationData["V"]
    plt.plot(weight, voltage*1000, "x")

    calib_coef = np.polyfit(weight, voltage, 1)
    plt.plot([0, 200], np.polyval(calib_coef, [0, 200])*1000)
    plt.xlabel("Hmotnost závaží [g]")
    plt.ylabel("Výstupní napětí [mV]")

    # calib_coef = np.polyfit(calib, weight , 1) # g/V
    # print(calib_coef)
    plt.show()

def getFutekForce(U, calib_coef = [-8.70612452e+04, -9.26333650e+00]):
    g = 0.00980665 # N/g
    return g*(np.polyval(calib_coef, U))

def measLoop(): # this is just to try out reading
    lj = U6()
    n = 100
    GI = 4
    U_calib = []
    while True:
        U0 = 0
        U1 = 0

        
        for i in range(n):
            U1  += lj.getAIN(7, gainIndex=GI, resolutionIndex=8, settlingFactor= 0)
            U0  += lj.getAIN(6, gainIndex=GI, resolutionIndex=8, settlingFactor= 0)
            # print(lj.getAIN(3, gainIndex=2, resolutionIndex=8, settlingFactor= 0))
            
        U0 = U0/n
        U1 = U1/n
        print(U0)
        print(U1)
        F = getFutekForce(U1 - U0)
        print("Force =", F,"N")

if __name__ == '__main__':

# proceedCalibration(U6())
# measLoop()
    plotCalibration()
# getLastCalibration()