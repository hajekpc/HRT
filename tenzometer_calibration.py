from stepper import Stepper
from u6 import U6
import numpy as np
import pandas as pd
from time import sleep, time
from futek import getFutekForce
from matplotlib import pyplot as plt
from datetime import datetime
from realtimeplotter import calibPlotter
from math import floor
from threading import Thread
from queue import Queue
import os
from scipy.stats import linregress
import csv

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
                u_tenzo = - np.mean(np.array(AIN_tenzo)) + np.mean(np.array(AIN_comptenzo)) # this is actual voltage on tenzometer minus compensation tenzometer voltage
                F_futek = getFutekForce(np.mean(np.array(AIN_futek)))
                break
    
    if T0 is not None:
        return [F_futek, u_tenzo, T1, T2]
    else:
        return [F_futek, u_tenzo]




def initCalibration(lj, stpr, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6, F_default = 0.7):
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    ChOpt_futek = 0b10110000 # gain 1000 -> range ~ +/- 0.01 V
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 33.9ms/scan -> 29 Hz scan freq
    lj.streamConfig(    NumChannels=3, ChannelNumbers= [Ch_comptenzo, Ch_tenzo, Ch_futek], ChannelOptions=[ChOpt_tenzo, ChOpt_tenzo, ChOpt_futek], 
                        ResolutionIndex=8, ScanFrequency= 27, InternalStreamClockFrequency=1, SettlingFactor=0,
                        )
    stpr.mv(-10)
    F_futek = getSample(lj, n_samples=200)[0]
    print("\n")
    print("F = %2.4f N" %F_futek, end="\r")
    if F_futek > F_default:
        while F_futek > F_default:
            stpr.mv(-1)
            sleep(0.2)
            F_futek = getSample(lj, n_samples= 50)[0]
            print("F = %2.4f N" %F_futek, end="\r")

    elif F_futek < F_default:
        while F_futek < F_default:
            stpr.mv(1)
            sleep(0.2)
            F_futek = getSample(lj, n_samples= 50)[0]
            print("F = %2.4f N" %F_futek, end="\r")
    stpr.x_cur = 0
    sleep(2)


