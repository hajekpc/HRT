from tkinter import *



class GUI(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.geometry('800x600')
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


if __name__ == '__main__':

    # Add image file
    
    gui = GUI()
    gui.mainloop()
    