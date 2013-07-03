#!/usr/bin/env python
from radiora import *
from Tkinter import *

radiora = Controller('10.0.1.44', 'lutron', 'integration')
house = House(radiora)
house.load()



class App:
    def __init__(self, master):
        frame = Frame(master, width=250)
        frame.pack()
	def onselection(arg):
		room = roomchooser.get(roomchooser.curselection()[0])
		loadchooser.delete(0, END)
		for output in house.findRoom(roomchoice()).listOutputs():
			loadchooser.insert(END, output)
		loadchooser.insert(END, 'All')
		loadchooser.select_set(END)
	roomchooser = Listbox(master, exportselection=0)
	roomchooser.pack()
	roomchooser.bind('<<ListboxSelect>>', onselection)
	for room in house.listRooms():
		roomchooser.insert(END, room)
	def roomchoice():
		return roomchooser.get(roomchooser.curselection()[0])
	def loadchoice():
		return loadchooser.get(loadchooser.curselection()[0])
	def setroom(value):
		if loadchoice() == 'All':
			house.findRoom(roomchoice()).Set(value)
		else:
			house.findRoom(roomchoice()).findOutput(loadchoice()).Set(value)
	loadchooser = Listbox(master, exportselection=0)
	loadchooser.pack()
        self.high = Button(frame, text="100%", command = lambda: setroom(100))
        self.high.pack()
        self.medhigh = Button(frame, text="75%", command = lambda: setroom(75))
        self.medhigh.pack()
	self.med = Button(frame, text="50%", command = lambda: setroom(50))
        self.med.pack()
        self.low = Button(frame, text="25%", command = lambda: setroom(25))
        self.low.pack()
	self.off = Button(frame, text="Off", fg="red", command = lambda: setroom(0))
        self.off.pack()


root = Tk()
root.wm_title("RadioRA 2")
root.geometry("200x450")
app = App(root)
root.mainloop()