def doDrift(lj, stpr, plotter, state, pos, calib, T_relax = 20, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    T0 = time()
    lj.streamStart()
    stpr.goto(pos)
    for r in lj.streamData():
        T = time() - T0
        print("T =",T,"s")
        if r is not None:
            u_tenzo = -np.mean(np.array(r["AIN%i" %Ch_tenzo])) + np.mean(np.array(r["AIN%i" %Ch_comptenzo]))
            F_futek = getFutekForce(np.mean(np.array(r["AIN%i" %Ch_futek])))
            calib.append([-1, F_futek, u_tenzo, T, 0, stpr.x_cur, state])
            plotter.addT(T, F_futek, stpr.x_cur)
        if T > T_relax:
            lj.streamStop()
            plotter.newT()
            break

def DriftTo(lj, stpr, plotter, calib, F, F_offset = 0, dF_min = 0.005, T_max = 180, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    plotter.newT()
    lj.streamStart()
    state = None
    T0 = time()
    dF = []
    for r in lj.streamData():
        T = time() - T0
        # print("T =",T,"s")
        if r is not None and stpr.state == "idle":
            u_tenzo = -np.mean(np.array(r["AIN%i" %Ch_tenzo])) + np.mean(np.array(r["AIN%i" %Ch_comptenzo]))
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

def rampUpAndDown(lj, stpr, calib, plotter, T0 = time(), F_bot = 1, F_top = 6, nF_points = 16, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    F_points = np.linspace(F_bot, F_top, nF_points)
    F_offset = 0 # can compensate overshooting
    sleep(1)
    # ramping up
    plotter.new()
    for F in F_points:
        DriftTo(lj, stpr, plotter, calib, F, F_offset= F_offset, Ch_tenzo= Ch_tenzo)
        sample = getSample(lj, T0, n_samples= 200)
        plotter.add(sample[0], sample[1])
        calib.writerow(sample + [stpr.x_cur, "up", F])

        F_futek = sample[0]
        print("F = %2.4f N" %F_futek, end="\r")
    plotter.clearT()
    
    # ramping down
    plotter.new()
    for F in np.flip(F_points)[1:]:
        DriftTo(lj, stpr, plotter, calib, F, F_offset= F_offset, Ch_tenzo= Ch_tenzo)
        sample = getSample(lj, T0, n_samples= 200)
        plotter.add(sample[0], sample[1])
        calib.writerow(sample + [stpr.x_cur, "down", F])
        F_futek = sample[0]
        print("F = %2.4f N" %F_futek, end="\r")
    plotter.clearT()


    stpr.goto(0)
    sleep(1)


def doCalibration(lj, stpr, outFilePrefix = "Tenzo", iterations = 1, Ch_tenzo = 4, Ch_comptenzo = 0, Ch_futek = 6):
    initCalibration(lj, stpr)
    T0 = time()
    plotter = calibPlotter()
    outFile = open("calibration/%s-%s.csv" %(outFilePrefix, datetime.now().strftime("%d-%m-%Y-%H-%M-%S")), "w")
    calib = csv.writer(outFile)
    header = ["F", "V", "T1", "T2", "x", "Status", "F_set"]
    calib.writerow(header)

    for i in range(iterations):
        rampUpAndDown(lj, stpr, calib, plotter, nF_points=11)

    outFile.close()

    stpr.goto(-5)
    sleep(2)
    stpr.cmd("kill")
    plotter.end()

def getLastCalibration(appendix= "Tenzo"):
    lastDatetime = datetime(1,1,1)
    for file in os.listdir("calibration/"):
        if file.startswith(appendix):
            currentDatetime = datetime.strptime(file[-23:-4], "%d-%m-%Y-%H-%M-%S")
            if currentDatetime > lastDatetime:
                lastDatetime = currentDatetime
                lastFile = file
    return "calibration/" + lastFile

def readCalibration(filename = None):
    if filename is None:
        filename = getLastCalibration()
    try:
        DataFrame = pd.read_csv(filename)
        return DataFrame
    except:
        print("File",filename,"does not exist.")

def getCalibrationParameters(filename = None):
    calib = readCalibration(filename)
    ramps = calib[calib["Status"].isin(["up","down"])]

def streamtest(lj):
    ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
    ChOpt_futek = 0b10110000 # gain 1000 -> range ~ +/- 0.01 V
    # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan = 33.9ms/scan -> 29 Hz scan freq
    lj.streamConfig(    NumChannels=3, ChannelNumbers= [0, 2, 6], ChannelOptions=[ChOpt_tenzo, ChOpt_tenzo, ChOpt_futek], 
                        ResolutionIndex=8, ScanFrequency= 27, InternalStreamClockFrequency=1, SettlingFactor=0,
                        )
    data0 = []
    data1 = []
    data2 = []

    T0 = time()
    lj.streamStart()
    for r in lj.streamData():
        if r is not None:
            data0 += r["AIN0"]
            data1 += r["AIN2"]
            data2 += r["AIN6"]
        if (time() - T0) > 120:
            lj.streamStop()
            break
    data = [
        np.array(data0),
        np.array(data1),
        np.array(data2)
    ]
    for d in data:
        print(d.size, np.mean(d), np.max(d),np.min(d))
    lj.close()

if __name__ == "__main__":
    
    lj = U6()
    stpr = Stepper(lj, DO= [7,6,5,4], delay= 0.005)
    doCalibration(lj, stpr, outFilePrefix="Tenzo1", iterations=1)


    # initCalibration(lj, stpr= stpr)
    # plotter = calibPlotter()
    # calib = []
    # rampUpAndDown(lj, stpr, calib, plotter)

    # stpr.goto(-5)
    # sleep(2)
    # stpr.cmd("kill")
    # plotter.end()


# doCalibration(lj, stpr, steps=3, F_top=7, iterations=2)
# doCalibrationAnalysis()