#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is simple example for stepper controll in HRT project.
"""
from labjack_unified.devices import LabJackU6
from HRT import stepper

if __name__ == '__main__':
    # Initialization of LabJackU6 and stepper module
    lj= LabJackU6()
    lj.display_info()
    stpr = stepper(lj= lj)
    stpr.start()

    # Controll loop
    while True:
        cmd = input(">: ")
        if cmd == "stop":
            break
        
        try:
            stpr.goto(int(cmd))
        except:
            pass

    # Ending section
    print("Stoping programm")
    stpr.join()
    lj.close()