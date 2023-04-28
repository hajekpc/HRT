from u6 import U6
from time import sleep
lj = U6()
n = 4000
GI = 4
U_calib = []
while True:
    U0 = 0
    U1 = 0

    
    for i in range(n):
        U1  += lj.getAIN(1, gainIndex=GI, resolutionIndex=8, settlingFactor= 0)
        U0  += lj.getAIN(0, gainIndex=GI, resolutionIndex=8, settlingFactor= 0)
        # print(lj.getAIN(3, gainIndex=2, resolutionIndex=8, settlingFactor= 0))
    U0 = U0/n
    U1 = U1/n

    print(U1-U0)
    U_calib.append(U1-U0)
    print(U_calib)
    if input(">: ") == "stop":
        break