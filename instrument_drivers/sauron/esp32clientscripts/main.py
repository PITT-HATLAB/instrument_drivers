import network
import time

#initialize wifi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.config(pm=wlan.PM_NONE)
time.sleep(3)

def wlan_connect(user='rpi_hatlab',pwd='rpi_hatlab'):
        if wlan.isconnected():
                print("connected to rasp pi")
        else:
                print("trying to connect to pi")
                wlan.connect(user,pwd)
                time.sleep(5)
                wlan_connect()

#connect to wifi
wlan_connect()

# set some GPIO pins purely for diagnostics
from machine import Pin
p0 = Pin(13,Pin.OUT)
p1 = Pin(12,Pin.OUT)
p3 = Pin(14, Pin.OUT)
p3.value(1)
p0.value(0)
p1.value(0)
print("active")

# Start measurments and publishing
execfile('ADS_singleshot_singlepub_timestamped.py')
