from tkinter import *
from stepper import Stepper
from u6 import U6, DAC0_8, DAC1_8
from threading import Thread, Lock
from time import sleep, time
from queue import Queue
import sys, json, csv
import numpy as np
from datetime import datetime
from simple_pid import PID


class HRT(Tk):
    def __init__(self, outFilePrefix = "Meas"):
        Tk.__init__(self)
        self.lj = U6()
        # self.lj.reset()
        # sleep(10)
        self.lj.getCalibrationData()
        self.outFilePrefix = outFilePrefix
        self.outFile = None

        self.geometry('800x600-0+0')
        self.resizable(width=False, height=False)
        self.title("HRT")
        self.img = PhotoImage(file='gui/scheme.png')
        self.record_state = False
        scheme = Label(self, image=self.img)
        scheme.place(x=0, y=0)
        # self.calibrated_force_value = StringVar()
        # self.calibrated_force_value.set('None')
        # self.x = 0
        # calibrated_force_label = Label(self, 
        #     textvariable=self.calibrated_force_value,
        #     anchor=S,
        #     font=("sans-serif", 18),
        #     bd=0,
        self.record_up = PhotoImage(file='gui/record_up.png')
        self.record_down = PhotoImage(file='gui/record_down.png')

        self.record_button = Button(
            self,
            image = self.record_up, 
            command = self.record,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.record_button.place(
            x= 50, 
            y= 101,
            anchor= SW,
            height= 48,
            width= 48,

            )
        

        # ).place(x=400, y=125, anchor='center')
        self.winder = (Winder(self, self.lj, 0, SensorName="Tenzo2" ), Winder(self, self.lj, 1, SensorName="Futek" ), Winder(self, self.lj, 2, SensorName="Tenzo1"))
        self.lj.getFeedback(DAC0_8(self.lj.voltageToDACBits(5, dacNumber = 0, is16Bits = False))) # Set DAC0 to 5 V
        self.lj.getFeedback(DAC1_8(self.lj.voltageToDACBits(5, dacNumber = 1, is16Bits = False))) # Set DAC1 to 5 V
        # setting stream to obtain tenzometers values
        # separate class might be created
        




        self.initDAQ()
    def record(self):
        if self.record_state:
            self.record_state = False
            self.record_button.config(image= self.record_up)
            self.outFile.close()
            self.outFile = None
        else:
            self.record_button.config(image= self.record_down)
            self.T0 = time()
            self.outFile = open("data/%s-%s.csv" %(self.outFilePrefix, datetime.now().strftime("%d-%m-%Y-%H-%M-%S")), "w")
            self.writer = csv.writer(self.outFile)
            header = ["F", "T", "x", "side"]
            self.writer.writerow(header)
            self.record_state = True


    def initDAQ(self, SensorNames = ["FutekL","FutekM","FutekR"], ChannelLeft = 6, ChannelMid = 8, ChannelRight = 10, ChannelComp = 0, WinderOrder = [0,1,2]):
        self.ChannelLeft = ChannelLeft
        self.ChannelMid = ChannelMid
        self.ChannelRight = ChannelRight
        self.ChannelComp = ChannelComp
        fCalib = open("cfg.json","r")
        calib = json.loads(fCalib.read())
        fCalib.close()
        self.CalibrationParametersLeft = calib[SensorNames[0]]
        self.CalibrationParametersMid = calib[SensorNames[1]]
        self.CalibrationParametersRight = calib[SensorNames[2]]
        ChOpt_tenzo = 0b10100000 # gain 100 -> range ~ +/- 0.1 V
        ChOpt_futek = 0b10110000 # gain 1000 -> range ~ +/- 0.01 V
        # for ResolutionIndex 8 and gain > 100 it need 11.3ms/channel/scan -> 22.1 Hz scan freq
        self.lj.streamConfig(   NumChannels=3, ChannelNumbers= [ChannelLeft, ChannelMid, ChannelRight], 
                                ChannelOptions= [ChOpt_futek, ChOpt_futek, ChOpt_futek], 
                                ResolutionIndex=8, ScanFrequency= 27, InternalStreamClockFrequency= 1, SettlingFactor= 0,
                            )

        self.DAQThread = Thread(target= self.DAQloop)
        self.DAQThread.start()

    def DAQloop(self, WinderOrder = [0,1,2]):
        L = "AIN%i" %self.ChannelLeft
        M = "AIN%i" %self.ChannelMid
        C = "AIN%i" %self.ChannelComp
        R = "AIN%i" %self.ChannelRight

        Lmax = 20
        Mmax = 20
        Rmax = 20

        Lset = None
        Mset = None
        Rset = None

        Lpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))
        Mpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))
        Rpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))
        
        Lfilo = []
        Mfilo = []
        Rfilo = []

        Cout = 0        
        

        try:
            self.lj.streamStart()
        except:
            self.lj.streamStop()
            self.lj.streamStart()
        # tenzometer zeroing
        # for r in self.lj.streamData():
        #     if r is not None:
        #         Lfilo += r[L]
        #         Rfilo += r[R]
        #         if len(Rfilo) > 500 and len(Lfilo) > 500:
        #             Lforce0 = np.mean(Lfilo)*self.CalibrationParametersLeft[1] + self.CalibrationParametersLeft[0]
        #             Rforce0 = np.mean(Rfilo)*self.CalibrationParametersRight[1] + self.CalibrationParametersRight[0]
        #             print("L0 =", Lforce0, "N")
        #             print("R0 =", Rforce0, "N")
        #             Lfilo = []
        #             Rfilo = []
        #             break

        for r in self.lj.streamData():
            if r is not None:
                Lfilo += r[L]
                Mfilo += r[M]
                Rfilo += r[R]
                if self.record_state:
                    T = time() - self.T0

                    for u in r[L]:
                        F = self.CalibrationParametersLeft[1]*u + self.CalibrationParametersLeft[0]
                        self.writer.writerow([F, T, self.winder[WinderOrder[0]].stepper.x_cur, "L"])
                    for u in r[M]:
                        F = self.CalibrationParametersMid[1]*u + self.CalibrationParametersMid[0]
                        self.writer.writerow([F, T, self.winder[WinderOrder[1]].stepper.x_cur, "M"])
                    for u in r[R]:
                        F = self.CalibrationParametersRight[1]*u + self.CalibrationParametersRight[0]
                        self.writer.writerow([F, T, self.winder[WinderOrder[2]].stepper.x_cur, "R"])

            if len(Lfilo) > Lmax:
                Lfilo = Lfilo[-Lmax:]
                Lout = np.mean(Lfilo)
                Lforce = self.CalibrationParametersLeft[1]*Lout + self.CalibrationParametersLeft[0]
                try:
                    self.winder[WinderOrder[0]].display["F"].set("%1.2f N" %Lforce)
                except:
                    pass
                if self.winder[WinderOrder[0]].PIDstate:
                    if self.winder[WinderOrder[0]].stepper.state == "idle":
                        Lpid.setpoint = self.winder[WinderOrder[0]].F_set                        
                        Lpidval = Lpid(Lforce)
                        self.winder[WinderOrder[0]].stepper.goto(int(Lpidval))
                        Lpid.output_limits = (Lpidval-20, Lpidval+20)

            if len(Mfilo) > Mmax:
                Mfilo = Mfilo[-Mmax:]
                Mout = np.mean(Mfilo)
                Mforce = self.CalibrationParametersMid[1]*Mout + self.CalibrationParametersMid[0]
                try:
                    self.winder[WinderOrder[1]].display["F"].set("%1.2f N" %Mforce)
                except:
                    pass
                if self.winder[WinderOrder[1]].PIDstate:
                    if self.winder[WinderOrder[1]].stepper.state == "idle":
                        Mpid.setpoint = self.winder[WinderOrder[1]].F_set                        
                        Mpidval = Mpid(Mforce)
                        self.winder[WinderOrder[1]].stepper.goto(int(Mpidval))
                        Mpid.output_limits = (Mpidval-20, Mpidval+20)

            if len(Rfilo) > Rmax:
                Rfilo = Rfilo[-Rmax:]
                Rout = np.mean(Rfilo)
                Rforce = self.CalibrationParametersRight[1]*Rout + self.CalibrationParametersRight[0]
                try:
                    self.winder[WinderOrder[2]].display["F"].set("%1.2f N" %Rforce)
                except:
                    pass
                if self.winder[WinderOrder[2]].PIDstate:
                    if self.winder[WinderOrder[2]].stepper.state == "idle":
                        Rpid.setpoint = self.winder[WinderOrder[2]].F_set                        
                        Rpidval = Rpid(Rforce)
                        self.winder[WinderOrder[2]].stepper.goto(int(Rpidval))
                        Rpid.output_limits = (Rpidval-20, Rpidval+20)

