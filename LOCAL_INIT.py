# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 11:05:31 2020

@author: Hatlab_3
"""

import matplotlib.pyplot as plt
import numpy as np
from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals, Parameter, Station)
import easygui
import ctypes

#base drivers
# from hatdrivers.Agilent_ENA_5071C import Agilent_ENA_5071C
# from hatdrivers.Keysight_P9374A import Keysight_P9374A
from instrument_drivers.base_drivers.Keysight_N5183B import Keysight_N5183B
from instrument_drivers.base_drivers.Yokogawa_GS200 import YOKO
from instrument_drivers.base_drivers.SignalCore_sc5511a import SignalCore_SC5511A
from instrument_drivers.base_drivers.MiniCircuits_Switch import MiniCircuits_Switch
from instrument_drivers.base_drivers.switch_control import SWT as SWTCTRL
from instrument_drivers.base_drivers.Keysight_MXA_N9020A import Keysight_MXA_N9020A
# from hatdrivers.Tektronix_AWG5014C import Tektronix_AWG5014C
from instrument_drivers import DLL
from instrument_drivers.yroko.YROKO_Client import YROKO
from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014

#customized drivers
from instrument_drivers.driver_wrappers.Hat_P9374A import Hat_P9374A
from instrument_drivers.driver_wrappers.Hat_ENA5071C  import Hat_ENA5071C
from instrument_drivers.driver_wrappers.Hat_MXA_N9020A import Hat_MXA_N9020A
#Metainstruments and tools ... 
from instrument_drivers.meta_instruments import Modes

from qcodes.instrument_drivers.AlazarTech.ATS9870 import AlazarTech_ATS9870
#%%AWG
# from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014
# from hatdrivers.Tektronix_AWG5014C_old import Tektronix_AWG5014C as Tk_old
# AWG = Tk_old('AWG', 'TCPIP0::169.254.116.102::inst0::INSTR')
# Alazar = AlazarTech_ATS9870('Alazar')
#%%
# MXA = Keysight_MXA_N9020A("MXA", address = 'TCPIP0::169.254.180.116::INSTR')
CXA = Hat_MXA_N9020A("CXA", address = 'TCPIP0::169.254.110.116::INSTR')
#%%
# VNA = Agilent_ENA_5071C("VNA", address = "TCPIP0::169.254.169.64::inst0::INSTR", timeout = 30)
# pVNA = Hat_P9374A("pVNA", address = "TCPIP0::Hatlab_3-PC::hislip0,4880::INSTR", timeout = 3)
# pVNA = Hat_P9374A("pVNA", address = "TCPIP0::DESKTOP-8EN5L8U::hislip0,4880::INSTR", timeout = 3)
pVNA = Hat_P9374A("pVNA", address = "TCPIP0::Hatlab_3-PC::hislip0,4880::INSTR", timeout = 3)
#for little VNA: TCPIP0::Hatlab_3-PC::hislip0,4880::INSTR\
#For big VNA: (RIP): TCPIP0::169.254.152.68::inst0::INSTR
#For big VNA2: TCPIP0::169.254.169.64::inst0::INSTR
#%%                      
SigGen = Keysight_N5183B("SigGen", address = "TCPIP0::169.254.29.44::inst0::INSTR")
# QGen = Keysight_N5183B("QGen", address = "TCPIP0::169.254.161.164::inst0::INSTR")
#%%
# try: 
yoko2 = YOKO('yoko2',address = "TCPIP::169.254.34.35::INSTR")
# except:           
#     print("YOKO not connected")
# yoko1 = YOKO('yoko1', address = 'TCPIP::169.254.239.5::INSTR')
# YROKO1 = YROKO('YROKO1')
#%%
# # Switches need to be initialized externally, then fed into the switch_control file explicitly
SWT1 = MiniCircuits_Switch('SWT1',address = 'http://169.254.47.255')
SWT2 = MiniCircuits_Switch('SWT2',address = 'http://169.254.47.253')

#%%update SWT Config

swt_modes = {
    "F":["xxx000xx", "xxxxxxxx"],
    "F_MX": ["xxx011xx", "xxxxxxxx"],
    "A":["xxx100xx", "xxxxxxxx"],
    "A_MX":["xxx111xx", "xxxxxxxx"],
    "2":["xx0xxxxx", "xxxxxxxx"],
    "6":["xx1xxxxx", "xxxxxxxx"]
    }

SWT = SWTCTRL(SWT1,SWT2,swt_modes)

#%% Load previous modes
Modes.load_from_folder(globals(),path = "Z:\Data\SH6F1_1141\modes")
#%%SignalCores z
dll_path = r'C:\Users\Hatlab_3\Desktop\RK_Scripts\New_Drivers\HatDrivers\DLL\sc5511a.dll'
# 
SC9 = SignalCore_SC5511A('SigCore9', serial_number = '1000190E', debug = True)

# from qcodes.instrument_drivers.tektronix.AWG5014 import Tektronix_AWG5014
SC4 = SignalCore_SC5511A('SigCore4', serial_number = '10001851', debug = True)
#%%
SC5 = SignalCore_SC5511A('SigCore5', serial_number = '10001852', debug = True)

