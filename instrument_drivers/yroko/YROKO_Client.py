# -*- coding: utf-8 -*-

"""
A driver to control the Modular DAC using Qtlab

@author: Hatlab - Ryan Kaufman
"""

from qcodes import Instrument
import qcodes.utils.validators as vals
import tkinter as tk
import tkinter.font as tkFont
import random
import logging
#from instrument import Instrument
import socket
import sys
import time

class YROKO(Instrument): 

    def __init__(self, name: str, IP = '169.254.6.22'):
        
        '''
        Initializes the YROKO
        - Uses YROKO TCP/IP socket. IP: 169.254.6.22 on Texas Switch
        - Port depends on the channel you would like to use. Each channel is run seperately on its own TCP/IP Socket
        '''
        self.IP = IP
        super().__init__(name)
        self.ch1_true_zero = -0.00106811e-3 #this is an offset that was tuned to make sure that there was no jumping when you plug in the magnet. 
        self.ch2_true_zero = -0.00106811e-3
        self.ch3_true_zero = 0
        self.resistance = 1000
        self.add_parameter('current', 
                           get_cmd = self.get_current, 
                           set_cmd = self.change_current, 
                           unit = 'A', 
                           vals=vals.Numbers(-10e-3, 10e-3), 
                           )
        self.TCP_Connect(name)
        
        print("Offsetting to true zero...")
        if name == 'YROKO1': 
            self.true_zero = self.ch1_true_zero
        elif name == 'YROKO1': 
            self.true_zero = self.ch2_true_zero
        elif name == 'YROKO2': 
            self.true_zero = self.ch3_true_zero

        self.change_current(self.true_zero)
        print("Offset complete, safe to plug in")
        
        #initializing a current parameter

        
    def TCP_Connect(self, name): 
        namelist = {'YROKO1':(1,10001),
                    'YROKO2':(2,10002),
                    'YROKO3':(3,10003),
                    }
        if name in namelist: 
            
            self.channel = namelist[name][0]-1 #arduino counts from 0, but we think starting at 1 :(
            port = namelist[name][1]
            
            
            # Create a TCP/IP connection
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect the socket to the port where the server is listening
            server_address = (self.IP, port) #this IP is only a specific location in the Texas Switch. Have to develop means of detection
            print (sys.stderr, 'Connecting to '+str(server_address[0]) +' port '+str(port) +' (YROKO channel '+str(self.channel)+')')
            self.sock.connect(server_address)
            print("Connection successful")
            #now get initial current:
            #unknown current indicated by 'U' so if that sticks around something is *seriously* fucked up
            print('YROKO channel '+str(self.channel)+' current: '+str(self.current()*1000)+'mA')
            print("Initialization Process Complete\n")
        else:
            raise Exception("Channel Requested Doesn't exist... Pick One: (YROKO1,YROKO2,YROKO3)") 
            
    def TCP_Exchange(self,message, wait = True): #framework for sending a message and waiting for a response
        feedback = ''
        print ("Sending: "+message)
        self.sock.sendall(bytes(message, 'utf-8'))
        #the system will wait until it receives something. So the server must send something for the client to be able to respond
        if wait:
            feedback = self.sock.recv(64)
        else: 
            feedback = b''
        # print("feedback from server: ", feedback)
        return str(feedback)

    def get_current(self): 
        feedback = self.TCP_Exchange('GET_DAC,'+str(self.channel))
#        print("Raw Feedback: "+feedback)
        feedback_split = feedback.split(r'\n')
        # print("Split Feedback: "+str(feedback_split))
        voltage = float(feedback_split[-2][:-2])
        
        return voltage/self.resistance

    def change_current(self, new_current, ramp_rate = None):
        if ramp_rate == None: 
            ramp_rate = 0.1
        old_current = self.current()
        old_voltage = old_current*self.resistance
        new_voltage = new_current*self.resistance
        if abs(new_voltage) > 10: 
            raise Exception("This device can't deliver more than 10mA in either direction")
        min_precision_value = 0.156e-3 #Volts - from data sheet of EVAL board
        time_step = 1.02*min_precision_value/ramp_rate #"Seconds between successive discrete voltage changes, its a digital system so it's non-continuous, 
        #i.e. this value is set so that for any deltaV,the step is the max precision of 15.25 mv and ramps at 0.1V/s, then with an added 2% safety zone"
        num_steps = int(abs(new_voltage-old_voltage)/min_precision_value) #int truncates, which in numbers > 0 is rounding dowm, so it will be slightly less precise
        message = "RAMP1,"+str(self.channel)+","+str(old_voltage)+","+str(new_voltage)+","+str(num_steps)+","+str(float(time_step*1e6))
        time_estimate = time_step*num_steps
        print("Time to ramp channel "+str(self.channel)+" to "+str(new_current*1000)+" mA: "+str(time_estimate)+"s")        
        print("Sending command and awaiting ramp completion...")        
        ramp_conf = self.TCP_Exchange(message) #This would ideally send back RAMP_FINISHED
        print("Ramp_Confirmation: "+ramp_conf)        
        print("Updating current value... ")
        time.sleep(0.01) #give the server-side time to reset the feedback variable
        new_current = self.get_current()
        print("Verified current: "+str(new_current)+'mA')
        return new_current
    def shutdown(self): 
        #as a final command, always 0 out current: 
        self.change_current(0)
        self.sock.close()
        print("Current zeroed, socket closed, shutdown complete. \nUnplugging channel "+str(self.channel+1)+' is safe now')
        
        
