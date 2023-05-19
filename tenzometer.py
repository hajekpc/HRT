from stepper import Stepper
from u6 import U6
import numpy as np
import pandas as pd
from time import sleep, time
from matplotlib import pyplot as plt
from datetime import datetime
from realtimeplotter import calibPlotter
from math import floor
from threading import Thread
from queue import Queue
from scipy.stats import linregress
import csv, json, os
fCalib = open("calib.json","r")
calib = json.loads(fCalib.read())
fCalib.close()
p = calib["FutekL"]
print(p)
def getFutekForce(u):
    global p
    return p[1]*u + p[0]

def getSample(lj, T0 = None, n_samples = 1000, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    # make stream to acquire voltage on tenzometer
    AIN_tenzo = []
    AIN_comptenzo = []
    AIN_futek = []
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    ChOpt_futek = 0b10110000
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 22.6ms/scan -> 44 Hz scan freq
    
    try:
        lj.streamStart()
    except:
        lj.streamStop()
        lj.streamStart()
    
    if T0 is not None:
        T1 = time() - T0
    for r in lj.streamData():
        if r is not None:
            AIN_tenzo += r["AIN%i" %Ch_tenzo]
            AIN_comptenzo += r["AIN%i" %Ch_comptenzo]
            AIN_futek += r["AIN%i" %Ch_futek]
            if len(AIN_tenzo) >= n_samples:
                if T0 is not None:
                    T2 = time() - T0
                lj.streamStop()    
                # print("tenoz:", np.mean(np.array(AIN_tenzo)), "comepen:", np.mean(np.array(AIN_comptenzo)), end="\n\n")
                u_tenzo = np.mean(np.array(AIN_tenzo)) - np.mean(np.array(AIN_comptenzo)) # this is actual voltage on tenzometer minus compensation tenzometer voltage
                F_futek = getFutekForce(np.mean(np.array(AIN_futek)))
                break
    
    if T0 is not None:
        return [F_futek, u_tenzo, T1, T2]
    else:
        return [F_futek, u_tenzo]

def initCalibration(lj, stpr, calib, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6, F_default = 0.5):
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    ChOpt_futek = 0b10110000 # gain 1000 -> range ~ +/- 0.01 V
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 33.9ms/scan -> 29 Hz scan freq
    lj.streamConfig(    NumChannels=3, ChannelNumbers= [Ch_comptenzo, Ch_tenzo, Ch_futek], ChannelOptions=[ChOpt_tenzo, ChOpt_tenzo, ChOpt_futek], 
                        ResolutionIndex=8, ScanFrequency= 27, InternalStreamClockFrequency=1, SettlingFactor=0,
                        )
    F_futek, u_tenzo = getSample(lj, n_samples=500, Ch_tenzo= Ch_tenzo)
    calib.writerow([F_futek, u_tenzo, 0, 0, 0, "init", 0])
    print("\n")
    print("F = %2.4f N" %F_futek, end="\r")
    if F_futek > F_default:
        while F_futek > F_default:
            stpr.mv(-5)
            sleep(0.2)
            F_futek = getSample(lj, n_samples= 20, Ch_tenzo= Ch_tenzo)[0]
            print("F = %2.4f N" %F_futek, end="\r")

    elif F_futek < F_default:
        while F_futek < F_default:
            stpr.mv(5)
            sleep(0.2)
            F_futek = getSample(lj, n_samples= 20, Ch_tenzo= Ch_tenzo)[0]
            print("F = %2.4f N" %F_futek, end="\r")
    sleep(2)

def DriftTo(lj, stpr, plotter, calib, F, F_offset = 0, dF_min = 0.005, T_max = 180, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    plotter.newT()
    state = None
    T0 = time()
    dF = []
    sleep(1)
    lj.streamStart()
    for r in lj.streamData():
        T = time() - T0
        # print("T =",T,"s")
        if r is not None:
            u_tenzo = np.mean(np.array(r["AIN%i" %Ch_tenzo])) # + np.mean(np.array(r["AIN%i" %Ch_comptenzo]))
            F_futek = getFutekForce(np.mean(np.array(r["AIN%i" %Ch_futek])))
            calib.writerow([F_futek, u_tenzo, T, 0, stpr.x_cur, "drift", F])
            plotter.addT(T, F_futek, stpr.x_cur)

            if state is None:
                # first iteration
                direction = np.sign(F - F_futek)
                state = "moving"

            if state == "moving":
                if direction*F_futek > direction*(F - F_offset):
                    state = "relax"
                if direction*F_futek > direction*F:
                    stpr.mv(direction*1)
                else:
                    stpr.mv(direction*1)


            if state == "relax":

                dF.append((F_futek - Fp)/(T - Tp)) # time derivative of the force
                if len(dF) > 5:
                    dF.pop(0)
                    # keep last 5 values only
                if (T > T_max) or all(np.abs(dF) < np.array(dF_min)):
                    lj.streamStop()
                    return
            Tp = T
            Fp = F_futek

def rampUpAndDown(lj, stpr, calib, plotter, T0 = time(), F_bot = 1, F_top = 5, nF_points = 9, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    F_points = np.linspace(F_bot, F_top, nF_points)
    F_offset = 0 # can compensate overshooting
    sleep(1)
    # ramping up
    plotter.new()
    for F in F_points:
        DriftTo(lj, stpr, plotter, calib, F, F_offset= F_offset, Ch_tenzo= Ch_tenzo)
        sample = getSample(lj, T0, n_samples= 200, Ch_tenzo= Ch_tenzo)
        plotter.add(sample[0], sample[1])
        calib.writerow(sample + [stpr.x_cur, "up", F])

        F_futek = sample[0]
        print("F = %2.4f N" %F_futek, end="\r")
    plotter.clearT()
    
    stpr.mv(+5)
    # ramping down
    plotter.new()
    for F in np.flip(F_points)[1:]:
        DriftTo(lj, stpr, plotter, calib, F, F_offset= F_offset, Ch_tenzo= Ch_tenzo)
        sample = getSample(lj, T0, n_samples= 200, Ch_tenzo= Ch_tenzo)
        plotter.add(sample[0], sample[1])
        calib.writerow(sample + [stpr.x_cur, "down", F])
        F_futek = sample[0]
        print("F = %2.4f N" %F_futek, end="\r")
    plotter.clearT()


    stpr.goto(0)
    sleep(1)


def doCalibration(lj, stpr, outFilePrefix = "Tenzo", iterations = 1, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    plotter = calibPlotter()
    outFile = open("calibration/%s-%s.csv" %(outFilePrefix, datetime.now().strftime("%d-%m-%Y-%H-%M-%S")), "w")
    calib = csv.writer(outFile)
    header = ["F", "V", "T1", "T2", "x", "Status", "F_set"]
    calib.writerow(header)
    initCalibration(lj, stpr, Ch_tenzo=Ch_tenzo, calib= calib)
    T0 = time()

    for i in range(iterations):
        rampUpAndDown(lj, stpr, calib, plotter, Ch_tenzo=Ch_tenzo)

    outFile.close()

    stpr.goto(-5)
    sleep(2)
    stpr.cmd("kill")
    plotter.end()

def getTimeBehavior(outFilePrefix = "Timebehavior", Ch = 0):
    lj = U6()
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 33.9ms/scan -> 29 Hz scan freq
    lj.streamConfig(    NumChannels=1, ChannelNumbers= [Ch], ChannelOptions=[ChOpt_tenzo], 
                        ResolutionIndex=8, ScanFrequency= 60, InternalStreamClockFrequency=0, SettlingFactor=0,
                        )
    outFileName = "calibration/%s-Ch%i-%s.csv" %(outFilePrefix, Ch, datetime.now().strftime("%d-%m-%Y-%H-%M-%S"))
    outFile = open(outFileName, "w")
    calib = csv.writer(outFile)
    header = ["u", "t"]
    calib.writerow(header)
    try:
        lj.streamStart()
    except:
        lj.streamStop()
        lj.streamStart()
    T0 = time()
    i = 0
    for r in lj.streamData():
        T = time() - T0
        if r is not None:
            for AIN in ["AIN%i" %Ch]:
                for u in r[AIN]:
                    calib.writerow([u, T])


        if T > 20:
            lj.streamStop()
            break
        i += 1
        # if T > 10 and T < 20:
        #     stpr.goto(100000)
        #     if T > 19.9:
        #         stpr.cmd("stop")
    outFile.close()


    data = pd.read_csv(outFileName)
    plt.plot(data["t"], data["u"], "x")
    
    plt.show()
    lj.close()
def getLastCalibration(prefix= "Tenzo"):
    lastDatetime = datetime(1,1,1)
    for file in os.listdir("calibration/"):
        if file.startswith(prefix):
            currentDatetime = datetime.strptime(file[-23:-4], "%d-%m-%Y-%H-%M-%S")
            if currentDatetime > lastDatetime:
                lastDatetime = currentDatetime
                lastFile = file
    print("Last calib file:",lastFile)
    return "calibration/" + lastFile

def readCalibration(filename = None, prefix= "Tenzo"):
    if filename is None:
        filename = getLastCalibration(prefix)
    try:
        DataFrame = pd.read_csv(filename)
        return DataFrame
    except:
        print("File",filename,"does not exist.")

def saveCalibrationParameters(filename = None, prefix= "Tenzo"):
    fCfg = open("cfg.json","r")
    Cfg = json.loads(fCfg.read())
    fCfg.close()

    calib = readCalibration(filename, prefix)
    ramps = calib.loc[calib["Status"].isin(["up","down"])]
    rampsUp = ramps.loc[ramps["Status"] == "up"]
    rampsDown = ramps.loc[ramps["Status"] == "down"]
    # ramps = ramps.loc[ramps["V"] > Cfg["V_limit"]] # filter outlayers
    slope, intercept, r_value, p_value, std_err  = linregress(ramps["F"],ramps["V"])
    R2 = r_value**2
    if R2 < 0.9:
        print("R^2 is too low!\nThere could be some outlayers in the data caused by DAQ card unstability... Try to edit V_limit in cfg.json.")
        return 1
    else:
        print("Saving fit parameters of %s to cfg.json" %prefix)
        Cfg[prefix] = [-intercept/slope, 1/slope]
        fCfg = open("cfg.json","w")
        fCfg.write(json.dumps(Cfg, indent= 4))
        fCfg.close()
        print(Cfg[prefix])
    
    err = np.sqrt(np.sum(np.abs(slope*ramps["F"] + intercept - ramps["V"])**2)/(len(ramps["F"])-1))
    plt.title("R^2 = %1.3f, std = %1.3e mV" %(R2, err*10**3))
    F0, F1 = np.min(ramps["F"])-0.2, np.max(ramps["F"]) + 0.2
    u0, u1 = F0*slope + intercept, F1*slope + intercept
    plt.plot(rampsUp["F"],rampsUp["V"]*1000, ".y", markersize=8)
    plt.plot(rampsDown["F"],rampsDown["V"]*1000, ".g", markersize=8)

    plt.plot([F0, F1], [u0*1000, u1*1000], "r")
    plt.plot([F0, F1], [(u0 + err)*1000, (u1 + err)*1000], "--r")
    plt.legend(["Winding","Unwinding", "Fit", "Error"])
    plt.plot([F0, F1], [(u0 - err)*1000, (u1 - err)*1000], "--r")
    plt.plot(rampsUp["F"],rampsUp["V"]*1000, ".y", markersize=8)
    plt.plot(rampsDown["F"],rampsDown["V"]*1000, ".g", markersize=8)
    plt.grid()
    plt.xlabel("Force [N]")
    plt.ylabel("Tenzometer votage [mV]")
    plt.show()

def calibrate(side = "L"):
    pins = [[8,9,10,11], [0, 1, 2, 3]]
    name = ["TenzoL", "TenzoR"]
    if side == "L":
        pins = pins[0]
        name = name[0]
        Ch = 4
    elif side == "R":
        pins = pins[1]
        name = name[1]
        Ch = 2
    else:
        print("Wring input of side! Must be L or R.")
        return
    lj = U6()
    stpr = Stepper(lj, DO= pins, delay= 0.005)
    doCalibration(lj, stpr, outFilePrefix=name, iterations=1, Ch_tenzo= Ch)
    lj.close()
    saveCalibrationParameters(prefix=name)

if __name__ == "__main__":
    calibrate("R")

    # saveCalibrationParameters(prefix= "Tenzo2")
    # getTimeBehavior(Ch= 0)