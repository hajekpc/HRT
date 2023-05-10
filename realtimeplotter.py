from matplotlib import pyplot as plt
from time import sleep
from math import ceil
from random import random, randint
class calibPlotter():
    def __init__(self):
        plt.ion()
        self.f = plt.figure(figsize=(10,8))    
        self.ax = self.f.add_subplot(211)
        self.ax.set_xlabel("Force [N]")
        self.ax.set_ylabel("Tenzometer voltage [V]")
        self.Ftop = 2
        self.ax.set_xlim([0,self.Ftop])
        self.F = []
        self.Ft = []

        self.u = []
        self.l, = self.ax.plot(self.F, self.u, '-x')
        self.ylims = None
        self.offset = 0.000005


        self.t = []
        self.x = []

        self.axF = self.f.add_subplot(212)
        self.axF.set_xlim([0, 1])
        self.axF.set_ylim([0, 2])
        self.axF.set_xlabel("Time [s]")
        self.axF.set_ylabel("Force [N]", color= 'tab:red')
        self.lF, = self.axF.plot(self.t, self.Ft, color= 'tab:red', marker= ".")

        self.axx = self.axF.twinx()
        self.axx.set_ylim([-1, 10])
        self.axx.set_ylabel("Position [steps]", color= 'tab:blue')
        self.lx, = self.axx.plot(self.t, self.x, color= 'tab:blue', marker= ".")

        self.linesT = [self.lx, self.lF]

        plt.pause(0.2)




    def add(self, F, u, detail = False):
        if self.ylims is None:
            self.ylims = [u - self.offset, u + self.offset]
            # self.ax.set_ylim(self.ylims)
        elif u < self.ylims[0]:
            self.ylims[0] = u - self.offset
        elif u > self.ylims[1]:
            self.ylims[1] = u + self.offset

        if detail:
            self.ax.set_ylim([u - self.offset, u + self.offset])
            self.ax.set_xlim([F - 0.5, F + 0.5])
        else:
            if self.ax.get_ylim() != self.ylims:
                self.ax.set_ylim(self.ylims)
            if F > self.Ftop:
                self.Ftop = ceil(F)
                self.ax.set_xlim([0, self.Ftop])
            if self.ax.get_xlim()[0] != 0:
                self.ax.set_xlim([0, self.Ftop])

        # print(self.ylims)
        self.F.append(F)
        self.u.append(u)
        self.l.set_xdata(self.F)
        self.l.set_ydata(self.u)
        # print(self.l.get_ydata())
        self.f.canvas.draw()
        self.f.canvas.flush_events()
        plt.pause(0.1)
    def new(self):
        self.F = []
        self.u = []

        self.l, = self.ax.plot(self.F, self.u, '-x')
        plt.pause(0.1)

    def zoomOut(self):
        self.ax.set_xlim([0, self.Ftop])
        self.ax.set_ylim(self.ylims)
        plt.pause(0.1)
        

    def addT(self, t, F, x):
        if ceil(t+1) > self.axF.get_xlim()[1]:
            self.axF.set_xlim([0, ceil(t+1)])
            self.axx.set_xlim([0, ceil(t+1)])
        if ceil(F + 0.5) > self.axF.get_ylim()[1]:
            self.axF.set_ylim([0, ceil(F+1)])

        if x + 10  > self.axx.get_ylim()[1]:
            self.axx.set_ylim([0, self.axx.get_ylim()[1] + 10])

        self.t.append(t)

        self.Ft.append(F)
        self.lF.set_xdata(self.t)
        self.lF.set_ydata(self.Ft)

        self.x.append(x)
        self.lx.set_xdata(self.t)
        self.lx.set_ydata(self.x)
        plt.pause(0.1)

    def newT(self):
        plt.setp(self.lF, linestyle= ":")
        plt.setp(self.lx, linestyle= ":")
        # plt.setp(self.lx, "--")
        plt.pause(0.1)
        self.t = []
        self.Ft = []
        self.x = []
        self.lF, = self.axF.plot(self.t, self.Ft, color= 'tab:red', marker= ".")
        self.lx, = self.axx.plot(self.t, self.x, color= 'tab:blue', marker= ".")
        self.linesT.append(self.lF)
        self.linesT.append(self.lx)

        plt.pause(0.1)
    def clearT(self):
        try:
            for line in self.linesT:
                line.remove()
            plt.pause(0.1)
        except:
            pass
        self.linesT = []
        plt.pause(0.1)

    def end(self):
        

        plt.ioff()
        plt.show()
        plt.pause(0.1)


if __name__ == '__main__':
    plotter = calibPlotter()

    for i in range(2):
        for i in range(3):
            plotter.add(i/10 + random(), -0.0024 + (random()-0.5)/10000)

        plotter.new()

    plotter.zoomOut()
    for i in range(2):
        for i in range(3):
            plotter.addT(i/10, i/10 + random(), i*10 + randint(-5, 5))

        plotter.newT()
    plotter.clearT()
    for i in range(2):
        plotter.new()
        for i in range(3):
            plotter.add(i/10 + random(), -0.0024 + (random()-0.5)/10000)


    for i in range(3):
        plotter.newT()
        for i in range(3):
            plotter.addT(i/10, i/10 + random(), i*10 + randint(-5, 5))

    sleep(0.5)
    plotter.end()