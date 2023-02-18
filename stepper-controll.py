#!/usr/bin/env python
"""
This is simple example for stepper controll in HRT project.
"""
from u6 import U6
from HRT import stepper

if __name__ == '__main__':
    # Initialization of LabJackU6 and stepper module
    lj= U6()
    

    stpr = stepper(lj= lj)
    stpr.start()

    # Controll loop
    while True:
        cmd = input(">: ")
        if cmd == "stop":
            stpr.cmd(cmd)
            break
        
        try:
            stpr.goto(int(cmd))
        except:
            pass

    # Ending section
    print("Stoping programm")
    stpr.join()
    lj.close()