class Winder():
    global Font
    def __init__(self, gui, lj, pos = 0, SensorName = "Tenzo2"):
        # create GUI

        # constants for layout at gui and LabJack digital pins
        x_positions = [203, 403, 603]
        stepper_pins = [[8, 9, 10, 11], [7, 6, 5, 4], [0, 1, 2, 3]]
        self.PIDstate = False
        self.F_set = 0
        y = 101
        x = x_positions[pos] # this x is for positions at gui
        self.display = {}

        # initialize physiccal stepper ;)
        self.stepper = Stepper(lj, DO= stepper_pins[pos], display=self.display, delay= 0.001)
        
        # initialize tk objects
        """ ROW 1 
        State display
        """
        self.display['state'] = StringVar(value= "init")
        state_label = Label(
            gui,
            textvariable = self.display['state'],
            font= ("Bauhaus 83", 26),
        ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
            height=46,
        )

        """ ROW 2
        1) stepper position display
        2) buttons to go up or down
        """
        y += 50
        self.display['x'] = IntVar(value= 0) # this is to display stepper position value :P
        self.plus_up = PhotoImage(file = "gui/plus_up.png")
        self.plus_down = PhotoImage(file = "gui/plus_down.png")
        self.minus_up = PhotoImage(file = "gui/minus_up.png")
        self.minus_down = PhotoImage(file = "gui/minus_down.png")
        Label(
            gui,
            textvariable= self.display['x'],
            font= ("Bauhaus 83", 28),
            ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
            height=46
            )
        self.minus_button = Button(
            gui, 
            image = self.minus_up, 
            command = self.minus,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.minus_button.place(
            x= x, 
            y= y,
            anchor= SW,
            height= 48,
            width= 48,

            )
        self.plus_button = Button(
            gui, 
            image = self.plus_up, 
            command = self.plus,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.plus_button.place(
            x= x + 150, 
            y= y,
            anchor=SW,
            height=48,
            width= 48,
            )

        

        """ ROW 3
        x_set entry
        """
        y += 50
        self.display['x_set'] = IntVar(value= 0)
        # self.display['x_set'].trace("w", self.x_set_update)

        self.x_set_entry = Entry(
            gui,
            textvariable= self.display['x_set'],
            font= ("Bauhaus 83", 28),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )
        self.x_set_entry.bind("<Return>", self.chase)
        self.x_set_entry.place(
            x= x + 99, 
            y= y,
            anchor=S,
            width=198,
            height=48
        )
        """ ROW 4
        Force display
        """
        y += 50
        self.display["F"] = StringVar(value= "-")

        Label(
            gui,
            textvariable= self.display["F"],
            font= ("Bauhaus 83", 28),
            ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=180,
            height=46
            )
        """ ROW 5
        F_set        
        """
        y += 50
        self.display['F_set'] = DoubleVar(value= 0)

        self.F_set_entry = Entry(
            gui,
            textvariable= self.display['F_set'],
            font= ("Bauhaus 83", 28),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )

        self.F_set_entry.bind("<Return>", self.F_set_update)
        self.F_set_entry.place(
            x= x + 99, 
            y= y,
            anchor=S,
            width=198,
            height=48
        )

        """ROW 6
        PID button
        """
        y += 50
        self.PID_up = PhotoImage(file = "gui/PID_up.png")
        self.PID_down = PhotoImage(file = "gui/PID_down.png")

        self.PID_button = Button(
            gui, 
            image = self.PID_up, 
            command = self.PID,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.PID_button.place(
            x= x, 
            y= y,
            anchor= SW,
            height= 48,
            width= 198,

            )

    def x_set_update(self, *args):
        try:
            # in case that display['x_set'] is not declared
            self.stepper.x_set = int(self.display['x_set'].get())
        except:
            pass
        if self.stepper.state == "chase" and self.stepper.lock.locked():
            # when chase state reaches the x_set, the thread is locked 
            # release the stepper lock for new x_set
            self.stepper.lock.release()

    def F_set_update(self, *args):
        self.F_set = self.display["F_set"].get()
    def set_all_off(self):
        # set all buttons up
        self.plus_button.config(image= self.plus_up)
        self.minus_button.config(image= self.minus_up)
        self.PID_button.config(image= self.PID_up)
        self.PIDstate = False
    
    # button functions
    def plus(self):
        if self.stepper.state == "up":
            self.plus_button.config(image = self.plus_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.plus_button.config(image = self.plus_down)
            self.stepper.cmd("up")
    
    def minus(self):
        if self.stepper.state == "down":
            self.minus_button.config(image = self.minus_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.minus_button.config(image = self.minus_down)
            self.stepper.cmd("down")
    def chase(self, source = None):
        try:
            x_set = int(self.display['x_set'].get())
            self.stepper.x_set = x_set
            if self.stepper.state != "chase":
                self.set_all_off()
                self.stepper.cmd("chase")
        except:
            pass
    def PID(self):
        if self.PIDstate:      
            self.PID_button.config(image = self.PID_up)
            self.PIDstate = False

            
        else:
            self.set_all_off()
            self.stepper.cmd("stop")
            self.PID_button.config(image = self.PID_down)
            self.PIDstate = True
            




if __name__ == '__main__':
    hrt = HRT()
    hrt.mainloop()
    sys.exit()
    