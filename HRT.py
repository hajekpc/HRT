#!/usr/bin/env python
"""
Python3.8.6
blablabla Tonda is the author :)
"""
#Import the necessary libraries
from threading import Thread
from queue import Queue
# from labjack_unified.devices import LabJackU6
from time import sleep
from tkinter import *


class stepper(Thread):
    # stepper is a thread, running a state machine
    def __init__(self, lj, DO = [0, 1, 2, 3], delay = 0.000015, name = "Stepper"):
        Thread.__init__(self) #thread initiation - must be started externaly by self.start()

        # set up variables
        self.state = "init"
        self.lj = lj # LabJackU6 session
        self.DO = DO # Occupied pins - MUST BE IN RIGHT ORDER!
        self.delay = delay # DO switching interval in seconds
        self.name = name # every nice things has a name!
        self.qu = Queue() # commands queue for state machine controll
        self.x_set = 0 # required position
        self.x_cur = 0 # current 'home' position
        
        # go to default motor state
        # change - to + for oposite direction at *
        for pin in range(4):
            pin = -pin # *
            # microstep
            self.lj.setDOState(self.DO[pin % 4], 1)
            print("turn on pin", pin % 4)
            sleep(self.delay)
            self.lj.setDOState(self.DO[(pin - 1) % 4], 1) # *
            print("turn on pin", (pin - 1) % 4) 
            sleep(self.delay)
            self.lj.setDOState(self.DO[pin % 4], 0)
            print("turn off pin", pin % 4)
            
            sleep(self.delay)
        self.lj.setDOState(self.DO[0], 0)
        
        print(self.name, "initialized")

    def zero(self): # set all pins to zero
        for pin in self.DO:
            self.lj.setDOState(pin, 0)
            self.state = 'idle'
    
    def step(self, s = -1): # do step in direction s
        if s == 0:
            self.zero()
        else:
            for pin in range(4):
                pin = s * pin
                # microstep
                self.lj.setDOState(self.DO[pin % 4], 1)
                sleep(self.delay)
                self.lj.setDOState(self.DO[(pin + s * 1) % 4], 1)
                sleep(self.delay)
                self.lj.setDOState(self.DO[pin % 4], 0)
                sleep(self.delay)

            self.x_cur += s
    
    def chase(self):
        # stepper will go to self.x_set
        while self.state == "chase": # chase loop - can be externally stopped by changing state
            # decide direction 
            if self.x_set > self.x_cur:
                s = 1
            elif self.x_set < self.x_cur: 
                s = -1
            
            if self.x_set == self.x_cur: # stepper is on x_set            
                self.zero() # set all pins zero
                print ("", end="\r")
                print(self.name, "is at x =", self.x_cur) # report position / end of process
                print(">:")
                # leave chase loop and set state to "idle"
                self.state = "idle"
                break
            else: # step towards x_set
                self.step(s)

    def run(self):
        # state machine of stepper thread
        while True:
            self.state = self.qu.get() # waiting for new command in queue
            sleep(0.2)

            if self.state == "chase":          
                self.chase()
        
            elif self.state == "stop": # with self.cmd exteption will stop cirrent process inside state machine
                self.zero()
                self.state = "idle"

            elif self.state == "kill": # kills the thread
                print(self.name, "- stopped.")
                break

    def cmd(self, cmd):
        # send cmd to queue
        if cmd != self.state:
            self.qu.put(cmd)
        # stop loops inside state machine
        if cmd == "stop": self.state = "stop" # self.stop() is owned by Thread class
    
    def mv(self, d):
        # move ralatively
        self.x_set = self.x_set + d
        self.cmd("chase")

    def goto(self, x):
        # move to absolute position
        self.x_set = x
        self.cmd("chase")

class GUI(Tk):
    def __init__(self):
        Tk.__init__(self)
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

        ).place(x=400, y=125, anchor='center')


        but1 = Button(self, text="blah",command=self.blah ).place(x=0,y=0)
        but2 = Button(self, text="quit",command=self.quit ).place(x=50, y=10)
    def blah(self):
        self.calibrated_force_value.set("%.3f N"%(self.x))
        self.x+=0.12

