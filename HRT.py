#Import the necessary libraries
from threading import Thread
from queue import Queue
from labjack_unified.devices import LabJackU6
from time import sleep

class stepper(Thread):
    # stepper is a thread, running a state machine
    def __init__(self, lj, DIO = ['FIO0', 'FIO1', 'FIO2', 'FIO3'], delay = 0.00002, name = "Stepper"):
        Thread.__init__(self) #thread initiation - must be started externaly by self.start()

        # set up variables
        self.state = "init"
        self.lj = lj # LabJackU6 session object
        self.DIO = DIO # Occupied pins - MUST BE IN RIGHT ORDER!
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
            self.lj.set_digital(self.DIO[pin%len(self.DIO)], 1)
            sleep(self.delay)
            self.lj.set_digital(self.DIO[(pin - 1) % len(self.DIO)], 1) # * 
            sleep(self.delay)
            self.lj.set_digital(self.DIO[pin%len(self.DIO)], 0)
            sleep(self.delay)
        self.lj.set_digital(self.DIO[0], 0)
        
        print(self.name, "initialized")

    def zero(self): # set all pins to zero
        for pin in self.DIO:
            self.lj.set_digital(pin, 0)
            self.state = 'idle'
    
    def step(self, s = -1): # do step in direction s
        if s == 0:
            self.zero()
        else:
            for pin in range(4):
                pin = s * pin
                # microstep
                self.lj.set_digital(self.DIO[pin % len(self.DIO)], 1)
                sleep(self.delay)
                self.lj.set_digital(self.DIO[(pin + s * 1) % len(self.DIO)], 1)
                sleep(self.delay)
                self.lj.set_digital(self.DIO[pin % len(self.DIO)], 0)
                sleep(self.delay)
            self.x_cur += s
    
    def chase(self):
        # stepper will go to self.x_set
        while self.state == "chase": # chase loop - can be externally stopped by changing state
            #decide direction 
            if self.x_set > self.x_cur:
                s = 1
            else: 
                s = -1

            if self.x_set == self.x_cur: # stepper is on x_set            
                self.zero() # set all pins zero
                print(self.name, "is at x =", self.x_cur) # report position / end of process
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