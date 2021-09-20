# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 01:55:08 2019

@author: Chao
"""
from instruments import get_instruments
instruments = get_instruments()


#CURRENT = instruments.create('CURRENT', 'Keithley_6221', address='TCPIP::169.254.47.111::INSTR')
#VNA = instruments.create('VNA','Agilent_ENA_5071C', address='TCPIP0::169.254.152.68::inst0::INSTR')

#MXA = instruments.create('MXA','Keysight_MXA_N9020A',address='TCPIP0::169.254.180.116::INSTR')

#SWT1 = instruments.create('SWT1','Mini_CircuitsSwitch',address='http://169.254.47.255')
#SWT2 = instruments.create('SWT2','Mini_CircuitsSwitch',address='http://169.254.47.253')

#YKYOKO = instruments.create('YOKO','Yokogawa_GS200',address = 'TCPIP::169.254.47.130::INSTR')
#YOKO = instruments.create('YOKO','Yokogawa_GS200',address = 'TCPIP::169.254.47.131::INSTR')


#SigGen = instruments.create('SigGen','Keysight_N5183B_1',address='TCPIP0::169.254.29.44::inst0::INSTR')#, reset = False)
#QGen = instruments.create('QGen','Keysight_N5183B_1',address='TCPIP0::169.254.161.164::inst0::INSTR', reset = False)  # restart the instrument, IP address changed
#BatGen = instruments.create('BatGen','Keysight_N5183B_1',address='TCPIP0::169.254.64.160::inst0::INSTR', reset = False)  # restart the instrument, IP address changed

#SigCore1 = instruments.create('SigCore1', 'SignalCore_sc5511a_test', serial_number = '10000E9D')
#SigCore2 = instruments.create('SigCore2', 'SignalCore_sc5511a_test', serial_number = '10001569')
#SigCore3 = instruments.create('SigCore3', 'SignalCore_sc5511a_test', serial_number = '1000156A')
#SigCore4 = instruments.create('SigCore4', 'SignalCore_sc5511a_test', serial_number = '10001851')
#SigCore5 = instruments.create('SigCore5', 'SignalCore_sc5511a_test', serial_number = '10001852')
#SigCore6 = instruments.create('SigCore6', 'SignalCore_sc5511a_test', serial_number = '1000184F')
#SigCore7 = instruments.create('SigCore7', 'SignalCore_sc5511a_test', serial_number = '10001850')
#SigCore8 = instruments.create('SigCore8', 'SignalCore_sc5511a_test', serial_number = '1000190F')
#SigCore9 = instruments.create('SigCore9', 'SignalCore_sc5511a_test', serial_number = '1000190E')

#QuSigCore1 = instruments.create('QuSigCore1', 'SignalCore_sc5506a', serial_number = '10001A85')

#SigHound = instruments.create('SigHound', 'SignalHound_SA124B', serial_number = '17320314')
#AWG = instruments.create('AWG','AWG5014C', address = 'TCPIP0::169.254.116.102::inst0::INSTR') ## DOWN ONE!!!
#AWG = instruments.create('AWG','AWG5014C', address = 'TCPIP0::169.254.47.254::inst0::INSTR') ## TOP ONE!!!
#YOKO1 = instruments.create('YOKO1','Yokogawa_GS200',address = 'TCPIP::169.254.47.130::INSTR')
YROKO1 = instruments.create('YROKO1','YROKO_Client')
#EXG = instruments.create('GEN','Keysight_N5183B',address='TCPIP0::169.254.79.129::inst0::INSTR', reset = False)

#import switch_control_20191028
#SWT = switch_control_20191028.SWT()