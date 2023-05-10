from u6 import U6
from time import sleep
lj = U6()
def sample(Ch = 0):
    print(lj.getAIN(Ch, differential= True))

Rmean = 0
n = 50
for i in range(n*4):
    ain2 = lj.getAIN(2, gainIndex=2, resolutionIndex=8, settlingFactor= 0) - lj.getAIN(1, gainIndex=2, resolutionIndex=8, settlingFactor= 0)
    R = ain2/0.0002
    Rmean += R
    # sleep(0.01)

Rmean = Rmean / (n*4)
print("Rmean = ", Rmean)
while True:
    R = 0
    
    for i in range(n):
        ain2 = lj.getAIN(2, gainIndex=2, resolutionIndex=8, settlingFactor= 0) - lj.getAIN(1, gainIndex=2, resolutionIndex=8, settlingFactor= 0)
        R += ain2/0.0002
        # print(lj.getAIN(3, gainIndex=2, resolutionIndex=8, settlingFactor= 0))
    R = R/n
    # print("dR/R = %7.4f %%, R = %5.2f" %((R - Rmean)/Rmean*100, R), end="\r")
    print(R, end="\r")
    # input(":")
