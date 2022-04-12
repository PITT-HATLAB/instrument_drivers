import types
import logging
import numpy as np
import time
from qcodes import (Instrument, VisaInstrument,
                    ManualParameter, MultiParameter,
                    validators as vals, Station)
import instrumentserver.serialize as ser
import easygui 
import os
import time

class Time(Instrument): 
    
    def __init__(self, name, **kwargs) -> None: 
        super().__init__(name, **kwargs)
        
        self.add_parameter('time', 
                           set_cmd = self.wait_until_time, 
                           # initial_value = par_dict["frequency"],
                           vals = vals.Numbers(0),
                           unit = 's'
                           )
        self.time_track = 0
        
    def wait_until_time(self, t): 
        time.sleep(t-self.time_track)
        self.time_track = t
        
        