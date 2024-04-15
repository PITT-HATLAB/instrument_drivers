# This client script publishes datetime tuple with each data point. The time is also updated every set interval by querying an NTP server (Pi is runnign an NTP server in this case)
#

from machine import SoftI2C
from machine import RTC
from time import sleep_ms, time_ns
from ADS1115 import *
import socket
import gc
import ntpupdate

# pull in correct time
ntpupdate.settime(timezone=0, server='192.168.4.1')

# SETUP ADS
ADS1115_ADDRESS = 72

i2c = SoftI2C(scl=22,sda=21)
adc = ADS1115(ADS1115_ADDRESS, i2c=i2c)
adc.setVoltageRange_mV(ADS1115_RANGE_6144)
adc.setCompareChannels(ADS1115_COMP_0_GND)
adc.setConvRate(ADS1115_860_SPS)
adc.setMeasureMode(ADS1115_SINGLE)

def readChannel_sing(channel):
  adc.setCompareChannels(channel)
  adc.startSingleMeasurement()
  while adc.isBusy():
    pass
  voltage = adc.getRawResult() #adc.getResult_mV()
  return voltage

def read_all():
  voltage0 = readChannel_sing(ADS1115_COMP_0_GND)
  voltage1 = readChannel_sing(ADS1115_COMP_1_GND)
  voltage2 = readChannel_sing(ADS1115_COMP_2_GND)
  voltage3 = readChannel_sing(ADS1115_COMP_3_GND)
  return f'{voltage0:06d}', f'{voltage1:06d}', f'{voltage2:06d}', f'{voltage3:06d}'


# SETUP COMMUNICATION PARAMETERS WITH PI
def soc_con(addr="192.168.4.1", port=65433, wifi_user = 'rpi_hatlab', wifi_pwd = 'rpi_hatlab'):

  while True:
    if wlan.isconnected():
      try:
        s = socket.socket()
        # s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) #disable Nagle's Algo for no lags in TCP packets
        s.connect((addr, port))
        break
      except:
        s.close()
        sleep_ms(1000)
        print("Retrying socket connection")
    else:
      wlan_connect(wifi_user,wifi_pwd)
      print("WiFi disconnected. Trying to get back on WiFi")
      time.sleep(5)
  return s


s = soc_con()
meas_t_ms = 1000 #must divide com_delay_sec
v0,v1,v2,v3 = read_all() #reject first data
time_stop, time_start = 0,0

hour = RTC().datetime()[4]

while True:
  sleep_ms(meas_t_ms- int((time_stop-time_start)//1e6)) #correct for the time taken in measurement and sending data
  time_start = time_ns()
  gc.collect()

  v0,v1,v2,v3 = read_all()

  dt = RTC().datetime()
  dt_tuple = f'({dt[0]:04d}. {dt[1]:02d}. {dt[2]:02d}. {dt[3]:01d}. {dt[4]:02d}. {dt[5]:02d}. {dt[6]:02d}. {dt[7]:06d})'
  buffer_str = f'{dt_tuple}, {v0}, {v1}, {v2}, {v3},'# total length = 70

  try:
    s.sendall(buffer_str.encode('utf-8'))
    print(f"## sent {len(buffer_str)} bytes ##\n")
  except OSError:
    s.close()
    s = soc_con()

  if abs(RTC().datetime()[4]-hour) > 1:
    ntpupdate.settime(timezone=0, server='192.168.4.1')
    hour = RTC().datetime()[4]
    print("updated time")

  time_stop = time_ns()