#    ################################################################################################   GUI Class
        
# class YROKO_GUI(): 
    
#     def __init__(self, name): 
#         self.ch1_true_zero = -0.00106811e-3 #this is an offset that was tuned to make sure that there was little jumping when you plug in the magnet. 
#         self.ch2_true_zero = -0.00106811e-3
#         self.ch3_true_zero = 0
#         '''
#         Initializes the YROKO
#         - Uses YROKO TCP/IP socket. IP: 169.254.6.22 on Texas Switch
#         - Port depends on the channel you would like to use. Each channel is run seperately on its own TCP/IP Socket
#         '''
#         self.resistance = 1000     
#         self.TCP_Connect(name)
        
#         '''
#         Now we boot up the GUI part, this is what's slightly different about this file. Instead of typing all the commands in manually
#         we call them using buttons
#         '''
#         self.setup() #now we can offset
#         print("Offsetting to true zero...")
#         if name == 'YROKO1': 
#             self.true_zero = self.ch1_true_zero
#         elif name == 'YROKO1': 
#             self.true_zero = self.ch2_true_zero
#         elif name == 'YROKO2': 
#             self.true_zero = self.ch3_true_zero

#         self.change_current(self.true_zero)
#         print("Offset complete, safe to plug in")
#         self.current = self.get_current()
#         print('updating GUI with current of: '+str(self.get_current()))
#         self.run_GUI()
        
# ######################################################################################### Regular YROKO functions
        
#     def TCP_Connect(self, name): 
#         '''
#         Notice that the ports are different here! in the regular YROKO file the ports are 10001, 10002, 10003
#         In this way, the 'manual' interface is actually just as remote as before. except since the threadrunner.py is still only opening a localhost port, 
#         the GUI can still only be run on the Pi itself. All that you would need to do to change that is pick the ip that the Pi is on as the target address
#         '''
#         namelist = {'YROKO1':(1,10005),
#                     'YROKO2':(2,10006),
#                     'YROKO3':(3,10007),
#                     }
#         if name in namelist: 
            
#             self.channel = namelist[name][0]-1 #arduino counts from 0, but we think starting at 1 :(
#             port = namelist[name][1]
            
#             # Create a TCP/IP connection
#             self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             # Connect the socket to the port where the server is listening
#             server_address = ('169.254.6.22', port) #this IP is only a specific location in the Texas Switch. Have to develop means of detection
#             print >>sys.stderr, 'Connecting to '+str(server_address[0]) +' port '+str(port) +' (YROKO channel '+str(self.channel+1)+')'
#             self.sock.connect(server_address)
#             print("Connection successful")
#             #now get initial current:
#             #unknown current indicated by 'U' so if that sticks around something is seriously fucked up
#             self.current = 'U'
#             print("Getting Current(Outside)")
#             self.current = self.get_current(update_GUI = False)
#             print("Current: "+str(self.current))
#             print('YROKO channel '+str(self.channel+1)+' current: '+str(self.current*1000)+'mA')
#             print("Initialization Process Complete\n")
#         else:
#             raise Exception("Channel Requested Doesn't exist... Pick One: (YROKO1,YROKO2,YROKO3)")    
            
#     def TCP_Exchange(self,message, wait = True): #framework for sending a message and waiting for a response
#         feedback = ''
#         print ("Sending: "+message)
#         self.sock.sendall(message)
#         #the system will wait until it receives something. So the server must send something for the client to be able to respond
#         if wait:     
#             feedback = self.sock.recv(64)
#         else: 
#             feedback = ''
#         return feedback

