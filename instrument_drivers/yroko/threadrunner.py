'''
This file is the main coordinator of everything happening to the Arduino.
It uses threading to start up TCP/IP ports for each channel
Then, the threads can access and change the global command variables in this terminal
(there is one global command variable for each channel)
When the loop hits a a non-empty string in the global command variable, it executes this command
After it is done executing, it sends the feedback provided to the serial port by the arduino back 
through the TCP/IP port that sent the command, empties the variable, and continues looping.
In this way, one serial port can be accessed and controlled by all 4 TCP/IP ports

TLDR: It makes the ports take turns controlling the Arduino
'''
'''
Addendum: the user interface: 
When the GUI is completed for each channel, they will also access the global command variables
'''
import sys
import serial
import port_lister
import socket
import threading
import time

#Create command variables
global Comm1
global Comm2
global Comm3
global Comm4
global Comm5
global Comm6
global Comm7
global Comm8
global Feedback1
global Feedback2
global Feedback3
global Feedback4
global Feedback5
global Feedback6
global Feedback7
global Feedback8
Comm1 = ''
Comm2 = ''
Comm3 = ''
Comm4 = ''
Comm5 = ''
Comm6 = ''
Comm7 = ''
Comm8 = ''
Feedback1 = ''
Feedback2 = ''
Feedback3 = ''
Feedback4 = ''
Feedback5 = ''
Feedback6 = ''
Feedback7 = ''
Feedback8 = ''

################################################# NETWORKING
def TCP_Thread(num):
    global Comm1
    global Comm2
    global Comm3
    global Comm4
    global Comm5
    global Comm6
    global Comm7
    global Comm8
    global Feedback1
    global Feedback2
    global Feedback3
    global Feedback4
    global Feedback5
    global Feedback6
    global Feedback7
    global Feedback8

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    port_num = 10000+num
    # Bind the socket to the port
    server_address = ('', port_num)
    print >>sys.stderr, 'starting up on %s port %s' % server_address
    sock.bind(server_address)
    # Listen for incoming connections
    sock.listen(1)
    # Wait for a connection
    while True: #BIG loop
	try:
            connection, client_address = sock.accept()
            #print >>sys.stderr, 'Channel '+str(num)' received connection from '+client_address
            
            # Receive the data in chunks (all messages should be <64 bytes) and retransmit it
            while True:
                print >>sys.stderr, 'Channel '+str(num)+' listening...'
                data = connection.recv(64)
                print >>sys.stderr, 'Channel '+str(num)+' received "%s"' % data
                if data: #1 if theres stuff in the string, Returns '' (which is read as False) when the connection is closed client-side
		    if num == 1:
                        Comm1 = data
                        #print >>sys.stderr, 'Channel '+str(num)+' changed Comm1 to: '+Comm1
                    elif num == 2:
                        Comm2 = data
                    elif num == 3:
                        Comm3 = data
                    elif num == 4:
                        Comm4 = data
                    elif num == 5:
                        Comm5 = data
                    elif num == 6:
                        Comm6 = data
                    elif num == 7:
                        Comm7 = data
                    elif num == 8:
                        Comm8 = data
                    print >>sys.stderr, 'Channel '+str(num)+' waiting for feedback...'
                    #this changes the right command variable to the received message
                    #after this, the MAIN LOOOP below detects this change, but the time taken is unknown...(depends on other channels)
                    #so we have to wait for the command to be executed
                    #we will know when the command is executed by the appropriate global feedback variable changing
                    counter = 0
                    while eval('Feedback'+str(num))=='':
		    	#here is where something can go wrong in the main loop, and we have to build in a timeout
		    	#the largest voltage swing possible is -10 to 10, which would
		    	#take just over 200s, so if more than that goes by something is wrong and the client needs to know
                        time.sleep(10e-3) #check back periodically
                        counter+=1
                        if counter == 22000: #220s
                            connection.sendall('ERROR: TIMEOUT')
                            counter = 0
                            break;
		    #if the feedback variable DOES change, everything is fine so we send the info back to the client
                    print >>sys.stderr, 'Ch '+str(num)+' sending feedback back to the client (message: '+eval('Feedback'+str(num))+')'
                    connection.sendall(eval('Feedback'+str(num)))
                    #reset the feedback variable
		    if num == 1:
                        Feedback1 = ''
                        #print >>sys.stderr, 'Channel '+str(num)+' changed Comm1 to: '+Comm1
                    elif num == 2:
                        Feedback2 = ''
                    elif num == 3:
                        Feedback3 = ''
                    elif num == 4:
                        Feedback4 = ''
		    elif num == 5:
                        Feedback5 = ''
                        #print >>sys.stderr, 'Channel '+str(num)+' changed Comm1 to: '+Comm1
                    elif num == 6:
                        Feedback6 = ''
                    elif num == 7:
                        Feedback7 = ''
                    elif num == 8:
                        Feedback8 = ''
                else:
                    #the only way this gets triggered is if the client has closed the connection. So we need to break out of this loop to reconnect
                    #but before we break, we must clean up the TCP_IP port. or nothing will be able to reconnect
                    connection.close()
                    print >>sys.stderr,"Disconnected from "+str(client_address)
                    break #break out of this smaller loop
        except: #this most likely means the connection has been terminated in a non-standard way
            #the best move in that case is to close the connection on the server and reopen it to allow you to get back in
            connection.close()
