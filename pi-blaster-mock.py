#!/usr/bin/python3
# Copyright (c) 2016 Sebastian Kanis
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import tkinter
import threading
from multiprocessing import Queue
from queue import Empty
import signal
import sys

VIRTUAL_DEVICE_PATH = "/dev/pi-blaster"
#interval of the virtual device checker in seconds
COLOR_UPDATER_SLEEPTIME=0.01
#interval of the UI queue evaluation in milliseconds (should be in sync with COLOR_UPDATER_SLEEPTIME)
UI_COM_QUEUE_CHECK_INTERVAL=10
#the GPIO pins used for the different colors
RED_PIN=17
GREEN_PIN=22
BLUE_PIN=24

#helper to get HEX value for UI from RGB value
def RGBToHex(r,g,b):
    return format(r<<16 | g<<8 | b, '06x')

#helper to check if a string is a float
def isFloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

#UI class
class UI(tkinter.Tk):

    #currently shown colors
    currentRed = 0
    currentGreen = 0
    currentBlue = 0

    #queue for communication between virtual device listening thread and UI thread
    queue = None
    
    def __init__(self,parent):
        tkinter.Tk.__init__(self,parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        
        #add app icon
        img = tkinter.PhotoImage(file='logo.png')
        self.tk.call('wm', 'iconphoto', self._w, img)

        #react to CTRL+c in UI Window
        self.bind('<Control-c>', lambda event: cleanUpAndExit(None,None))
        self.grid()
       
        #init red label
        self.redLabelVariable = tkinter.StringVar()
        self.redLabel = tkinter.Label(self,textvariable=self.redLabelVariable, anchor="w", fg="black", height=5)
        self.redLabel.grid(column=0,row=0,sticky='EW')
        colorString = "no color set yet"
        self.redLabelVariable.set(colorString)

        #init green label
        self.greenLabelVariable = tkinter.StringVar()
        self.greenLabel = tkinter.Label(self,textvariable=self.greenLabelVariable, anchor="w", fg="black", height=5)
        self.greenLabel.grid(column=1,row=0,sticky='EW')
        self.greenLabelVariable.set(colorString)

        #init blue label
        self.blueLabelVariable = tkinter.StringVar()
        self.blueLabel = tkinter.Label(self,textvariable=self.blueLabelVariable, anchor="w", fg="black", height=5)
        self.blueLabel.grid(column=2,row=0,sticky='EW')
        self.blueLabelVariable.set(colorString)

        #init label for combined colors
        self.labelVariable = tkinter.StringVar()
        self.label = tkinter.Label(self,textvariable=self.labelVariable,
                                   anchor="center",fg="black", height=5, justify=tkinter.CENTER)
        self.label.grid(column=0, columnspan=3,row=1,sticky='EW')
        self.labelVariable.set(colorString)

        
        self.grid_columnconfigure(0,weight=1)
        self.grid_columnconfigure(1,weight=1)
        self.grid_columnconfigure(2,weight=1)
        self.grid_rowconfigure(1, weight=1)
        #self.minsize(width=300, height=300)
        #self.maxsize(width=300, height=300)
        self.resizable(True, True)
        self.update()
        self.geometry(self.geometry())

    #set a single color to a specified value
    def setColor(self, color, value, printInfo=False):
        value = min(255, max(0, round(value*255)))
        if color == "red":
            self.currentRed = value
        elif color == "green":
            self.currentGreen = value
        elif color == "blue":
            self.currentBlue = value
        formattedOutput = "red: {}, green: {}, blue: {}".format(self.currentRed, self.currentGreen, self.currentBlue)
        if printInfo:
            print(formattedOutput,flush=True)
        #update the label
        self.labelVariable.set(formattedOutput)
        #update the combined label
        fgLabel = ("white" if (self.currentRed + self.currentGreen + self.currentBlue) < 128 else "black")
        self.label.configure(bg="#"+RGBToHex(self.currentRed, self.currentGreen, self.currentBlue), fg=fgLabel)
        self.configure(bg="#"+RGBToHex(self.currentRed, self.currentGreen, self.currentBlue))

        #update the red label
        redFg = ("white" if self.currentRed < 128 else "black")
        self.redLabel.configure(bg="#"+RGBToHex(self.currentRed, 0,0), fg=redFg)
        self.redLabelVariable.set("red: {}".format(self.currentRed))
        #update the green label
        greenFg = ("white" if self.currentGreen < 128 else "black")
        self.greenLabel.configure(bg="#"+RGBToHex(0, self.currentGreen,0), fg=greenFg)
        self.greenLabelVariable.set("green: {}".format(self.currentGreen))
        #update the blue label
        blueFg = ("white" if self.currentBlue < 128 else "white")
        self.blueLabel.configure(bg="#"+RGBToHex(0, 0, self.currentBlue), fg=blueFg)
        self.blueLabelVariable.set("blue: {}".format(self.currentBlue))
                
    #init thread monitoring the virtual device and queue for communication with it
    def initColorUpdater(self):
        self.queue = Queue()
        colorUpdater = ColorUpdater(self.queue)
        #start thread as deamon to stop it on exit signal
        colorUpdater.daemon = True
        colorUpdater.start()
        #check the queue for input form the monitoring thread
        self.after(UI_COM_QUEUE_CHECK_INTERVAL, self.updateColor)

    #checks if the thread monitoring the virtual device has written data to the queue
    def updateColor(self, printInfo=False):
        try:
            msg = self.queue.get(0)
            #check which color needs to be updated
            if msg.startswith(str(RED_PIN) + "="):
                value = msg[len(str(RED_PIN))+1:]
                if isFloat(value):
                    if printInfo:
                        print("updateColor: updating red: {}".format(value))
                    self.setColor("red", float(value), printInfo)
            elif msg.startswith(str(GREEN_PIN) + "="):
                value = msg[len(str(GREEN_PIN))+1:]
                if isFloat(value):
                    if printInfo:
                        print("updateColor: updating green: {}".format(value))
                    self.setColor("green", float(value), printInfo)
            elif msg.startswith(str(BLUE_PIN) + "="):
                value = msg[len(str(BLUE_PIN))+1:]
                if isFloat(value):
                    if printInfo:
                        print("updateColor: updating blue: {}".format(value))
                    self.setColor("blue", float(value), printInfo)
        except Empty:
            pass
        #reschedule execution of the UI update
        self.after(UI_COM_QUEUE_CHECK_INTERVAL, self.updateColor)

#Thread to monitor the virtual input device        
class ColorUpdater(threading.Thread):
    def __init__(self, resultQueue):
        threading.Thread.__init__(self)
        self.resultQueue = resultQueue
        
    def run(self):
        pipeIn = open(VIRTUAL_DEVICE_PATH, 'r')
        while True:
            time.sleep(COLOR_UPDATER_SLEEPTIME)
            #only reads one line every COLOR_UPDATER_SLEEPTIME if more input is given it is not processed in realtime
            line = pipeIn.readline()[:-1]
            if len(line) > 0:
                self.resultQueue.put(line)


def initInput():
    #create the virtual device (FIFO) if nonexistent
    if not os.path.exists(VIRTUAL_DEVICE_PATH):
        os.mkfifo(VIRTUAL_DEVICE_PATH)  
    os.chmod(VIRTUAL_DEVICE_PATH, 442)

def cleanUpAndExit(signal, frame):
    print('Cancelled!')
    #remove the virtual device (FIFO) if existent
    if os.path.exists(VIRTUAL_DEVICE_PATH):
        os.remove(VIRTUAL_DEVICE_PATH)
    sys.exit(0)

initInput()
#react to CTRL+C in the command line
signal.signal(signal.SIGINT, cleanUpAndExit)
app = UI(None)
app.title('pi-blaster rgb mock')
app.after(0, app.initColorUpdater)
app.mainloop()
