#!/usr/bin/env python
"""
This is simple example for stepper controll in HRT project.
"""
from u6 import U6
from HRT import Stepper

if __name__ == '__main__':
    # Initialization of LabJackU6 and stepper module
    lj= U6()
    stpr = Stepper(lj= lj)
    stpr.start()

    # Controll loop
    while True:
        cmd = input(">: ")
        if cmd == "kill":
            stpr.cmd(cmd)
            break
        elif cmd != "":
            try:
                stpr.goto(int(cmd))
            except:
                stpr.cmd(cmd)

    # Ending section
    print("Stoping programm")
    stpr.join()
    lj.close()