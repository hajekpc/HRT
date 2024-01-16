from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from u6 import U6, DAC0_8, DAC1_8
from datetime import datetime
from scipy.stats import linregress
from threading import Thread
from time import sleep
import os, json, argparse

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
def measLoop(lj, Ch_futek = 6, run = [True]):
    ChOpt_futek = 0b10110000 # gain 1000 - range +/- 0.01 V, differential measurement 
    AIN_futek = []
    # for ResolutionIndex 8 and gain > 1000 it need 11.3 ms/channel/scan = 11.3 ms/scan -> 88 Hz scan freq
    
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
            AIN_futek = np.mean(r["AIN%i" %Ch_futek])
            print(AIN_futek)
        if not run[0]:
            lj.streamStop()
            return
         
def measStart(Ch = 10, DAC = 1, U = 5):
    lj = U6()
    lj.getCalibrationData()

    lj.getFeedback(DAC1_8(lj.voltageToDACBits(U, dacNumber = DAC, is16Bits = False))) # Set DAC0 to 1.5 V
    run = [True]
    thread = Thread(target=measLoop, args= [lj,Ch,run])
    thread.start()
    state = "init"
    while state != "stop":
        state = input("...: ")
    run[0] = False

def proceedCalibration(lj, prefix = "Futek", Ch_futek = 6):
    u_calib = []
    weight = []
    getSample(lj, Ch_futek=Ch_futek, n_samples=500)
    lj.getFeedback(DAC0_8(lj.voltageToDACBits(5, dacNumber = 0, is16Bits = False))) # Set DAC0 to 5 V
    lj.getFeedback(DAC1_8(lj.voltageToDACBits(5, dacNumber = 1, is16Bits = False))) # Set DAC1 to 5 V
    sleep(1)

    print("Type \x1B[3mstop\x1B[0m to quit the calibration.")
    while True:
        w = input("Weight [g]: ")
        if w == "stop":
            break

        weight.append(int(w))
        u = getSample(lj, Ch_futek=Ch_futek, n_samples=500, config= False)
        print(u, "V")
        u_calib.append(u)

    print(weight)
    print(u_calib)

    pd.DataFrame(np.array([weight,u_calib]).transpose()).to_csv("calibration/%s-%s.csv" %(prefix, datetime.now().strftime("%d-%m-%Y-%H-%M-%S")),index_label="i", header=["W","V"])


def getLastCalibration(prefix= "Futek"):
    lastDatetime = datetime(1,1,1)    
    for file in os.listdir("calibration/"):
        if file.startswith(prefix):
            currentDatetime = datetime.strptime(file[-23:-4], "%d-%m-%Y-%H-%M-%S")
            if currentDatetime > lastDatetime:
                lastDatetime = currentDatetime
                lastFile = file
    return "calibration/" + lastFile


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

def readCalibration(filename = None, prefix= "Futek"):
    if filename is None:
        filename = getLastCalibration(prefix)
    try:
        DataFrame = pd.read_csv(filename)
        return DataFrame
    except:
        print("File",filename,"does not exist.")

def saveCalibrationParameters(filename = None, prefix= "Futek"):
    fCfg = open("cfg.json","r")
    Cfg = json.loads(fCfg.read())
    fCfg.close()

    calib = readCalibration(filename, prefix)
    


    slope, intercept, r_value, p_value, std_err  = linregress(calib["W"], calib["V"])
    R2 = r_value**2
    if R2 < 0.9:
        print("R^2 is too low!\nThere could be some outlayers in the data caused by DAQ card unstability... Try to edit V_limit in cfg.json.")
        return 1
    else:
        print("Saving fit parameters of %s to cfg.json" %prefix)
        g = 0.00980665 # N/g
        Cfg[prefix] = [-g*intercept/slope, g/slope]
        fCfg = open("cfg.json","w")
        fCfg.write(json.dumps(Cfg, indent= 4))
        fCfg.close()
    
    err = np.sqrt(np.sum(np.abs(slope*calib["W"] + intercept - calib["V"])**2)/(len(calib["W"])-1))

    W0, W1 = np.min(calib["W"])-5, np.max(calib["W"]) + 5
    u0, u1 = W0*slope + intercept, W1*slope + intercept
    plt.plot(calib["W"],calib["V"]*1000, ".k", markersize=8)
    plt.plot([W0, W1], [u0*1000, u1*1000], "r")
    plt.plot([W0, W1], [(u0 + err)*1000, (u1 + err)*1000], "--r")
    plt.legend(["Data", "Fit", "Error"])
    plt.plot([W0, W1], [(u0 - err)*1000, (u1 - err)*1000], "--r")
    plt.plot(calib["W"],calib["V"]*1000, ".k", markersize=8)
    plt.grid()
    plt.xlabel("Weight [g]")
    plt.ylabel("Futek votage [mV]")
    plt.show()

if __name__ == '__main__':
    # parse position argument
    parser = argparse.ArgumentParser()
    parser.add_argument('pos', help='Winder position (L/M/R)')
    args = parser.parse_args()
    arg = (args.pos).lower()

    # settings
    options = "lmr"
    futek_names = ('FutekL', 'FutekM', 'FutekR')
    channels = (6, 8, 10) # LJ analog input channels!

    # check input argument ... must be l/m/r/L/M/R
    if len(arg) > 1 or arg not in options:
        print("Input argument must be one of the followings: l/m/r/L/M/R")
        parser.print_help()
        exit(1)


    futek_name = futek_names[options.find(arg)]
    channel = channels[options.find(arg)]

    # start calibration process
    lj = U6()
    proceedCalibration(lj, futek_name, channel)
    saveCalibrationParameters(prefix= futek_name)
    lj.close()