#     def get_current(self, update_GUI = True): 
#         print >>sys.stderr, "Now getting current..."
#         feedback = self.TCP_Exchange('GET_DAC,'+str(self.channel))
# #        print("Raw Feedback: "+feedback)
#         feedback_split = feedback.split('\n') 
#         print("Split Feedback: "+str(feedback_split))
#         voltage = float(feedback_split[-2][:-2])
#         #GUI Addition
#         if update_GUI:
#             self.current_string.set(str(voltage/self.resistance*1000)+'mA')
#         return voltage/self.resistance

#     def change_current(self, new_current, ramp_rate = 0.1):
#         old_current = self.get_current()
#         old_voltage = old_current*self.resistance
#         new_voltage = new_current*self.resistance
#         if abs(new_voltage) > 10: 
#             raise Exception("This device can't deliver more than 10mA in either direction")
#         if abs(new_current-old_current) <= 1.1e-6: #this is going to be considered small enough to just step the current directly: 
#             feedback = self.TCP_Exchange("SET,"+str(self.channel)+","+str(new_voltage))
#             print("Feedback from SET: "+feedback)
#             feedback_split = feedback.split('\n') 
#             print("Split Feedback: "+str(feedback_split))
#             new_current = self.get_current()
#             #update GUI
#             self.current_string.set(str(new_current*1000)+'mA')
#             return new_current
#         else: 
#             min_precision_value = 0.156e-3 #Volts - from data sheet of EVAL board
#             time_step = 1.02*min_precision_value/ramp_rate #"Seconds between successive discrete voltage changes, its a digital system so it's non-continuous, 
#             #i.e. this value is set so that for any deltaV,the step is the max precision of 15.25 mv and ramps at 0.1V/s, then with an added 5% safety zone"
#             num_steps = int(abs(new_voltage-old_voltage)/min_precision_value) #int truncates, which in numbers > 0 is rounding dowm, so it will be slightly less precise
#             message = "RAMP1,"+str(self.channel)+","+str(old_voltage)+","+str(new_voltage)+","+str(num_steps)+","+str(float(time_step*1e6))
#             time_estimate = time_step*num_steps
#             print("Time to ramp channel "+str(self.channel)+" to "+str(new_current*1000)+" mA: "+str(time_estimate)+"s")        
#             print("Sending command and awaiting ramp completion...")        
#             ramp_conf = self.TCP_Exchange(message) #This would ideally send back RAMP_FINISHED
#             print("Ramp_Confirmation: "+ramp_conf)        
#             print("Updating current value... ")
#     #        time.sleep(0.01) #give the server-side time to reset the feedback variable
#             new_current = self.get_current()
#             print("Verified current: "+str(new_current*1000)+'mA')
#             return new_current
    
#     def shutdown(self): 
#         #as a final command, always 0 out current: 
#         self.change_current(0)
#         self.sock.close()
#         print("Current zeroed, socket closed, shutdown complete. \nUnplugging channel "+str(self.channel+1)+' is safe now')
        
# ######################################################################################### GUI Functions
#     def setup(self): 
#         self.master = tk.Tk()
#         #detecting screen size
#         screen_width = self.master.winfo_screenwidth()
#         screen_height = self.master.winfo_screenheight()
#         #open in different locations depending on channel
#         if self.channel == 0: 
#             geoArg = str(int(screen_width/2))+'x'+str(int(screen_height/2))+'+0+0'
#         elif self.channel == 1: 
#             geoArg = str(int(screen_width/2))+'x'+str(int(screen_height/2))+'+'+str(int(screen_width/2))+'+0'
#         elif self.channel == 2: 
#             geoArg = str(int(screen_width/2))+'x'+str(int(screen_height/2))+'+0+'+str(int(screen_height/2))
#         elif self.channel == 3: 
#             geoArg = str(int(screen_width/2))+'x'+str(int(screen_height/2))+'+'+str(int(screen_width/2))+'+'+str(int(screen_height/2))
#         else: 
#             geoArg = str(int(screen_width/2))+'x'+str(int(screen_height/2))
#         self.master.geometry(geoArg)
        
#         self.master.grid()
#         #build the GUI using the utility functions below
        
#         #make title
#         helv = tkFont.Font(family='Helvetica', size=int(self.master.winfo_screenwidth()/40), weight='bold')
#         title = tk.Label(self.master, text= 'Channel '+str(self.channel+1)+' Control', font = helv)
#         title.grid(row = 0, column = 0, columnspan = 6)
#         #Making literally everything else
#         self.button_array(self.master, 1,0)

        
#     def run_GUI(self): 
#         self.master.mainloop()
        