######################################################   UTILITIES (ARDUINO)

def listen():  #This just reads out what is in the Serial buffer
        arduinoData = ""
        i = 0
        while i<=10: #this number is also critical, this is the limit of how many lines can be read out of the serial buffer, lines are marked with EOL strings like '\n'
            arduinoData += ser.readline().decode('ascii')
            time.sleep(1e-3)
            i+= 1
        return arduinoData

def generalCommandListen(command):
	ser.open()
        ser.reset_input_buffer()
#        print("port opened")
        fullComm = bytearray(command+"\r","ascii")
        ser.write(fullComm)
#        print("command sent, reading response")
        time.sleep(2e-3)
        data = listen() #collect stuff out of serial buffer
        ser.close()
#        print("port closed")
        return data


def commExecuter(CommX, channel): #takes in any command and executes it on the proper channel
    if CommX == '':
        return ''
    elif CommX =='STOP':
        #build in a way to halt everything in place?
        pass
    elif CommX =='STOP_ALL':
        pass
    else:
        print >>sys.stderr, "Executing "+CommX
        #print >>sys.stderr, "TROUBLE: "+CommX[0:4]
        if CommX[0:4] == 'RAMP': #then we should execute and wait for the expected amount of time, THEN return the feedback
            generalCommandListen(CommX) #this starts the ramp, but we dont care about the feedback because is just echoes what we sent
            time_estimate = float(CommX.split(',')[-1])*float(CommX.split(',')[-2])/1e6 #time given was in microseconds, divide that back out for s
            print >>sys.stderr, 'Waiting '+str(time_estimate)+ ' seconds for ramp completion...'
            time.sleep(time_estimate*1.05) #waits 5% extra juuuuuuust in case
            feedback = 'RAMP_FINISHED'
        else: #this is pretty much just getting current values
            feedback = generalCommandListen(CommX)
        return feedback

#################################################### MAIN LOOP

#connect to Arduino
port = "/dev/ttyACM0" #this is the default that the arduino connects to on device boot, otherwise use ports_lister
global ser
ser = serial.Serial(port, baudrate = 115200, timeout = 0.001)
startup = listen()
ser.close()
print ('Startup Message: '+startup) #nothing is the best case here

#Start the threads for each port
port1 = threading.Thread(target = TCP_Thread, args = (1,))
port1.start()
port2 = threading.Thread(target = TCP_Thread, args = (2,))
port2.start()
port3 = threading.Thread(target = TCP_Thread, args = (3,))
port3.start()
port4 = threading.Thread(target = TCP_Thread, args = (4,))
port4.start()

# MANUAL CONTROL PORTS
port5 = threading.Thread(target = TCP_Thread, args = (5,))
port5.start()
port6 = threading.Thread(target = TCP_Thread, args = (6,))
port6.start()
port7 = threading.Thread(target = TCP_Thread, args = (7,))
port7.start()
port8 = threading.Thread(target = TCP_Thread, args = (8,))
port8.start()

comm = 1
while True:
	if comm == 1:
		#print("Main Loop checking Comm1: "+Comm1)
                Feedback1 = commExecuter(Comm1,1)
                Comm1 = ''
	elif comm == 2:
                #print("Main Loop checking Comm2: "+Comm2)
		Feedback2 = commExecuter(Comm2,2)
                Comm2 = ''
	elif comm == 3:
                #print("Main Loop checking Comm3: "+Comm3)
		Feedback3 = commExecuter(Comm3,3)
                Comm3 = ''
	elif comm == 4:
                #print("Main Loop checking Comm4: "+Comm4)
		Feedback4 = commExecuter(Comm4,4)
                Comm4 = ''
############################################################### MANUAL CHANNELS BELOW
	elif comm == 5:
		#print("Main Loop checking Comm1: "+Comm1)
                Feedback5 = commExecuter(Comm5,1)
                Comm5 = ''
	elif comm == 6:
                #print("Main Loop checking Comm2: "+Comm2)
		Feedback6 = commExecuter(Comm6,2)
                Comm6 = ''
	elif comm == 7:
                #print("Main Loop checking Comm3: "+Comm3)
		Feedback7 = commExecuter(Comm7,3)
                Comm7 = ''
	elif comm == 8:
                #print("Main Loop checking Comm4: "+Comm4)
		Feedback8 = commExecuter(Comm8,4)
                Comm8 = ''
	else:
		comm = 0
                time.sleep(0.02)
	comm +=1


