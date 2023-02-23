from u6 import U6
from time import sleep
lj = U6()
Rmean = 118.66990371765245
Rmean = 0
for i in range(100):
    ain2 = lj.getAIN(2, gainIndex=2)
    R = ain2/0.0002
    Rmean += R
    sleep(0.01)

Rmean = Rmean / 100
print("Rmean = ", Rmean)
while True:
    R = 0
    
    for i in range(20):
        ain2 = lj.getAIN(2, gainIndex=2)
        R += ain2/0.0002
    R = R/20
    print("dR =",(Rmean - R)/Rmean*100, end="\r")

print(sum/100/0.0002)