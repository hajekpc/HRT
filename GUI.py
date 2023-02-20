from tkinter import *
from HRT import Stepper
from u6 import U6


class GUI(Tk):
    def __init__(self, lj):
        Tk.__init__(self)
        self.lj = lj
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
            bd=0,

        ).place(x=400, y=125, anchor='center')

        self.winder1 = Winder(self, lj, 0 )
        self.winder2 = Winder(self, lj, 1 )
        self.winder3 = Winder(self, lj, 2 )

    def blah(self):
        self.calibrated_force_value.set("%.3f N"%(self.x))
        self.x+=0.12

class Winder():
    global Font
    def __init__(self, gui, lj, pos = 0):
        # create GUI

        # constants for layout at gui and LabJack digital pins
        x_positions = [203, 403, 603]
        stepper_pins = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]   
        y = 301
        x = x_positions[pos] # this x is for positions at gui        
        self.display = {}     

        # initialize physiccal stepper ;)
        self.stepper = Stepper(lj, DO= stepper_pins[pos], display=self.display)
        
        # initialize tk objects
        """ ROW 1 
        State display
        """
        self.display['state'] = StringVar(value= "init")
        state_label = Label(
            gui,
            textvariable = self.display['state'],
            font= ("Bauhaus 83", 28),
        ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
        )

        """ ROW 2
        1) stepper position display
        2) buttons to go up or down
        """
        y += 50
        self.display['x'] = IntVar(value= 0) # this is to display stepper position value :P
        self.plus_up = PhotoImage(file = "plus_up.png")
        self.plus_down = PhotoImage(file = "plus_down.png")
        self.minus_up = PhotoImage(file = "minus_up.png")
        self.minus_down = PhotoImage(file = "minus_down.png")
        Label(
            gui,
            textvariable= self.display['x'],
            font= ("Bauhaus 83", 28),
            ).place(
            x= x + 100, 
            y= y,
            anchor=S,
            width=100,
            )
        self.minus_button = Button(
            gui, 
            image = self.minus_up, 
            command = self.minus,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.minus_button.place(
            x= x, 
            y= y,
            anchor=SW,
            )
        self.plus_button = Button(
            gui, 
            image = self.plus_up, 
            command = self.plus,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.plus_button.place(
            x= x + 150, 
            y= y,
            anchor=SW,
            )

        

        """ ROW 3 & 4
        x_set entry
        Chase x_set button
        """
        y += 50
        self.display['x_set'] = IntVar(value= 0)
        self.display['x_set'].trace("w", self.x_set_update)

        self.x_set_entry = Entry(
            gui,
            textvariable= self.display['x_set'],
            font= ("Bauhaus 83", 28),
            justify=CENTER,
            borderwidth = 0,
            highlightthickness= 0,

        )
        self.x_set_entry.place(
            x= x + 99, 
            y= y,
            anchor=S,
            width=198,
            height=48
        )

        y += 50
        self.chase_up = PhotoImage(file = "chase_up.png")
        self.chase_down = PhotoImage(file = "chase_down.png")
        self.chase_button = Button(
            gui, 
            image = self.chase_up, 
            command = self.chase,
            borderwidth = 0,
            highlightthickness= 0,
            )
        self.chase_button.place(
            x= x + 99, 
            y= y,
            anchor=S,
            )
        
        
        self.stepper.start()


    def x_set_update(self, *args):
        try:
            self.stepper.x_set = int(self.display['x_set'].get())
        except:
            pass

    def set_all_off(self):
        self.plus_button.config(image= self.plus_up)
        self.minus_button.config(image= self.minus_up)
        self.chase_button.config(image= self.chase_up)
    
    def plus(self):
        if self.stepper.state == "up":
            self.plus_button.config(image = self.plus_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.plus_button.config(image = self.plus_down)
            self.stepper.cmd("up")
    
    def minus(self):
        if self.stepper.state == "down":
            self.minus_button.config(image = self.minus_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.minus_button.config(image = self.minus_down)
            self.stepper.cmd("down")
    def chase(self):
        if self.stepper.state == "chase":
            self.chase_button.config(image = self.chase_up)
            self.stepper.cmd("stop")
        else:
            self.set_all_off()
            self.chase_button.config(image = self.chase_down)
            self.stepper.cmd("chase")



        
   
        
        

        
            


if __name__ == '__main__':

    # Add image file
    lj = U6()
    gui = GUI(lj)
    gui.mainloop()
    