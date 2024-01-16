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
from queue import Queue, Empty


class HRT(Tk):
    def __init__(self, outFilePrefix = "Meas"):
        Tk.__init__(self)
        # init LabJack (LJ)
        self.lj = U6()
        self.lj.getCalibrationData()
        # LJ processes kill variable :)
        self.quit = False

        # init output file
        self.outFilePrefix = outFilePrefix
        self.outFile = None
        self.outFile = open("data/%s-%s.csv" %(self.outFilePrefix, datetime.now().strftime("%d-%m-%Y-%H-%M-%S")), "w", newline='', encoding='utf-8')
        self.writer = csv.writer(self.outFile) #, dialect= 'unix')
        header = ["T", "FL", "FM", "FR", "xL", "xM", "xR"]
        self.writer.writerow(header)

        # Tk window settings
        self.geometry('800x400-0+0')
        self.resizable(width=False, height=False)
        self.title("HRT")
        self.img = PhotoImage(file='gui/scheme.png')

        scheme = Label(self, image=self.img)
        scheme.place(x=0, y=0)
        self.castGui()
            
        # self.Fval = DoubleVar(value= 0)
        # self.display['x_set'].trace("w", self.x_set_update)

        # self.F_set_entry = Entry(
        #     self,
        #     textvariable= self.Fval,
        #     font= ("Bauhaus 83", 28),
        #     justify=CENTER,
        #     borderwidth = 0,
        #     highlightthickness= 0,

        # )
        # self.F_set_entry.bind("<Return>", self.sendF)
        # self.F_set_entry.place(
        #     x= 100, 
        #     y= 200,
        #     anchor=S,
        #     width=198,
        #     height=48)
        
        # init buffers 
        self.AINqueue = (Queue(), Queue(), Queue())
        
        # load calibration
        self.SensorName = ("FutekL", "FutekM", "FutekR") # sensor names that will be attached to stepper from left to right
        self.side = ("L", "M", "R")
        self.Ch = (6, 8, 10) # LJ analog channels!
        self.CalibPar = ()
        fCalib = open("calib.json","r")
        calib = json.loads(fCalib.read())
        fCalib.close()

        # init winders, left is first
        self.winder = ()
        for i in range(3):
            self.CalibPar += (calib[self.SensorName[i]],)
            self.winder += (Winder(self, self.lj, pos= i, SensorName= self.SensorName[i], AINqueue= self.AINqueue[i]),)
        # turn on Futek excitation voltage for internal wheatson bridge circuit
        self.lj.getFeedback(DAC0_8(self.lj.voltageToDACBits(5, dacNumber = 0, is16Bits = False))) # Set DAC0 to 5 V, i.e. FutekM excitation voltage
        self.lj.getFeedback(DAC1_8(self.lj.voltageToDACBits(5, dacNumber = 1, is16Bits = False))) # Set DAC1 to 5 V, i.e. FutekR excitation voltage
        # FutekL is connected to VS pin (~ 5V from USB)



        # init DAQ
        self.ScanFrequency = 24 # for ResolutionIndex 8 and gain 1000 it need 11.3ms/channel/scan -> 29 Hz scan freq
        self.syncOutLock = Lock()
        self.syncOutLock.acquire()
        self.DAQThread = Thread(target= self.DAQ)
        self.DAQThread.start()
        self.syncOutThread = Thread(target= self.syncOut)
        self.syncOutThread.start()

    def sendF(self, somepar):

        self.winder[0].pid.setpoint = float(self.Fval.get())
        self.winder[2].pid.setpoint = float(self.Fval.get())

    def syncOut(self):

        dT = 1/(self.ScanFrequency)/3 # = 0.012345679012345678
        calibT = 0 # time to compensate DAQ and sinc clock shift
        # trigger will produce rising edge for each taken sample... there are 3 channels being switched with multiplexer befor ADC... each shifted by dT from each other
        while True:
            if not self.record_state:
                # wait until lock release
                print("sync waiting")
                self.syncOutLock.acquire()
                T0 = time() - calibT # get new timing after lock release
                print("sync started")
                # time of first pulse is delayed by calibT

            sleep(dT*0.45) # to not consume cpu 
            if (time() - dT) >= T0:

                self.lj.setDOState(12,1)
                T0 = time()
                sleep(dT/3) # pulse length
                self.lj.setDOState(12,0)

            if self.quit:
                break

            
    def castGui(self):
        # recording button
        self.record_state = False
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
            x= 152, 
            y= 400,
            anchor= SW,
            height= 48,
            width= 48,

            )

        # entangle button 
        self.entangle_state = False
        self.entangle_up = PhotoImage(file='gui/entangle_up.png')
        self.entangle_down = PhotoImage(file='gui/entangle_down.png')
        self.entangle_button = Button(
            self,
            image = self.entangle_up, 
            command = self.entangle,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.entangle_button.place(
            x= 402, 
            y= 400,
            anchor= SW,
            height= 48,
            width= 198,

            )

    def record(self):
        if self.record_state:
            self.syncOutLock.acquire()
            self.record_state = False
            self.record_button.config(image= self.record_up)

        else:
            self.record_state = True
            self.record_button.config(image= self.record_down)
    
    def entangle(self):
        # set entangle off
        if self.entangle_state:
            self.entangle_state = False
            self.entangle_button.config(image= self.entangle_up)
            self.winder[0].entagled_winder = None
            self.winder[2].entagled_winder = None

        # set entangle on
        else:
            self.entangle_state = True
            self.entangle_button.config(image= self.entangle_down)
            self.winder[0].entagled_winder = self.winder[2]
            self.winder[2].entagled_winder = self.winder[0]


    def DAQ(self):      
        ChOpt_futek = [0b10110000] # gain 1000 -> range ~ +/- 0.01 V
        self.lj.streamConfig(   NumChannels=3, ChannelNumbers= self.Ch, ChannelOptions= 3*ChOpt_futek, 
                                ResolutionIndex=8, ScanFrequency= self.ScanFrequency, InternalStreamClockFrequency= 1, SettlingFactor= 0,
                            )

        # Lpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))
        # Mpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))
        # Rpid = PID(7,4,5, setpoint=0, sample_time=0.3, output_limits=(0,20))

        # start AIN streaming
        try:
            self.lj.streamStart()
        except:
            # in case of already stream stream 
            self.lj.streamStop()
            self.lj.streamStart()

        self.T0 = time()
        ChannelData = [[], [], []]
        # AIN acquisition loop
        for r in self.lj.streamData():
            if r is not None:
                if self.record_state and self.syncOutLock.locked():
                    # start out clock immediately after acquiring the first sample
                    self.syncOutLock.release()
                
                for i in range(3):
                    ChannelData[i] = (np.array(r["AIN%i" %self.Ch[i]])*self.CalibPar[i][1] + self.CalibPar[i][0]).tolist() # get data for specific AIN
                    self.AINqueue[i].put(ChannelData[i]) # send data to queue

                if self.record_state:
                    self.writer.writerow([time() - self.T0] + ChannelData + [self.winder[0].stepper.x_cur, self.winder[1].stepper.x_cur, self.winder[2].stepper.x_cur])

            if self.quit:
                print("Terminating DAQ thread")
                self.lj.streamStop()
                self.outFile.close()
                return
                        
            # if len(Lfilo) > Lmax:
            #     Lfilo = Lfilo[-Lmax:]
            #     Lout = np.mean(Lfilo)
            #     Lforce = self.CalibrationParametersLeft[1]*Lout + self.CalibrationParametersLeft[0]
            #     try:
            #         self.winder[WinderOrder[0]].display["F"].set("%1.2f N" %Lforce)
            #     except:
            #         pass
            #     if self.winder[WinderOrder[0]].PIDstate:
            #         if self.winder[WinderOrder[0]].stepper.state == "idle":
            #             Lpid.setpoint = self.winder[WinderOrder[0]].F_set                        
            #             Lpidval = Lpid(Lforce)
            #             self.winder[WinderOrder[0]].stepper.goto(int(Lpidval))
            #             Lpid.output_limits = (Lpidval-20, Lpidval+20)
    def exit(self):
        self.quit = True
        for winder in self.winder:
            winder.stepper.cmd("kill") # kills stepper controll thread
            winder.quit = True # kills readout thread after queue timeout

        if self.syncOutLock.locked():
            self.syncOutLock.release()

class Winder():
    global Font
    def __init__(self, gui, lj, pos, SensorName, AINqueue):

        
        # LJ DIO pins! pins, order of pins defines the direction of the rotation (### IMPORTANT FOR PID !!!
        self.entagled_winder = None
        stepper_pins = [[8, 9, 10, 11], [7, 6, 5, 4], [0, 1, 2, 3]] 
        self.PIDrun = False
        self.F_set = 0 # default force to PID
        self.display = {} # tk variable continer
        self.quit = False # thread kill variable

        # constants for layout at gui
        x_positions = [200, 400, 600]
        x = x_positions[pos] # this x is for positions at gui
        self.castGui(gui, x)
        # init stepper
        self.stepper = Stepper(lj, DO= stepper_pins[pos], display=self.display, delay= 0.001)
        # init and start PID thread
        self.PIDProcThread = Thread(target=self.PIDProc, args= [AINqueue])
        self.PIDProcThread.start()

    # PID state machine
    def PIDProc(self, AINqueue):
        self.pid = PID(7,10,2, setpoint=0, sample_time=0.3)
        self.pid.auto_mode = False
        self.PIDstate = "idle"
        F_offset = 0.2
        while True:
            try:
                F = AINqueue.get(timeout= 1.5)
                Fmean = np.mean(F)
                try:
                    self.display["F"].set("%1.3f N" %Fmean)
                except:
                    pass # gui is not initialized or it is killed
                
                # this follows STATE MACHINE PATTERN!
                if self.PIDrun:

                    if self.PIDstate == "init":
                        direction = np.sign(self.F_set - Fmean)
                        self.PIDstate = "ramping"
                    
                    if self.PIDstate == "ramping":
                        if direction*Fmean > direction*abs(self.F_set - F_offset):
                            self.PIDstate = "run"
                            self.pid.set_auto_mode(True, self.stepper.x_cur)
                            self.pid.output_limits = (self.stepper.x_set - 2, self.stepper.x_set + 2)
                        elif abs(self.stepper.x_cur - self.stepper.x_set) <= 7:
                            self.stepper.mv(direction*10)
                    if self.PIDstate == "run" and abs(self.stepper.x_cur - self.stepper.x_set) <= 4:
                        pidVal = int(self.pid(Fmean))
                        self.stepper.goto(pidVal)
                        self.pid.output_limits = (pidVal - 20, pidVal + 20)

                elif self.PIDstate == "stop":
                    self.pid.auto_mode = False
                    self.PIDstate = "idle"

            except Empty:
                if self.quit:
                    break
            # if len(Lfilo) > Lmax:
            #     Lfilo = Lfilo[-Lmax:]
            #     Lout = np.mean(Lfilo)
            #     Lforce = self.CalibrationParametersLeft[1]*Lout + self.CalibrationParametersLeft[0]
            #     try:
            #         self.winder[WinderOrder[0]].display["F"].set("%1.2f N" %Lforce)
            #     except:
            #         pass
            #     if self.winder[WinderOrder[0]].PIDstate:
            #         if self.winder[WinderOrder[0]].stepper.state == "idle":
            #             Lpid.setpoint = self.winder[WinderOrder[0]].F_set                        
            #             Lpidval = Lpid(Lforce)
            #             self.winder[WinderOrder[0]].stepper.goto(int(Lpidval))
            #             Lpid.output_limits = (Lpidval-20, Lpidval+20)

    def castGui(self, gui, x):

        y = 100

        # initialize tk objects
        """ ROW 1 
        State display
        """
        self.display['state'] = StringVar(value= "init")
        state_label = Label(
            gui,

            textvariable = self.display['state'],
            font= ("Bauhaus 83", 20),
        ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
            height=48,
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
            font= ("Bauhaus 83", 20),
            ).place(
            x= x + 100,
            y= y,
            anchor=S,
            width=100,
            height=48
            )
        self.minus_button = Button(
            gui, 
            image = self.minus_up, 
            command = self.minus,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.minus_button.place(
            x= x+2, 
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
            font= ("Bauhaus 83", 20),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )
        self.x_set_entry.bind("<Return>", self.chase)
        self.x_set_entry.place(
            x= x + 101, 
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
            font= ("Bauhaus 83", 20),
            ).place(
            x= x + 101, 
            y= y,
            anchor=S,
            width=180,
            height=48
            )
        """ ROW 5
        F_set        
        """
        y += 50
        self.display['F_set'] = DoubleVar(value= 0)

        self.F_set_entry = Entry(
            gui,
            textvariable= self.display['F_set'],
            font= ("Bauhaus 83", 20),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )

        self.F_set_entry.bind("<Return>", self.F_set_update)
        self.F_set_entry.place(
            x= x + 101, 
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
            x= x+2, 
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

    def PID(self, native = True):
        if self.PIDrun:      
            self.PID_button.config(image = self.PID_up)
            self.PIDstate = "stop"
            self.PIDrun = False

        else:
            self.set_all_off()
            self.stepper.cmd("stop")
            self.PID_button.config(image = self.PID_down)
            self.PIDstate = "init"
            self.PIDrun = True

        if self.entagled_winder and native:
            self.entagled_winder.PID(False)
    
    def F_set_update(self, native = True, *args):
        self.F_set = self.display["F_set"].get()
        self.pid.setpoint = self.F_set

        if self.entagled_winder and native:
            # self.entagled_winder.F_set = self.F_set
            self.entagled_winder.display["F_set"].set(self.F_set)
            self.entagled_winder.F_set_update(native = False)
    
    def set_all_off(self):
        # set all buttons up
        self.plus_button.config(image= self.plus_up)
        self.minus_button.config(image= self.minus_up)
        self.PID_button.config(image= self.PID_up)
        self.PIDrun = False
    

if __name__ == '__main__':
    hrt = HRT()
    hrt.mainloop()
    hrt.exit()
    sys.exit()
    