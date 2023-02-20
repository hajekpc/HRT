#!/usr/bin/env python
"""
Python3.8.6
blablabla Tonda is the author :)
"""
#Import the necessary libraries
from threading import Thread, Lock
from queue import Queue

# from labjack_unified.devices import LabJackU6
from time import sleep
from tkinter import *


class Stepper(Thread):
    # stepper is a thread, running a state machine
    def __init__(self, lj, DO = [0, 1, 2, 3], delay = 0.000015, name = "Stepper", display= None):
        Thread.__init__(self) #thread initiation - must be started externaly by self.start()

        # set up variables
        self.state = "init"
        self.lj = lj # LabJackU6 session
        self.DO = DO # Occupied pins - MUST BE IN RIGHT ORDER!
        self.delay = delay # DO switching interval in seconds
        self.name = name # every nice things has a name!
        self.lock = Lock() # lock for synchronization
        self.lock.acquire() 
        self.x_set = 0 # required position
        self.x_cur = 0 # current 'home' position
        self.display = display
        # go to default motor state
        # change - to + for oposite direction at *
        for pin in range(4):
            pin = -pin # *
            # microstep
            self.lj.setDOState(self.DO[pin % 4], 1)
            sleep(self.delay)
            self.lj.setDOState(self.DO[(pin - 1) % 4], 1) # *
            sleep(self.delay)
            self.lj.setDOState(self.DO[pin % 4], 0)            
            sleep(self.delay)
        self.lj.setDOState(self.DO[0], 0)
        
        print(self.name, "initialized")

    def zero(self): # set all pins to zero
        for pin in self.DO:
            self.lj.setDOState(pin, 0)
    
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
            try:
                self.display['x'].set(self.x_cur)
            except:
                pass


    def chase(self):
        # stepper will go to self.x_set
        # decide direction 
        if self.x_set > self.x_cur:
            s = 1
        elif self.x_set < self.x_cur: 
            s = -1
        
        if self.x_set == self.x_cur: # stepper is on x_set            
            self.zero() # set all pins zero
        else: # step towards x_set
            self.step(s)

    def run(self):
        # state machine of stepper thread
        while True:

            if self.state == "idle":
                # self.qu.get() # waiting for new command in queue
                self.lock.acquire()

            if self.state == "chase":          
                self.chase()
            
            elif self.state == "up":
                self.step(1)
            
            elif self.state == "down":
                self.step(-1)

            elif self.state == "stop": # with self.cmd exteption will stop cirrent process inside state machine
                self.zero()
                self.state = "idle"

            elif self.state == "kill": # kills the thread
                self.zero()
                print(self.name, "- stopped.")
                break

            else:
                self.state = "stop"

            # update state display
            try:
                self.display['state'].set(self.state)
            except:
                pass

    def cmd(self, cmd):
        # send cmd to queue
        if cmd != self.state:
            # self.qu.put(cmd)
            if self.lock.locked():
                self.lock.release()
            self.state = cmd
            
    
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