#     def kill_GUI(self): #A bit dark, but it gets the job done
#         self.shutdown()
#         self.master.destroy()
        
#     def current_bump_button_maker(self,current_change, root, loc):
#         '''
#         this is a convenience thing to create a button that will adjust a given 
#         channel's current by binding a specific call of the change_current function (bump current)
#         '''
#         def bump_current(amount): #helping function that is required because of how tkinter buttons work http://effbot.org/zone/tkinter-callbacks.htm
#             prev_current = self.get_current()
#             desired_current = prev_current + amount
#             self.change_current(desired_current)
#             print("current changed by "+str(amount))
#             return None
#         #aesthetic things
#         if current_change > 0: 
#             if current_change >= 10e-6: 
#                 buttontext = "+"+str(current_change*1000)+'mA'
#                 bgcolor = '#08e800'
#             else: 
#                 buttontext = "+"+str(current_change*1000000)+'uA'
#                 bgcolor = '#08e800'
#         else:
#             if abs(current_change) >= 10e-6: 
#                 buttontext = str(current_change*1000)+'mA'
#                 bgcolor = '#ff2b75'
#             else: 
#                 buttontext = str(current_change*1000000)+'uA'
#                 bgcolor = '#ff2b75'
            
#         helv = tkFont.Font(family='Helvetica', size=int(self.master.winfo_screenwidth()/85), weight='bold')
        
#         button = tk.Button(root, text = buttontext, command = lambda: bump_current(current_change), bg = bgcolor, font = helv)
#         button.grid(row = loc[0],column = loc[1], rowspan = 2)
#         return button
    
#     def button_array(self,root,rowstart,colstart):
#         '''
#         This function is doing most of the work of building the UI. It creates the clickable (touchable) buttons to adjust the current value
#         '''
#         ###################### ROW 1 - add current
#         #go from larger magnitude(left) to smmallest magnitude (right)
            
#         plus_1000 = self.current_bump_button_maker(1e-3, root, [rowstart,colstart])
        
#         plus_100 = self.current_bump_button_maker(1e-4, root, [rowstart,colstart+1])

#         plus_10 = self.current_bump_button_maker(1e-5, root, [rowstart,colstart+2])
        
#         plus_1 = self.current_bump_button_maker(1e-6, root, [rowstart,colstart+3])
        
#         plus_half = self.current_bump_button_maker(5e-7, root, [rowstart,colstart+4])
        
#         ##################### ROW 2 - The display
#         #make current label. This is actually the easy part, as labels in the mainloop() will automatically update
#         self.current_string = tk.StringVar() #this is the special BS you need to use for tkinter to update the label
#         helv = tkFont.Font(family='Helvetica', size=self.master.winfo_screenwidth()/35, weight='bold')
#         self.currLabel = tk.Label(root, textvariable = self.current_string, font = helv)
#         self.currLabel.grid(row = rowstart+2, column = colstart +0 , columnspan = 6)
        
#         ##################### ROW 3 - subtract current
#         minus_1000 = self.current_bump_button_maker(-1e-3, root, [rowstart+3,colstart])
        
#         minus_100 = self.current_bump_button_maker(-1e-4, root, [rowstart+3,colstart+1])

#         minus_10 = self.current_bump_button_maker(-1e-5, root, [rowstart+3,colstart+2])
        
#         minus_1 = self.current_bump_button_maker(-1e-6, root, [rowstart+3,colstart+3])
        
#         minus_half = self.current_bump_button_maker(-5e-7, root, [rowstart+3,colstart+4])
#         #################### ROW 4 - Update , zero and shutdown button
        
#         helv = tkFont.Font(family='Helvetica', size=int(self.master.winfo_screenwidth()/80), weight='bold')
        
#         update_button = tk.Button(root, text = "Update", command = lambda: self.get_current(), bg = '#00ffff', font = helv)
#         update_button.grid(row = rowstart+5,column = colstart+0, rowspan = 2)
        
#         zero_button = tk.Button(root, text = "Zero", command = lambda: self.change_current(0), bg = '#ff2b75', font = helv)
#         zero_button.grid(row = rowstart+5,column = colstart+1, rowspan = 2)
        
#         shutdown_button = tk.Button(root, text = "Shutdown", command = lambda: self.kill_GUI(), bg = '#ff2b75', font = helv)
#         shutdown_button.grid(row = rowstart+5,column = colstart+2, rowspan = 2, columnspan = 2)
        
        

