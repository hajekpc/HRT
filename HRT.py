from tkinter import *
from stepper import Stepper
from u6 import U6
from threading import Thread, Lock
from time import sleep
from queue import Queue
import sys


class HRT(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.lj = U6()
        # self.lj.reset()
        # sleep(10)
        self.lj.getCalibrationData()
        self.geometry('800x600-0+0')
        self.resizable(width=False, height=False)
        self.title("HRT")
        self.img = PhotoImage(file='scheme.png')
        scheme = Label(self, image=self.img)
        scheme.place(x=0, y=0)
        self.calibrated_force_value = StringVar()
        self.calibrated_force_value.set('None')
        self.x = 0
        calibrated_force_label = Label(self, 
            textvariable=self.calibrated_force_value,
            anchor=S,
            font=("sans-serif", 18),
            bd=0,

        ).place(x=400, y=125, anchor='center')

        self.winder = (Winder(self, self.lj, 0 ), Winder(self, self.lj, 2 ), Winder(self, self.lj, 1 ))

        # setting stream to obtain tenzometers values
        # separate class might be created
        ChOpt = 0b00100000
        
        self.lj.streamConfig(   NumChannels=3, ChannelNumbers=[0, 1, 2], ChannelOptions=[ChOpt, ChOpt, ChOpt], 
                                ResolutionIndex=8, ScanFrequency= 300, InternalStreamClockFrequency=1, SettlingFactor=0
                                )
                                
        self.AIN_thread = Thread(target= self.scanAIN ,daemon=True)
        self.AIN_lock = Lock()
        self.AIN_lock.acquire()

        try:
            self.lj.streamStart()
        except:
            self.lj.streamStop()
            self.lj.streamStart()
        self.AIN = [float(0), float(0), float(0)]
        self.stateDAQ = "forcemeas"
        self.AIN_thread.start()
        while self.AIN == [0,0,0]:
            sleep(0.1)
        
        
        # self.gotoDefaultposition(id= 2)
        # self.winder2.stepper.cmd("up")
        # while 
        # print(self.R0)
        # print(self.AIN)
        # sleep(2)
        # print(self.AIN)


        # while True:
        #     print(self.AIN_queue[0].get())

    def blah(self):
        self.calibrated_force_value.set("%.3f N"%(self.x))
        self.x+=0.12

    def scanAIN(self):
        n = 5
        i = 0
        first = True
        meanR = [0,0,0]
        R0 = [1,1,1]
        self.meanRelativeR = [0,0,0]
        Rhistory = [[0]*10, [0]*10, [0]*10]

        try:
            for r in self.lj.streamData():

                if r is not None and self.stateDAQ == "forcemeas":
                    # acquire R0
                    self.AIN[0] = sum(r['AIN0'])/len(r['AIN0'])
                    self.AIN[1] = sum(r['AIN1'])/len(r['AIN1'])
                    self.AIN[2] = sum(r['AIN2'])/len(r['AIN2'])
                    current = 0.0002 # LJ current supply constant
                    R = (self.AIN[0]/current, (self.AIN[1] - self.AIN[0])/current, (self.AIN[2] - self.AIN[1])/current)
                    # print(R[2])
                    
                    # print(Rhistory[2])
                    for iR in range(3):
                        Rhistory[iR][i] = R[iR]
                    i += 1
                    if i == n:
                        i = 0

                    
                    if first:
                        if i == 0:
                            first = False
                            for iR in range(3):
                                R0[iR] = sum(Rhistory[iR])/n
                                meanR[iR] = sum(Rhistory[iR])/n
                                self.meanRelativeR = getRelativeResistance(meanR, R0)
                                self.relativeR = getRelativeResistance(R, R0)

                            self.AIN_lock.release()

                    else:
                        for iR in range(3):
                            meanR[iR] = sum(Rhistory[iR])/n
                    if not first:
                        self.relativeR = getRelativeResistance(R, R0)
                        print("dR/R = %7.4f %%" %self.meanRelativeR[2], end='\r')
                        self.meanRelativeR = getRelativeResistance(meanR, R0)

        finally:
            print("Stream stopped due to error in stream reading.")
            if self.lj.streamStarted:
                self.lj.streamStop()

    def gotoDefaultposition(self, id):
        self.AIN_lock.acquire()
        self.winder[id].stepper.cmd('chase')
        while self.meanRelativeR[id] < 0.015 and self.relativeR[id] < 0.03:
            self.winder[id].stepper.x_set += 5
            print('blah')
        self.winder[id].stepper.cmd('idle')
        self.AIN_lock.release()
        

        # while self.meanRelativeR[id] < 0.015:
        #     self.winder[id].stepper.x_set += 10
        # self.self.winder[id].stepper.cmd('idle')

def getRelativeResistance(R, R0):
    return (100*(R[0] - R0[0])/R0[0], 100*(R[1] - R0[1])/R0[1], 100*(R[2] - R0[2])/R0[2])


class Winder():
    global Font
    def __init__(self, gui, lj, pos = 0):
        # create GUI

        # constants for layout at gui and LabJack digital pins
        x_positions = [203, 403, 603]
        stepper_pins = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]   
        y = 301
        x = x_positions[pos] # this x is for positions at gui        
        self.display = {}     

        # initialize physiccal stepper ;)
        self.stepper = Stepper(lj, DO= stepper_pins[pos], display=self.display)
        
        # initialize tk objects
        """ ROW 1 
        State display
        """
        self.display['state'] = StringVar(value= "init")
        state_label = Label(
            gui,
            textvariable = self.display['state'],
            font= ("Bauhaus 83", 28),
        ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
        )

        """ ROW 2
        1) stepper position display
        2) buttons to go up or down
        """
        y += 50
        self.display['x'] = IntVar(value= 0) # this is to display stepper position value :P
        self.plus_up = PhotoImage(file = "plus_up.png")
        self.plus_down = PhotoImage(file = "plus_down.png")
        self.minus_up = PhotoImage(file = "minus_up.png")
        self.minus_down = PhotoImage(file = "minus_down.png")
        Label(
            gui,
            textvariable= self.display['x'],
            font= ("Bauhaus 83", 28),
            ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
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
            anchor=SW,
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
            )

        

        """ ROW 3 & 4
        x_set entry
        Chase x_set button
        """
        y += 50
        self.display['x_set'] = IntVar(value= 0)
        self.display['x_set'].trace("w", self.x_set_update)

        self.x_set_entry = Entry(
            gui,
            textvariable= self.display['x_set'],
            font= ("Bauhaus 83", 28),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )
        self.x_set_entry.place(
            x= x + 99, 
            y= y,
            anchor=S,
            width=198,
            height=48
        )

        y += 50
        self.chase_up = PhotoImage(file = "chase_up.png")
        self.chase_down = PhotoImage(file = "chase_down.png")
        self.chase_button = Button(
            gui, 
            image = self.chase_up, 
            command = self.chase,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.chase_button.place(
            x= x + 99, 
            y= y,
            anchor=S,
            )
        
        
        # self.stepper.start()


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

    def set_all_off(self):
        # set all buttons up
        self.plus_button.config(image= self.plus_up)
        self.minus_button.config(image= self.minus_up)
        self.chase_button.config(image= self.chase_up)
    
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
    def chase(self):
        if self.stepper.state == "chase":
            self.chase_button.config(image = self.chase_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.chase_button.config(image = self.chase_down)
            self.stepper.cmd("chase")



        
   
        
        

        
            


if __name__ == '__main__':
    hrt = HRT()
    hrt.mainloop()
    sys.exit()
    